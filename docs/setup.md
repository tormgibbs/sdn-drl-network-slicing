# Setup Guide

## 1. Hardware and OS Requirements

- CPU: x86_64 with AVX/AVX2 support (required for MongoDB 4.4)
- RAM: 8GB minimum, 16GB recommended
- OS: Ubuntu 22.04 or later, native install recommended. VM deployments will work but add overhead and may cause issues with kernel module compilation.
- Kernel: 6.x or 7.x (tested on 7.0.0-14 and 7.0.0-15)

Verify AVX support before proceeding:

```bash
grep -o 'avx[^ ]*' /proc/cpuinfo | sort -u
```

You must see `avx` and `avx2` in the output. If not, MongoDB 4.4 will fail to start.

---

## 2. System Preparation

Update your package index and install the required dependencies:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget build-essential linux-headers-$(uname -r) iw net-tools
```

---

## 3. Prerequisites

The following must be installed and verified before proceeding:

- **Docker Engine** (v24.0+) and **Docker Compose v2**: follow the [official Ubuntu install guide](https://docs.docker.com/engine/install/ubuntu/). Ensure your user is added to the `docker` group (`sudo usermod -aG docker $USER`). The legacy `docker-compose` v1 standalone binary is not supported.
- **Python 3.10+**: required for the SDN controller and traffic generation scripts.
- **uv**: required for Python dependency management.

---

## 4. Mininet-WiFi Installation

Mininet-WiFi must be installed from source. The Ubuntu package is outdated.

```bash
git clone https://github.com/intrig-unicamp/mininet-wifi
cd mininet-wifi
```

Before running the install script, patch it to replace the removed `wireless-tools`
package with `iw`, which serves the same purpose and is available on Ubuntu 22.04+:

```bash
sed -i 's/wireless-tools/iw/g' util/install.sh
```

Install the `six` Python module:

```bash
sudo pip install six --break-system-packages
```

Run the install script:

```bash
sudo util/install.sh -Wlnfv
```

Verify:

```bash
sudo mn --wifi --test pingall
```

---

## 5. Open vSwitch

OVS is installed as part of the Mininet-WiFi install script above. Verify it is running:

```bash
sudo ovs-vsctl show
ovs-vsctl --version
```

Expected: OVS version 3.x or later. If OVS is not running:

```bash
sudo systemctl start openvswitch-switch
sudo systemctl enable openvswitch-switch
```

---

## 6. gtp5g Kernel Module

gtp5g is required by the free5GC UPF and must be compiled from source. The build process may require patches depending on your kernel version; resolve any compilation errors as they arise.

### 6.1 Clone and build

```bash
git clone https://github.com/free5gc/gtp5g.git
cd gtp5g
make
sudo make install
sudo modprobe gtp5g
```

Verify:
```bash
lsmod | grep gtp5g
```
Expected output: `gtp5g   163840  0`

### 6.2 After kernel updates

If the kernel updates, gtp5g must be rebuilt:

```bash
cd gtp5g
make clean
make
sudo make install
sudo modprobe gtp5g
```

The module is registered in `/etc/modules-load.d/gtp5g.conf` for auto-load on boot, but only for the current kernel version. A kernel update may require a rebuild.

---

## 7. Clone Project

```bash
git clone https://github.com/tormgibbs/sdn-drl-network-slicing
cd sdn-drl-network-slicing
```

Install Python dependencies:
```bash
uv sync
```

---

## 8. free5GC Deployment

### 8.1 Start the core

```bash
make core-up
make core-status
```

All 14 containers must show as running. If any container shows as Restarting, check its logs:

```bash
docker logs <container_name> 2>&1 | tail -30
```

### 8.2 Verify UPF is ready

UPF readiness means the PFCP listener is up and accepting connections, not just that the container started. Check with:

```bash
docker exec upf ss -lnup 2>/dev/null | grep ':8805'
```

If this returns output, UPF is ready. If it returns nothing, wait a few seconds and retry.

If UPF shows `operation not supported` in its logs, gtp5g is not loaded:

```bash
sudo modprobe gtp5g
docker restart upf
```

### 8.3 Verify SMF-UPF PFCP association

```bash
docker logs smf 2>&1 | grep -i "association"
```

Expected: a line containing `UPF(<ip>) setup association`. The UPF IP is dynamically assigned by Docker and will differ between runs.

If the association line does not appear, SMF may have cached a stale UPF address from a previous failed attempt. Restart SMF after confirming UPF is healthy:

```bash
docker restart smf
docker logs smf 2>&1 | grep -i "association"
```

---

## 9. Subscriber Registration

See [docs/subscriber-registration.md](subscriber-registration.md).

This is a one-time setup step. Subscriber data persists in MongoDB across restarts and does not need to be repeated unless the database volume is wiped.

---

## 10. UERANSIM -- gNB and UE Attach

The gNB starts automatically when `make core-up` runs. No manual gNB startup is required.

### 10.1 Verify gNB registered with AMF

```bash
docker logs amf 2>&1 | grep -i "ng-setup"
```

Expected: a line containing `Send NG-Setup response`.

### 10.2 Attach all UEs

```bash
make ue-attach
make ue-setup
```

`make ue-attach` starts all 5 UE processes simultaneously. `make ue-setup` polls until `ue1tun0` appears (up to 30 seconds) then adds routes for all 5 slices.

### 10.3 Verify tunnel interfaces

```bash
docker exec ueransim ip addr show | grep -E "ue[0-9]tun|inet 10.60"
```

Expected: 5 tunnel interfaces with deterministic names and correct IPs:

```
ue1tun0  inet 10.60.1.1
ue2tun0  inet 10.60.2.1
ue3tun0  inet 10.60.3.1
ue4tun0  inet 10.60.4.1
ue5tun0  inet 10.60.5.1
```

---

## 11. Mininet-WiFi, Network Setup, and Controller

### 11.1 Load required kernel modules

```bash
make module-load
```

### 11.2 Start topology

In Terminal 1:

```bash
make topology
```

Wait for the Mininet-WiFi CLI prompt to appear before proceeding. The topology script automatically:
- Associates all stations with their access points
- Configures per-station routes and ARP entries for UE return path
- Starts iperf3 servers on all sink stations (sta1, sta3, sta5, sta7, sta9)

### 11.3 Run network setup

In Terminal 2 (after topology CLI appears):

```bash
make network-setup
```

This script:
- Creates the s1-upf/upf-s1 veth pair
- Waits for OVS bridge s1 to be ready
- Waits for UPF PFCP listener on port 8805
- Adds s1-upf to OVS s1
- Adds upf-s1 to br-free5gc
- Creates upf-gw internal port with pinned MAC 02:00:00:00:0c:00
- Configures host and UPF container routes
- Configures UPF iptables NAT scoped to the UE pool (10.60.0.0/16)

### 11.4 Start the controller

In Terminal 2 (after network-setup completes):

```bash
make controller
```

The controller connects to all 8 switches and installs:
- VLAN-based forwarding rules on s1, s2, s3
- UPF ingress classification rules on s1 (IP-to-VLAN per slice)
- Return path rules on s1 (discovered via OpenFlow port description at connection time)
- HTB queues per slice on all 5 access points
- OpenFlow meters on s2 and s3
- MAC rewrite rules on all 5 access points

### 11.5 Attach UEs

```bash
make ue-attach && make ue-setup
```

### 11.6 Verify end-to-end

```bash
docker exec ueransim ping -I ue1tun0 10.0.1.1 -c 4
```

Expected: 3 or 4 received (first packet may drop on ARP resolution). A second run should show 0% loss. Verify all 5 slices:

```bash
docker exec ueransim ping -I ue2tun0 10.0.2.1 -c 4
docker exec ueransim ping -I ue3tun0 10.0.3.1 -c 4
docker exec ueransim ping -I ue4tun0 10.0.4.1 -c 4
docker exec ueransim ping -I ue5tun0 10.0.5.1 -c 4
```

### 11.7 Verify controller installed return path rules

```bash
strings logs/controller.log | grep "Return path rule installed"
```

Expected: 5 lines, one per slice.

### 11.8 Clean up

```bash
make down
```

---

## 12. Traffic Generation

See [docs/traffic-config.md](traffic-config.md) for full configuration reference and rate design rationale.

iperf3 servers start automatically on sink stations when `make topology` runs.

```bash
# Run one loop across all slices
uv run scripts/traffic_generator.py --loops 1

# Run continuously
make traffic-start

# Stop
make traffic-stop
```

---

## 13. Startup Sequence After Reboot

```bash
make core-up
make module-load

# Terminal 1
make topology

# Terminal 2 (after topology CLI appears)
make network-setup
make controller
make ue-attach && make ue-setup

# Optional: start traffic generation
make traffic-start
```

---

## 14. Known Issues and Workarounds

See [docs/known-issues.md](known-issues.md).

For 5GC-specific failure modes and diagnostic commands see [docs/debugging-5gc.md](debugging-5gc.md).
