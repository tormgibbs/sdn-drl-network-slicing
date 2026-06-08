# Autonomous SDN Network Slicing with Deep Reinforcement Learning

A private 5G campus network slicing framework for the University of Mines and Technology (UMaT). A Deep Reinforcement Learning agent dynamically allocates bandwidth across five network slices to maintain QoS under variable traffic conditions.

## What It Does

- Emulates a three-tier campus network using Mininet-WiFi and Open vSwitch
- Integrates a free5GC 5G core for real GTP-U tunnel-based traffic forwarding
- Manages five network slices (VLE, Student Portal, Admin, IoT, General) with VLAN isolation
- Collects per-slice metrics (throughput, latency, packet loss) via an OS-Ken SDN controller
- Trains a PPO agent to allocate bandwidth across slices to maximise SLA satisfaction

## Stack

- **Network emulation:** Mininet-WiFi, Open vSwitch, OpenFlow 1.3
- **5G core:** free5GC v4.2.2, UERANSIM
- **SDN controller:** OS-Ken with FastAPI northbound API
- **DRL:** Stable-Baselines3 PPO, Gymnasium
- **Traffic generation:** iperf3 with ON/OFF burst patterns

## Getting Started

See [docs/setup.md](docs/setup.md) for full installation and startup instructions.

For a system architecture overview see [docs/system-overview.md](docs/system-overview.md).

## Documentation

| Document | Description |
|----------|-------------|
| [docs/setup.md](docs/setup.md) | Installation and startup guide |
| [docs/system-overview.md](docs/system-overview.md) | Architecture and component descriptions |
| [docs/traffic-configuration.md](docs/traffic-configuration.md) | Traffic generator configuration |
| [docs/subscriber-registration.md](docs/subscriber-registration.md) | free5GC subscriber setup |
| [docs/drl-agent-design.md](docs/drl-agent-design.md) | DRL agent state space, reward function, algorithm |
| [docs/known-issues.md](docs/known-issues.md) | Known issues and workarounds |
| [docs/debugging-5gc.md](docs/debugging-5gc.md) | 5GC and data path debugging |

## Requirements

- Ubuntu 22.04+ (native install recommended)
- Python 3.10+
- Docker Engine v24.0+ and Docker Compose v2
- Kernel 6.x or 7.x
- x86_64 with AVX/AVX2 support (required for MongoDB 4.4)
