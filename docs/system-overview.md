# System Overview

This document describes the architecture, components, and data flow of the Autonomous SDN Network Slicing framework. It is intended as the entry point for anyone new to the codebase.

For setup instructions see [docs/setup.md](setup.md). For traffic configuration see [docs/traffic-config.md](traffic-config.md).

---

## What This System Does

The system implements a private 5G campus network for the University of Mines and Technology (UMaT), divided into five logical network slices — one per campus service category. A Deep Reinforcement Learning (DRL) agent continuously monitors the state of each slice and dynamically adjusts bandwidth allocations to maintain Quality of Service (QoS) targets without manual intervention.

The core problem it addresses: university network traffic is driven by academic calendars. During registration periods, thousands of students access the Student Portal simultaneously. During exams, VLE traffic surges. Static bandwidth allocation cannot anticipate these spikes. The DRL agent learns to respond to them automatically, prioritising high-priority slices when total demand exceeds capacity.

---

## Network Slices

Five slices are defined, each mapped to a campus service category and a 3GPP S-NSSAI identifier:

| Slice | VLAN | SST | SD | Traffic Type | Priority |
|-------|------|-----|-----|-------------|----------|
| VLE | 10 | 1 (eMBB) | 000001 | Lecture video, file uploads, quizzes | 5 (highest) |
| Student Portal | 20 | 1 (eMBB) | 000002 | Registration, results access | 4 |
| Admin Systems | 30 | 1 (eMBB) | 000003 | Institutional services | 3 |
| IoT | 40 | 2 (mMTC) | 000004 | Sensor and device communication | 2 |
| General Traffic | 50 | 1 (eMBB) | 000005 | Student and staff browsing | 1 (lowest) |

Slice isolation is enforced at Layer 2 using VLAN tagging in Open vSwitch. Each slice has defined SLA thresholds for maximum latency, maximum packet loss, and minimum throughput. The DRL agent's reward function penalises SLA violations weighted by slice priority.

---

## Architecture

The system has four layers:

```
┌─────────────────────────────────────────────────────┐
│                   DRL Agent (PPO)                   │
│         Observes state, outputs allocations         │
└─────────────────────┬───────────────────────────────┘
                      │ REST API (/metrics, /allocate)
┌─────────────────────▼───────────────────────────────┐
│              OS-Ken SDN Controller                  │
│   Collects stats, installs OpenFlow rules/meters    │
└──────────┬──────────────────────────┬───────────────┘
           │ OpenFlow 1.3             │ OpenFlow 1.3
┌──────────▼──────────┐   ┌──────────▼───────────────┐
│   Mininet-WiFi      │   │      free5GC 5G Core      │
│   Three-tier OVS    │   │   AMF, SMF, UPF, NSSF    │
│   topology          │   │   PCF, NRF, UDR, etc.    │
└─────────────────────┘   └──────────────────────────┘
```

### Three-Tier OVS Topology

The campus network is emulated using Mininet-WiFi with Open vSwitch:

- **Core switch (s1):** connects to the 5G UPF via a veth pair. Classifies UE traffic by source IP subnet and pushes VLAN tags. Handles return path from campus stations back to UEs.
- **Aggregation switches (s2, s3):** enforce dynamic bandwidth ceilings via OpenFlow meters updated by the DRL agent. Collect per-slice port statistics every 5 seconds.
- **Access points (ap1–ap5):** one per slice. Enforce minimum bandwidth floors via HTB queues. Handle VLAN tagging/stripping and MAC rewriting for station traffic.

```
s1 (core)
├── s2 (aggregation) ── ap1 (VLE) ── sta1 (sink), sta2 (source)
│                   ── ap2 (Student Portal) ── sta3, sta4
│                   ── ap3 (Admin) ── sta5, sta6
└── s3 (aggregation) ── ap4 (IoT) ── sta7, sta8
                    ── ap5 (General) ── sta9, sta10
```

### 5G Core (free5GC)

The 5G core runs as Docker containers and handles UE authentication, session management, and user plane forwarding:

- **AMF** — authenticates UEs and manages mobility. Each UE registers with the AMF which assigns it to the correct slice based on its S-NSSAI.
- **SMF** — creates and manages PDU sessions. Assigns static IPs to UEs from per-slice pools and selects the UPF for data forwarding.
- **UPF** — the user plane function. Decapsulates GTP-U tunnels from UERANSIM and forwards traffic to the campus network via a veth pair connected to s1. This is the boundary between the 5G core and the Mininet topology.
- **NSSF** — selects the appropriate network slice for each UE based on its S-NSSAI.
- **NRF, UDR, UDM, AUSF, PCF** — support functions for service discovery, subscriber data, authentication, and policy.

### How 5G Connects to the Campus Network

```
UERANSIM (gNB + UEs)
      │
      │ GTP-U tunnel (UDP/2152)
      ▼
free5GC UPF
      │
      │ veth pair (upf-s1 / s1-upf)
      ▼
OVS s1 (core switch)
      │
      │ VLAN-tagged forwarding
      ▼
s2/s3 (aggregation) → ap1–ap5 (access) → sta1–sta10 (sinks)
```

Traffic from a UE travels through the UERANSIM GTP tunnel, gets decapsulated by UPF, exits via the veth pair into s1, gets classified by source IP and tagged with the slice VLAN, forwarded through aggregation to the correct AP, and delivered to the sink station. Return traffic follows the reverse path.

Each UE has a static IP and a dedicated tunnel interface (`ue1tun0` through `ue5tun0`) mapped to its slice. Traffic generators bind to these interfaces, forcing all generated traffic through the GTP tunnels and through the full data path.

### SDN Controller (OS-Ken)

The OS-Ken controller manages all eight switches via OpenFlow 1.3. At startup it installs:

- **VLAN forwarding rules** on s1 — flood VLAN-tagged frames to the correct aggregation switch
- **UPF ingress rules** on s1 — classify UPF-originated traffic by source IP subnet, push VLAN tag, forward to aggregation
- **Return path rules** on s1 — match VLAN + destination UE subnet, strip VLAN, rewrite dst MAC to UPF eth0, forward out s1-upf
- **Aggregation forwarding rules** on s2/s3 — per-VLAN per-port unicast forwarding, no flooding
- **OpenFlow meters** on s2/s3 — dynamic bandwidth ceilings per slice, updated by the DRL agent
- **HTB queues** on ap1–ap5 — minimum bandwidth floors per slice
- **MAC rewrite rules** on ap1–ap5 — rewrite dst MAC to sink station MAC for downlink traffic

### Stats Collector

The stats collector runs inside the controller process and produces the observation that feeds the DRL agent. Every 5 seconds it:

1. Requests port statistics from s2 and s3 via OpenFlow — derives `tx_throughput_bps` per slice
2. Runs ping probes from each UE tunnel to its slice sink station — derives `latency_ms` and `loss_pct` per slice
3. Merges results into a cache served by the REST API

### REST API

The controller exposes a northbound REST API:

- `GET /metrics` — current per-slice state (throughput, latency, loss)
- `POST /allocate` — set bandwidth allocation fractions per slice, triggers OpenFlow meter updates
- `GET /health` — controller health check
- `WebSocket /ws` — pushes stats to subscribers every collection cycle

### DRL Agent

The agent is implemented using PPO from Stable-Baselines3. It wraps the network environment in a Gymnasium interface:

- **Observation space:** `Box(15,)` — normalised `[latency_ms, loss_pct, tx_throughput_bps]` per slice × 5 slices
- **Action space:** `Box(5,)` — raw logits, softmax applied internally before sending to `/allocate`
- **step():** posts allocation → blocks on WebSocket for next stats push → computes reward → returns observation
- **Reward:** weighted sum of SLA satisfaction, latency penalty, loss penalty, utilisation reward, and fairness penalty

---

## Bandwidth Enforcement: Two-Mechanism Design

Each slice has two bandwidth controls operating at different layers:

- **HTB queues on access points** — minimum bandwidth floor. Guaranteed regardless of what the agent decides. Prevents complete starvation.
- **OpenFlow meters on aggregation switches** — dynamic bandwidth ceiling. Set by the DRL agent at each decision step. The agent operates above the floors and below 100 Mbps total.

The agent controls only the ceilings. The floors are fixed infrastructure.

---

## Traffic Model

Two traffic patterns are used to create realistic slice load:

- **Continuous** — a sustained iperf3 flow at the slice's SLA minimum throughput. Represents baseline activity that is always present.
- **Mixed** — a continuous baseline plus an ON/OFF burst component on a separate port. Burst durations are exponentially distributed. Represents bursty academic traffic (lecture streams, registration spikes).

VLE and Student Portal use mixed patterns. Admin, IoT, and General use continuous only. See [docs/traffic-config.md](traffic-config.md) for full details.

---

## Codebase Structure

```
infrastructure/
  controller/         OS-Ken SDN controller
    app.py            Main controller, OpenFlow event handlers
    flow_manager.py   Flow rule installation
    meter_manager.py  OpenFlow meter management
    queue_manager.py  HTB queue management
    stats_collector.py Per-slice metrics collection
    rest_api.py       Northbound REST API and WebSocket
  topology/
    campus_topology.py Mininet-WiFi topology definition
  free5gc/
    config/           free5GC network function configs
    docker-compose.yaml 5G core container definitions

scripts/
  traffic_generator.py Per-slice iperf3 traffic generation
  network-setup.sh    Veth pair, OVS bridge, routing setup

config/
  slices.yaml         Slice QoS parameters and SLA thresholds
  topology.yaml       Switch hierarchy and port mappings
  ue_profiles.yaml    UE identity and tunnel mappings
  traffic.yaml        Traffic profiles per slice

docs/
  setup.md            Installation and startup guide
  system-overview.md  This document
  traffic-config.md   Traffic generator configuration
  subscriber-registration.md  free5GC WebUI registration steps
  known-issues.md     Known issues and workarounds
  debugging-5gc.md    5GC and data path debugging guide
  drl-agent-design.md DRL agent state space, reward, algorithm
```

---

## Key Design Decisions

**VLAN as slice isolation proxy** — 3GPP slicing uses S-NSSAI at the 5G layer. Inside the Mininet OVS data plane, VLAN tags provide equivalent logical isolation at Layer 2, which OpenFlow 1.3 can match and enforce.

**Static UE IPs** — UPF normally assigns IPs dynamically. Static assignment makes the IP-to-VLAN classification rules on s1 deterministic and reproducible across experiment runs.

**Aggregation as the stats and enforcement point** — per-slice metrics are collected at s2/s3 because each aggregation switch covers multiple slices. Collecting at s1 mixes all slices. Collecting at APs gives per-AP stats, not per-slice totals.

**Single flow per slice for traffic generation** — a single TCP flow with `-b` rate targeting is sufficient to reach SLA-level rates in this emulated environment. Multiple parallel flows add complexity without benefit since the bottleneck is OVS meter enforcement, not TCP throughput per flow.

**Native hub threading** — OS-Ken 4.2.0 uses Python's native threading module, not eventlet. The stats collector uses `threading.Event` for synchronisation between the OpenFlow reply handler and the collection loop.