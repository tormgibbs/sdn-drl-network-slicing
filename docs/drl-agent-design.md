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

R = w1·R_SLA − w2·P_latency − w3·P_loss + w4·R_util − w5·P_fairness

**Symbol convention:** `latency_i` and `loss_i` in this section are raw values (milliseconds, percent) — the same units as the SLA thresholds `L_i` and `Loss_i`. This is what makes `(latency_i − L_i) / L_i` dimensionally correct. Do not substitute the normalised observation values here.

### R_SLA — SLA Satisfaction Reward

R_SLA = Σ s_i × 𝟙(latency_i ≤ L_i AND loss_i ≤ Loss_i)

Positive reward when both latency and loss are within SLA thresholds, weighted by slice priority s_i.

### P_latency — Latency Penalty

P_latency = Σ s_i × max(0, (latency_i − L_i) / L_i)

Continuous penalty proportional to the degree of latency SLA violation.

### P_loss — Packet Loss Penalty

P_loss = Σ s_i × loss_i

Weighted packet loss penalty across all slices.

### R_util — Resource Utilisation Reward

R_util = (1/n) × Σ min(throughput_i / a_i, 1.0)

`throughput_i` is the delivered downlink throughput to the slice sink, measured as delta `tx_bytes` / elapsed time on the AP-facing port of s2/s3 (post-meter). `a_i` is the current meter ceiling applied to that slice in bps. The `min(..., 1.0)` clamp matches the observation builder's clamp on `utilisation_i`, ensuring the agent observes the same signal it is rewarded on.

This measures delivery efficiency: how much of the allocated ceiling is being usefully consumed. A slice receiving 50 Mbps and delivering 48 Mbps contributes 0.96. A slice allocated 50 Mbps but delivering only 5 Mbps contributes 0.10, signalling wasted allocation.

**Measurement point:** `throughput_i` is post-meter and therefore structurally bounded by `a_i`. The ratio is always in [0, 1] by construction. This is intentional — the formula measures delivery efficiency against the current ceiling, not against unconstrained demand.

**Denominator safety:** `a_i ≥ floor_i > 0` is guaranteed by `project_allocation()`, called controller-side inside `meter_manager.install_meters()` on every /allocate request. The environment trusts the `rates_kbps` returned in /allocate's response as `a_i`. `_compute_reward()` and `_build_observation()` additionally assert `a_i > 0` before use, since this value crosses a network boundary — division by zero should be structurally impossible per the floor guarantee, but the assertion surfaces a violation loudly rather than allowing a bare ZeroDivisionError.

**Signal behaviour under load:** R_util provides weak gradient signal when total demand is below capacity — all slices show high efficiency regardless of allocation. Learning is driven primarily by R_SLA, P_latency, and P_loss in this regime. R_util becomes the dominant differentiating signal when total demand approaches or exceeds C (registration spike, exam period scenarios). The curriculum training order reflects this.

**Idle vs lossy disambiguation:** both an idle slice and a lossy-but-active slice produce low `throughput_i / a_i`. These are partially disambiguated by `loss_i` in the state vector: a lossy-but-active slice shows elevated ICMP probe loss; an idle slice shows near-zero loss. This disambiguation is imperfect — the probe uses ICMP through the GTP tunnel, not the iperf3 data path — so the agent learns the correlation empirically.

### P_fairness — Fairness Penalty

P_fairness = 1 − (Σ a_i/s_i)² / (n × Σ (a_i/s_i)²)

Priority-weighted Jain's Fairness Index penalty. "Fair" means a_i/s_i is equal across slices — a high-priority slice receives proportionally more bandwidth. n = 5 slices.

During spike scenarios, the expected agent behaviour is to disproportionately favour high-priority slices, which increases the spread of a_i/s_i and raises P_fairness. With w5 = 0.10 this effect is likely minor, but if VLE/Student Portal SLA satisfaction is suppressed during spike training, P_fairness interaction is the first diagnostic to check.

### Weights

| Weight | Value | Role |
|--------|-------|------|
| w1 | 0.35 | SLA satisfaction bonus |
| w2 | 0.25 | Latency penalty |
| w3 | 0.20 | Packet loss penalty |
| w4 | 0.10 | Utilisation reward |
| w5 | 0.10 | Fairness penalty |

Weights are hyperparameters tuned during training.

---

## SLA Thresholds

| Slice | Max Latency | Max Loss | Min Throughput | Priority (s_i) |
|-------|-------------|----------|----------------|----------------|
| VLE | 100 ms | 0.5% | 50 Mbps | 5 |
| Student Portal | 50 ms | 0.1% | 25 Mbps | 4 |
| Admin | 150 ms | 1% | 10 Mbps | 3 |
| IoT | 200 ms | 5% | 64 Kbps | 2 |
| General | 500 ms | 10% | 5 Mbps | 1 |

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
