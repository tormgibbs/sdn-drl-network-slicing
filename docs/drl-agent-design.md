# DRL Agent Design

This document specifies the Deep Reinforcement Learning agent design for the autonomous SDN network slicing framework. It defines the state space, action space, reward function, algorithm, and Gymnasium environment interface.

---

## Problem Framing

The network resource management task is modelled as a Markov Decision Process (S, A, R, P, γ). The agent makes one allocation decision per stats collection cycle (every 5 seconds). At each step the agent observes the network state, selects a bandwidth allocation action, and receives a reward reflecting SLA satisfaction.

---

## State Space — 15 dimensions

Three metrics per slice, five slices: S = {v1, v2, v3, v4, v5} ∈ R^15

Per-slice vector: vi = {latency_i, loss_i, utilisation_i}

| Metric | Source | Collection method |
|--------|--------|-------------------|
| Average end-to-end latency | Active RTT probe per slice | ping from UE tunnel to sink station, RTT/2 |
| Packet loss rate | Active RTT probe per slice | packet loss percentage from ping output |
| Bandwidth utilisation | OVS port stats | delta bytes / elapsed time per slice port |

All metrics are normalised to [0, 1] before feeding to the neural network:

| Metric | Normalisation | Clamp |
|--------|--------------|-------|
| latency_i | latency_ms / max_latency_ms (per-slice SLA threshold) | min(..., 1.0) |
| loss_i | loss_pct / 100 | none (structurally bounded) |
| utilisation_i | tx_throughput_bps / a_i (current meter ceiling, bps) | min(..., 1.0) |

**Symbol convention:** `latency_i`, `loss_i`, and `utilisation_i` in the state vector are normalised [0,1] values. The Reward Function section reuses `latency_i` and `loss_i` to refer to the raw values (ms, %) — same variables, different units. The two sections are not interchangeable.

**State/reward consistency:** `utilisation_i` in the state vector and the `throughput_i / a_i` term in R_util use the same numerator and denominator. The agent observes the same efficiency signal it is rewarded on.

Queue occupancy was excluded from the state space. Instantaneous queue depth is not observable at any practical polling granularity in a single-kernel veth-based emulation environment — the transmit path drains the qdisc within the same softirq context as enqueue, producing structurally zero backlog regardless of load. This was verified empirically. Direct RTT measurement via active ping probing already captures the congestion signal that queue depth would predict. See design-note-queue-removal.md for full reasoning.

---

## Action Space — 5 dimensions

Continuous 5D vector, one allocation fraction per slice. Raw neural network output z_i is passed through softmax to produce a probability distribution. The Gymnasium environment sends these fractions to /allocate; floor projection happens controller-side, not in the environment.

**Pipeline:**

1. **Softmax (environment):** p_i = softmax(z_i), producing a probability distribution summing to 1, POSTed to /allocate as {slice_name: fraction}.
2. **Floor projection (controller):** `project_allocation(p, floors_kbps, C_kbps)` inside `meter_manager.install_meters()` ensures each slice receives at least its minimum bandwidth floor. Slices whose softmax-implied allocation falls below their floor are clamped; remaining capacity is distributed proportionally among unclamped slices.
3. **Output:** integer kbps values summing to exactly C, installed via OFPMeterMod and returned to the environment in /allocate's response as `rates_kbps`.

The controller is the single source of truth for the projection. The environment does not call `project_allocation()` itself. It POSTs raw fractions and trusts the `rates_kbps` returned in the response as `a_i` for observation and reward computation. This avoids two independently-computed projections being assumed to agree.

**Per-slice floors** (from slices.yaml min_throughput_bps):

| Slice | Floor (kbps) |
|-------|-------------|
| VLE | 50000 |
| Student Portal | 25000 |
| Admin | 10000 |
| IoT | 64 |
| General | 5000 |

Sum of floors: 90064 kbps. Remainder for agent decisions: 9936 kbps.

**Guarantees:**
- All allocations ≥ per-slice floor
- Sum of allocations equals exactly C (100000 kbps)
- No link oversubscription
- Integer kbps output matches OFPMeterMod enforcement boundary

---

## Reward Function

R = w1·R_SLA − w2·P_latency − w3·P_loss − w4·P_oscillation + w5·R_util − w6·P_fairness

This is a dense, proactive reward function designed to provide continuous gradient signals before SLA boundaries are breached, and to penalize unnecessary allocation oscillation.

### R_SLA — Dense SLA Satisfaction Reward
R_SLA = Σ s_i × max(0, 1 − (latency_i / L_i)) × max(0, 1 − (loss_i / Loss_i))

Provides a smooth, continuous reward that scales down as latency or loss approaches the SLA threshold, rather than a binary cliff.

### P_latency — Proactive Latency Penalty
P_latency = Σ s_i × (latency_i / L_i)²

A squared penalty that increases quadratically as latency approaches the limit. This provides a strong gradient signal to proactively reserve headroom before the hard SLA boundary is crossed.

### P_loss — Packet Loss Penalty
P_loss = Σ s_i × (loss_i / Loss_i)

Continuous weighted packet loss penalty, normalized by each slice's specific SLA threshold. A slice with a 0.1% loss SLA is penalized 10× more harshly than a slice with a 1% loss SLA for the same absolute loss percentage.

### P_oscillation — Allocation Stability Penalty
P_oscillation = Σ |a_i(t) − a_i(t−1)| / C

Penalizes large, unnecessary shifts in bandwidth allocation between consecutive steps. This prevents the agent from oscillating wildly and reduces control-plane overhead.

### R_util — Resource Utilisation Reward

R_util = (1/n) × Σ min(throughput_i / a_i, 1.0)

Measures delivery efficiency: how much of the allocated ceiling is being usefully consumed. 

### P_fairness — Fairness Penalty
P_fairness = 1 − (Σ (a_i/s_i))² / (n × Σ (a_i/s_i)²)

Priority-weighted Jain's Fairness Index penalty. Ensures high-priority slices receive proportionally more bandwidth.

### Weights

| Weight | Value | Role |
|--------|-------|------|
| w1 | 0.30 | Dense SLA satisfaction bonus |
| w2 | 0.25 | Proactive latency penalty (squared) |
| w3 | 0.15 | Packet loss penalty |
| w4 | 0.10 | Allocation oscillation penalty |
| w5 | 0.10 | Utilisation reward |
| w6 | 0.10 | Fairness penalty |

### Design Rationale
This reward function is informed by recent research on proactive DRL resource allocation (2024–2025). The squared latency penalty approximates the risk-sensitive sigmoid penalty used in SafeSlice (Nagib et al., 2025), providing gradient signal before SLA boundaries are breached rather than reacting only after violations occur. The oscillation penalty addresses the stability concerns identified in hierarchical DRL frameworks (Hu et al., 2024). The dense SLA satisfaction term replaces the binary step-function approach, ensuring the agent receives continuous feedback even when operating well within SLA limits.

**Future enhancement:** SafeSlice's sigmoid-based risk penalty `1/(1 + e^(-c1·(-l - (-c2))))` provides a theoretically more principled S-curve penalty bounded in [0,1], compared to the unbounded squared penalty used here. This is a candidate for future iteration if the squared penalty produces undesirable gradient behavior near SLA boundaries.

---

## Algorithm

PPO via Stable-Baselines3, MLP policy network.

- Input: 15-dimensional normalised state vector
- Output: 5-dimensional continuous allocation vector (softmax applied internally; floor projection happens controller-side)

PPO is selected because campus network traffic conditions are dynamic and change continuously. PPO's clipped surrogate objective restricts policy updates at each step, preventing large changes that would cause the agent to forget previously learned behaviour. It handles continuous action spaces naturally and is fully supported by Stable-Baselines3.

**Training approach: curriculum-based**

1. Train under normal load to learn a stable baseline allocation policy
2. Gradually expose to peak scenarios (registration spike, exam period)

---

## Training Scenarios

| Scenario | Description | Expected agent behaviour |
|----------|-------------|--------------------------|
| Normal | All slices at baseline load, total demand ~90 Mbps | Maintain all SLAs, learn stable allocation |
| Registration spike | Student Portal and VLE surge simultaneously, total demand exceeds 100 Mbps | Prioritise VLE (s_i=5) and Student Portal (s_i=4), reduce IoT and General |
| Exam period | VLE surge only | Allocate majority to VLE, protect remaining SLAs |

---

## Baselines for Comparison

1. **Static allocation (hard slicing):** floor-projected equal-split allocation, fixed for the entire run: [50000, 25000, 12211, 4472, 8317] kbps. This represents a reasonable fixed allocation that respects per-slice SLA minimums but cannot adapt to demand. The same projection function and floor values are used as in the DRL agent's action pipeline, ensuring the comparison isolates adaptivity (DRL vs static) rather than floor-awareness.

2. **Rule-based heuristic:** step-increase allocation when a slice exceeds 80% of its current allocation. Introduces basic adaptability but relies on fixed thresholds and cannot optimise across slices simultaneously.

---

## Gymnasium Environment Interface

- `observation_space`: Box(15,) normalised [0, 1]
- `action_space`: Box(5,) raw logits; softmax applied internally, floor projection controller-side

### step()

1. Apply softmax to raw action logits, producing fractions p
2. POST p to /allocate; controller projects through `project_allocation()` and returns the installed `rates_kbps`
3. Store `rates_kbps` as the current allocation (a_i for observation/reward)
4. Block on WebSocket until next stats push (5 seconds)
5. Build 15-dimensional observation vector from received stats
6. Compute reward
7. Return (observation, reward, terminated, truncated, info)

**Failure handling:** /allocate POST, WebSocket receive, and metrics validation are wrapped in a single try/except covering `httpx.HTTPError`, `OSError`, `websockets.WebSocketException`, and `AssertionError`. On failure, step() returns (last_obs, 0.0, terminated=False, truncated=True, info={"failure": reason}).

`last_obs` is the real observation from the most recent successful step or reset — confirmed via SB3 2.9.0 source that `DummyVecEnv` copies whatever observation is returned alongside `truncated=True` into `info["terminal_observation"]` for value bootstrapping. Reward is 0.0 rather than a separate penalty, since SB3's bootstrap already corrects for truncation. `_step_count` increments on failure — failed steps are not exempt from episode length.

### reset()

**Normal path** (UE sessions assumed persistent across episodes):

1. Check all 5 UE tunnel interfaces exist (ue1tun0 through ue5tun0 via `docker exec ueransim ip link show`)
2. POST equal-split fractions [0.2, 0.2, 0.2, 0.2, 0.2] to /allocate; controller installs baseline allocation [50000, 25000, 12211, 4472, 8317] kbps, returns `rates_kbps`
3. Reconnect to WebSocket
4. Block until next stats push, build and return initial observation, info={}

The current implementation trusts /allocate's response rather than independently confirming installed meter state via OFPMeterConfigStatsRequest. Independent verification is a possible future hardening step.

**Recovery path** (invoked when tunnel interfaces are missing):

1. Re-trigger UERANSIM registration for missing UEs via `docker exec -d ueransim /ueransim/nr-ue -c /ueransim/config/<config_file>`, with config file resolved from ue_profiles.yaml
2. Wait up to 30 seconds for each missing interface to appear
3. Log a structured warning — recovery events indicate emulation instability and should be investigated
4. Proceed from step 2 of normal path

The recovery path adds 10–30 seconds per invocation. During training, UE sessions persist across episodes — recovery should fire rarely. Frequent recovery is a signal of emulation instability, not a reset() design issue.

**Failure handling:** /allocate POST, WebSocket connect/receive, metrics validation, and tunnel interface checks are wrapped in a single try/except. Unlike step(), there is no degraded return — a failed reset() raises `RuntimeError`, chaining the original exception for debugging. Whether a training harness retries reset() is a harness-level decision.

**Episode termination:** fixed number of steps (100 steps ≈ 8 minutes)

---

## Key Implementation Constraints

- `step()` blocks on WebSocket, not polling `/metrics` — ensures observation is always fresh
- Softmax is applied inside the Gymnasium environment; floor projection happens controller-side inside `meter_manager.install_meters()` — the environment never calls `project_allocation()` itself
- `project_allocation()` is the single enforcement point for per-slice minimum bandwidth, called only from the controller
- All state metrics are normalised before neural network input
- Agent controls meter ceilings only, via OFPMeterMod at s2/s3
- Reward computation uses `throughput_i` (post-meter tx_bytes delta, bps) and `a_i` (current meter ceiling, bps) directly, both available from stats_collector and meter_manager without additional instrumentation
- Post-softmax action-distribution entropy should be logged separately from SB3's built-in policy entropy during training — softmax can saturate (large logit differences map to near-identical allocations), collapsing effective exploration while z-space entropy appears healthy; if post-softmax entropy drops early in training, first remediation is increasing ent_coef, logit clipping is a fallback
