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

All metrics normalised to [0, 1] before feeding to the neural network.

Queue occupancy was excluded from the state space. Instantaneous queue depth is not observable at any practical polling granularity in a single-kernel veth-based emulation environment — the transmit path drains the qdisc within the same softirq context as enqueue, producing structurally zero backlog regardless of load. This was verified empirically. Direct RTT measurement via active ping probing already captures the congestion signal that queue depth would predict. See design-note-queue-removal.md for full reasoning.

---

## Action Space — 5 dimensions

Continuous 5D vector, one allocation fraction per slice. Raw neural network output zi passed through softmax to produce a probability distribution. Each allocation:

ai = softmax(zi) × C

where C = total link capacity (100 Mbps).

Guarantees:
- All allocations strictly positive
- Sum of allocations equals exactly C
- No link over-subscription

Applied via OFPMeterMod commands through the /allocate REST endpoint.

---

## Reward Function

R = w1·R_SLA − w2·P_latency − w3·P_loss + w4·R_util − w5·P_fairness

**SLA Satisfaction Reward (R_SLA)**

R_SLA = Σ si × 1(latency_i ≤ Li AND loss_i ≤ Loss_i)

Positive reward if both latency and loss are within SLA thresholds, weighted by slice priority si.

**Latency Penalty (P_latency)**

P_latency = Σ si × max(0, (latency_i − Li) / Li)

Continuous penalty proportional to the degree of latency SLA violation.

**Packet Loss Penalty (P_loss)**

P_loss = Σ si × loss_i

Weighted packet loss penalty across all slices.

**Resource Utilisation Reward (R_util)**

R_util = Σ min(ai, demand_i) / C

Rewards allocating capacity to slices that actually use it. `demand_i` is the
slice's offered load in bps, taken from the raw OVS port-stat
delta-bytes/elapsed-time measurement — the same intermediate value used to
compute `utilisation_i` for the state vector, but retained pre-normalization
so it shares units with `ai` and `C`.

`min(ai, demand_i)` caps credit at the allocated ceiling: the agent gets no
utilisation credit for demand beyond what it chose to allocate (that shortfall
is already penalised via `P_latency`/`P_loss`/`R_SLA`), and gets no credit for
allocation beyond what a slice actually used (preventing the agent from
"parking" unused ceiling on an idle slice to inflate this term).

**Previous formulation removed:** R_util = Σ (ai/C) was a constant equal to 1
on every step, since `Σ ai = C` by construction of the softmax-normalised
action space (see Action Space guarantees). It contributed a fixed offset to
the reward and provided no learning signal.

**Fairness Penalty (P_fairness)**

P_fairness = 1 − (Σ ai/si)^2 / (n × Σ (ai/si)^2)

Priority-weighted Jain's Fairness Index penalty. Prevents extreme resource starvation. n = 5 slices.

**Initial weights:**

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

| Slice | Max Latency | Max Loss | Min Throughput | Priority (si) |
|-------|-------------|----------|----------------|---------------|
| VLE | 100 ms | 0.5% | 50 Mbps | 5 |
| Student Portal | 50 ms | 0.1% | 25 Mbps | 4 |
| Admin | 150 ms | 1% | 10 Mbps | 3 |
| IoT | 200 ms | 5% | 64 Kbps | 2 |
| General | 500 ms | 10% | 5 Mbps | 1 |

---

## Algorithm

PPO via Stable-Baselines3, MLP policy network.

- Input: 15-dimensional normalised state vector
- Output: 5-dimensional continuous allocation vector (softmax applied internally)

PPO is selected because the campus network traffic conditions are dynamic and change continuously. PPO's clipped surrogate objective restricts policy updates at each step, preventing large changes that would cause the agent to forget previously learned behaviour. It handles continuous action spaces naturally and is fully supported by Stable-Baselines3.

**Training approach: curriculum-based**

1. Train under normal load to learn a stable baseline allocation policy
2. Gradually expose to peak scenarios (registration spike, exam period)

---

## Training Scenarios

| Scenario | Description | Expected agent behaviour |
|----------|-------------|--------------------------|
| Normal | All slices at baseline load, total demand ~90 Mbps | Maintain all SLAs, learn stable allocation |
| Registration spike | Student Portal and VLE surge simultaneously, total demand exceeds 100 Mbps | Prioritise VLE (si=5) and Student Portal (si=4), reduce IoT and General |
| Exam period | VLE surge only | Allocate majority to VLE, protect remaining SLAs |

---

## Baselines for Comparison

1. **Static allocation (hard slicing):** fixed bandwidth per slice regardless of demand. Reflects the current manual approach.
2. **Rule-based heuristic:** step-increase allocation when a slice exceeds 80% of its current allocation. Introduces basic adaptability but relies on fixed thresholds and cannot optimise across slices simultaneously.

---

## Gymnasium Environment Interface

- `observation_space`: Box(15,) normalised [0, 1]
- `action_space`: Box(5,) raw logits, softmax applied internally before /allocate call

**step() flow:**
1. Apply action via POST /allocate
2. Block on WebSocket until next stats push (5 seconds)
3. Build 15-dimensional observation vector from received stats
4. Compute reward
5. Return (observation, reward, terminated, truncated, info)

**reset() flow:** reconnect to WebSocket, return initial observation

**Episode termination:** fixed number of steps (100 steps ≈ 8 minutes)

---

## Key Implementation Constraints

- `step()` blocks on WebSocket, not polling `/metrics` — ensures observation is always fresh
- Softmax applied inside the Gymnasium environment before sending to `/allocate`, not by the controller
- All state metrics normalised before neural network input
- HTB floors protect against complete starvation — agent operates above floors
- Agent controls meter ceilings only, not HTB floors


## Key Implementation Constraints

- `step()` blocks on WebSocket, not polling `/metrics` — ensures observation is always fresh
- Softmax applied inside the Gymnasium environment before sending to `/allocate`, not by the controller
- All state metrics normalised before neural network input
- HTB floors protect against complete starvation — agent operates above floors
- Agent controls meter ceilings only, not HTB floors
- Reward computation requires raw pre-normalization demand_i (bps) per slice from stats_collector, in addition to the normalized [0,1] observation vector