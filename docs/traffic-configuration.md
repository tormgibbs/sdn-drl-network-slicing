# Traffic Generator Configuration

Traffic profiles are defined in `config/traffic.yaml`. Each slice has a pattern and rate parameters that control how traffic is generated through the GTP tunnels.

---

## Patterns

**`continuous`** — a single iperf3 flow runs for the full duration at the specified target rate. Used for Admin, IoT, and General slices which represent stable, predictable traffic.

**`mixed`** — two concurrent iperf3 flows run simultaneously on separate ports:
- A continuous baseline flow on port 5201 representing persistent background activity
- An ON/OFF burst flow on port 5202 that randomly activates and deactivates using exponential inter-arrival times, representing transient demand spikes

VLE and Student Portal use the mixed pattern to model lecture streaming and registration activity respectively.

---

## Parameters

| Parameter | Applies To | Description |
|-----------|------------|-------------|
| `pattern` | all | `continuous` or `mixed` |
| `protocol` | all | `tcp` or `udp` |
| `target_bps` | continuous | Aggregate target rate in bits per second |
| `port` | continuous | iperf3 server port (default 5201) |
| `packet_size` | continuous UDP | UDP packet size in bytes |
| `continuous_bps` | mixed | Target rate for the baseline flow |
| `continuous_port` | mixed | Server port for baseline flow (5201) |
| `on_off_bps` | mixed | Target rate during ON periods |
| `on_off_port` | mixed | Server port for burst flow (5202) |
| `mean_on_sec` | mixed | Mean ON duration in seconds (exponential distribution) |
| `mean_off_sec` | mixed | Mean OFF duration in seconds (exponential distribution) |
| `device_count` | all | Number of real-world devices this profile represents |
| `duration_sec` | all | Flow duration per loop (overrides default if set per slice) |

---

## Rate Design Rationale

Target rates are set at or above each slice's SLA minimum throughput threshold. This ensures that when all slices compete simultaneously for the 100 Mbps total capacity, demand exceeds supply and the DRL agent must actively prioritise higher-priority slices to maintain SLA compliance.

| Slice | Continuous Rate | Burst Rate | SLA Minimum |
|-------|----------------|------------|-------------|
| VLE | 50 Mbps | 30 Mbps | 50 Mbps |
| Student Portal | 25 Mbps | 20 Mbps | 25 Mbps |
| Admin | 10 Mbps | — | 10 Mbps |
| IoT | 64 Kbps | — | 64 Kbps |
| General | 5 Mbps | — | 5 Mbps |

Peak total demand when all bursts are active simultaneously: ~130 Mbps, exceeding the 100 Mbps link capacity by 30%.

---

## ON/OFF Burst Model

The ON/OFF burst component uses exponentially distributed ON and OFF durations, which is the standard model for self-similar network traffic. The mean durations per slice are chosen to reflect realistic academic traffic patterns:

| Slice | Mean ON | Mean OFF | Rationale |
|-------|---------|----------|-----------|
| VLE | 15s | 45s | Lecture video segments with pauses |
| Student Portal | 8s | 20s | Short registration transactions |

---

## Running the Traffic Generator

```bash
# Run all slices continuously
make traffic-start

# Run one loop across all slices
uv run scripts/traffic_generator.py --loops 1

# Run specific slices
uv run scripts/traffic_generator.py --slices vle student_portal --loops 1

# Stop
make traffic-stop
```

Results are saved to `logs/traffic/results_<timestamp>.json` after each loop. Each file contains per-slice metrics: throughput (sender and receiver Mbps), retransmits (TCP), loss percentage, jitter and packet counts (UDP), and component label (continuous or on_off).

---

## Dual-Port Architecture

VLE and Student Portal run two iperf3 servers on their sink stations — one on port 5201 for the continuous baseline and one on port 5202 for the ON/OFF burst. This is necessary because iperf3 server only accepts one client connection at a time per port. The dual-port setup allows both components to run concurrently without interference.

Admin, IoT, and General use only port 5201.
