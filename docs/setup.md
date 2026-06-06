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

The module is registered in `/etc/modules-load.d/gtp5g.conf` for auto-load on boot, but only for the current kernel version. A kernel update amy require a rebuild.

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

All 16 containers must show as running. If any container shows as Restarting, check its logs:

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

Go to http://localhost:5000 and log in with `admin` / `free5gc`.

Navigate to Subscribers and create five subscribers. For each subscriber, fill in the fields as follows. Only SUPI, SST, SD, and Static IP change per subscriber. All other fields are identical.

Common fields for all subscribers:

- Authentication Management Field (AMF): `8000`
- Authentication Method: `5G_AKA`
- Operator Code Type: `OPc`
- Operator Code Value: `8e27b6af0e692e750f32667a3b14605d`
- Permanent Authentication Key: `8baf473f2f8fd09487cccbd7097c6862`
- Subscribed UE AMBR Uplink: `1 Gbps`
- Subscribed UE AMBR Downlink: `2 Gbps`
- DNN: `internet`
- Default 5QI: `9`
- Delete all pre-filled Flow Rules
- Delete all pre-filled S-NSSAI entries, then add one new S-NSSAI per subscriber

Per-subscriber values:

| Subscriber | SUPI                     | SST | SD     | Static IP  |
|------------|--------------------------|-----|--------|------------|
| UE1 (VLE)  | imsi-208930000000001     | 1   | 000001 | 10.60.1.1  |
| UE2 (Portal) | imsi-208930000000002   | 1   | 000002 | 10.60.2.1  |
| UE3 (Admin) | imsi-208930000000003    | 1   | 000003 | 10.60.3.1  |
| UE4 (IoT)  | imsi-208930000000004     | 2   | 000004 | 10.60.4.1  |
| UE5 (General) | imsi-208930000000005  | 1   | 000005 | 10.60.5.1  |

To set the static IP, toggle the IPv4 Address switch ON inside the DNN configuration section and enter the IP. Click VERIFY to confirm the IP is within the configured static pool. It will only verify correctly after the SST and SD fields are set for that slice.

---

## 10. UERANSIM -- gNB and UE Attach

### 10.1 Start the gNB

```bash
docker exec -d ueransim ./nr-gnb -c ./config/gnbcfg.yaml
```

Verify gNB registered with AMF:

```bash
docker logs amf 2>&1 | tail -5
```

Expected: `Send NG-Setup response`

### 10.2 Attach UE1

```bash
docker exec ueransim ./nr-ue -c ./config/uecfg-ue1.yaml
```

Expected output (last lines):

```
Initial Registration is successful
PDU Session establishment is successful PSI[1]
Connection setup for PDU session[1] is successful, TUN interface[uesimtun0, 10.60.1.1] is up.
```

### 10.3 Verify tunnel interface

In a separate terminal:

```bash
docker exec ueransim ip addr show uesimtun0
```

Expected: `inet 10.60.1.1/16 scope global uesimtun0`

---

## 11. Mininet-WiFi, Network Setup, and Controller

### 11.1 Load required kernel modules

```bash
make network-setup
```

### 11.2 Start topology

In Terminal 1:

```bash
make topology
```

Wait for the Mininet-WiFi CLI prompt to appear before proceeding.

### 11.3 Run network setup

In Terminal 2 (after topology CLI appears):

```bash
make network-setup
```

This script:
- Waits for OVS bridge s1 to be ready
- Waits for UPF PFCP listener on port 8805
- Adds s1-upf to OVS s1 with a fixed port name
- Adds upf-s1 to br-free5gc
- Creates upf-gw internal port with pinned MAC 02:00:00:00:0c:00
- Configures host and UPF container routes
- Configures UPF iptables NAT scoped to the UE pool

### 11.4 Start the controller

In Terminal 2 (after network-setup completes):

```bash
make controller
```

The controller connects to all 8 switches and installs flow rules including:
- VLAN-based forwarding on s1, s2, s3
- UPF ingress classification rules on s1
- Return path rules on s1 (discovered via OpenFlow port description at connection time)
- HTB queues and OpenFlow meters per slice
- ap1 MAC rewrite rule for sta1

### 11.5 Attach UE1

```bash
make ue-attach && make ue-setup
```

ue-setup polls for uesimtun0 with a 30-second timeout and adds the campus route once the interface appears.

### 11.6 Verify end-to-end

```bash
docker exec ueransim ping -I uesimtun0 10.0.1.1 -c 4
```

Expected: 4 packets transmitted, 3 or 4 received (first packet may drop due to ARP resolution). A second run should show 0% loss.

### 11.7 Verify controller installed return path rules

```bash
strings logs/controller.log | grep "Return path rule installed"
```

Expected: 5 lines, one per slice.

### 11.8 Clean up

make down

---

## 12. Known Issues and Workarounds

**gtp5g lost after kernel update**
The module is installed per kernel version. After any kernel update, rebuild from source (see Section 4.3).

**Station auto-association not working**
Mininet-WiFi does not automatically trigger wpa_supplicant per station. Use manual `iw connect` as shown in Section 9.4. Root cause not yet identified.

**OVS meters not enforced on kernel 7.x**
OpenFlow meters are installed but not enforced in the kernel datapath. HTB queues provide the bandwidth floor. Meter enforcement is pending empirical verification.

**UPF fails to start with "operation not supported"**
gtp5g module is not loaded. Run `sudo modprobe gtp5g` then `docker restart upf`.

**SMF panic: invalid argument to Intn**
Caused by staticPools CIDR matching the full dynamic pool CIDR. Fixed by setting staticPools to /32 per UE. Already applied in smfcfg.yaml.

**docker compose version warning**
The `version` attribute in docker-compose.yaml is obsolete in Compose v2. The warning is harmless and can be ignored.

**OVS does not emit port status events for ports added via ovs-vsctl**
OFPPR_ADD is unreliable when adding ports to a connected OVS bridge via ovs-vsctl. The controller discovers runtime-added ports via the OpenFlow handshake port description reply instead. Do not rely on EventOFPPortStatus for this purpose.

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
```
