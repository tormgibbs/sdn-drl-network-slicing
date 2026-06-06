# 5GC and Data Path Debugging Guide

This document captures specific failure modes, diagnostic commands, and dead ends from debugging the free5GC + UERANSIM + Mininet-WiFi + OVS data path in this testbed. It is not a generic free5GC guide. It reflects what actually happened in this setup and what resolved each problem.

---

## Diagnostic Commands That Work in This Setup

**UPF GTP tunnel traffic counters:**
```bash
docker exec upf ip -s link show upfgtp
```
RX = uplink packets decapsulated from UE. TX = downlink packets encapsulated toward UE. TX errors mean gtp5g is attempting encapsulation but failing. Zero TX with nonzero RX means the return path is broken, not the forward path.

**Return path ethernet headers:**
```bash
sudo tcpdump -i upf-s1 -n -e icmp
```
The `-e` flag shows ethernet headers. Use this to confirm the dst MAC on return packets is UPF eth0's MAC, not upf-gw's MAC. This was the root cause of the first return path failure.

**GTP-U traffic on the free5gc bridge:**
```bash
sudo tcpdump -i br-free5gc -n udp port 2152
```
Shows GTP-U encapsulated traffic between gNB (UERANSIM) and UPF. If you see traffic only from gNB to UPF (10.100.200.12 to 10.100.200.14) but nothing in the reverse direction, gtp5g is not encapsulating downlink packets.

**Controller log search:**
```bash
strings logs/controller.log | grep -i "keyword"
```
The controller log file is binary due to mixed output encoding. Plain `grep` will miss matches. Always use `strings` first.

**UPF PFCP listener readiness:**
```bash
docker exec upf ss -lnup | grep 8805
```
This is the correct readiness check for UPF. IP address presence in docker inspect only means the container started, not that UPF is ready to handle PFCP sessions.


**OVS port discovery:**
```bash
sudo ovs-ofctl show s1 -O OpenFlow13
sudo ovs-ofctl dump-ports-desc s1 -O OpenFlow13
```
Use dump-ports-desc to get the full port list including runtime-added ports like s1-upf. The port number for s1-upf changes across restarts and must be discovered dynamically.

---

## Failure Modes and Resolutions

### Return path 100% packet loss with correct forward path

**Symptom:** UE ping shows 100% loss. tcpdump on ap1-wlan1 shows ICMP request arriving at sta1 and reply being sent. tcpdump on upf-s1 shows reply with wrong dst MAC.

**Root cause:** The return path flow rule on s1 was stripping the VLAN tag and forwarding to s1-upf, but the dst MAC was set to upf-gw's MAC (02:00:00:00:0c:00) instead of UPF eth0's MAC. UPF eth0 dropped the frame at L2 before it reached the IP stack.

**Resolution:** The flow rule action must include `set_field:UPF_ETH0_MAC->eth_dst` before `output:s1-upf`. UPF eth0 MAC is now pinned to 02:00:00:00:00:ff in docker-compose.yaml via `mac_address` field and stored in topology.yaml under the `upf` block.

**Key diagnostic:** `sudo tcpdump -i upf-s1 -n -e icmp` -- look at the dst MAC on reply packets. It must match UPF eth0's MAC, not upf-gw's.


---

### GTP TX errors on upfgtp with zero TX packets

**Symptom:** `ip -s link show upfgtp` shows nonzero RX (uplink working) but zero TX and nonzero TX errors (downlink failing).

**Root cause:** In an earlier session this was caused by stale PFCP session state after a UPF restart. The PDR/FAR rules in gtp5g were cleared but the nr-ue process was still running with an orphaned PDU session.

**Resolution:** Kill nr-ue and reattach. The fresh PDU session establishment reinstalls PDR/FAR into gtp5g.

**Note:** TX errors can also appear when the return packet arrives at UPF eth0 with the wrong dst MAC (see failure mode above). Distinguish by checking whether TX errors increment when pings are sent.

---

### OFPPortDescStatsReply handler never fires

**Symptom:** Controller log shows `Discovered s1-upf port` never appears. Return path rules never installed. Flow table on s1 missing nw_dst=10.60.x.x entries.

**Root cause 1:** Handler registered for MAIN_DISPATCHER only, but the framework's automatic OFPPortDescStatsRequest fires during CONFIG_DISPATCHER. The reply arrives before the datapath transitions to MAIN_DISPATCHER and is dropped.

**Resolution 1:** Register the handler for both dispatchers:
```python
@set_ev_cls(ofp_event.EventOFPPortDescStatsReply, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
```

**Root cause 2:** Manual OFPPortDescStatsRequest sent in switch_features_handler in addition to the framework's automatic one, causing two replies and duplicate rule installation.

**Resolution 2:** Do not send a manual OFPPortDescStatsRequest. The OS-Ken/Ryu framework automatically sends one during the OpenFlow 1.3 handshake. Rely on that reply alone.

---

### OVS does not emit OFPPR_ADD when adding a port via ovs-vsctl

**Symptom:** `ovs-vsctl add-port s1 s1-upf` succeeds, port appears in OVS, but EventOFPPortStatus with reason OFPPR_ADD never fires in the controller.

**Root cause:** OVS does not reliably send OpenFlow port status notifications to the controller for ports added via ovs-vsctl on an already-connected switch. This is a known OVS behavior.

**Resolution:** Change the startup order so s1-upf exists before the controller connects. Run make network-setup before make controller. The framework's handshake OFPPortDescStatsRequest then discovers s1-upf at connection time.

**Dead ends tried:**
- `sudo ovs-ofctl mod-port s1 s1-upf up -O OpenFlow13` -- does not trigger OFPPR_MODIFY
- Handling OFPPR_MODIFY alongside OFPPR_ADD -- correct in theory but never fires in practice for this setup

---

### upf-s1 loses br-free5gc membership on restart

**Symptom:** Forward path broken. tcpdump on br-free5gc shows ICMP requests from UPF but they do not appear on upf-s1. Traffic exits br-free5gc directly without going through OVS.

**Root cause:** `docker compose down` removes the free5gc network and recreates it on the next `up`. The upf-s1 veth leg loses its bridge master on teardown.

**Resolution:** network-setup.sh runs `sudo ip link set upf-s1 master br-free5gc` on every startup. This is a required step and cannot be omitted.

---

### SMF PFCP association uses 0.0.0.0 after UPF restart

**Symptom:** SMF logs show PFCP association to 0.0.0.0 instead of UPF's actual IP. PDU sessions fail.

**Root cause:** SMF caches the UPF address from a previous failed association attempt. If UPF restarts after SMF has already tried and failed to associate, SMF retains the cached 0.0.0.0 address.

**Resolution:** Restart SMF after UPF is confirmed healthy. In the startup sequence, wait for UPF PFCP listener on port 8805 before proceeding, then restart SMF if needed.

---

### UPF eth0 MAC changes on every container recreation

**Symptom:** Return path flow rules installed with a hardcoded UPF MAC break after `make down && make up`. Docker assigns a new random MAC to UPF eth0 on each container recreation.

**Resolution:** Pin the MAC in docker-compose.yaml:
```yaml
networks:
  privnet:
    aliases:
      - upf.free5gc.org
    mac_address: "02:00:00:00:0a:00"
```
Store the pinned value in topology.yaml under the `upf` block. The controller reads it from there at startup.

**Dead end:** Writing the discovered MAC to topology.yaml at runtime from network-setup.sh. This makes a config file mutable at runtime, creates git noise, and breaks reproducibility.

---

### upf-gw MAC changes after port deletion and recreation

**Symptom:** sta1's hardcoded ARP entry for 10.60.1.1 stops working after clean-topology deletes and recreates upf-gw. OVS assigns a new random MAC to internal ports on creation.

**Resolution:** Pin the MAC at port creation in network-setup.sh:
```bash
sudo ovs-vsctl --may-exist add-port s1 upf-gw \
    -- set Interface upf-gw type=internal \
    -- set Interface upf-gw mac=\"02:00:00:00:0c:00\"
```
Note the escaped quotes -- OVS requires this syntax for the mac field in bash.

FROM free5gc/ueransim:latest
RUN apt-get update && \
    apt-get install -y --no-install-recommends iperf3 && \
    rm -rf /var/lib/apt/lists/*### Non-deterministic tunnel interface assignment for multiple UEs

**Symptom:** With multiple UEs attached, `uesimtun0` does not reliably correspond to UE1. Interface-to-UE mapping shifts between runs, causing routes added to `uesimtun0` to target the wrong UE.

**Root cause:** UERANSIM assigns tunnel interface indices in PDU session establishment order, which is non-deterministic when multiple `nr-ue` processes attach concurrently.

**Resolution:** Set `tunName` per UE config file. UERANSIM uses this as a prefix:

```yaml
# uecfg-ue1.yaml
tunName: ue1tun
```

This produces `ue1tun0`, `ue2tun0`, etc. — deterministic regardless of attach order. All five UE configs now have explicit `tunName` values. `make ue-setup` uses these hardcoded names for route configuration.

---

## Runtime State That Must Be Recreated After Every Restart

These are not persisted by OVS or Docker and must be applied by network-setup.sh on every startup:

- `sudo ovs-vsctl add-port s1 s1-upf` -- s1-upf added to OVS s1
- `sudo ip link set upf-s1 master br-free5gc` -- upf-s1 rejoined to br-free5gc
- `sudo ovs-vsctl add-port s1 upf-gw ... mac=...` -- upf-gw internal port with pinned MAC
- `sudo ip addr add 10.100.200.200/24 dev upf-gw` -- upf-gw IP address
- `sudo ip route add 10.0.0.0/8 dev upf-gw` -- host route for campus subnets
- `docker exec upf ip route add 10.0.0.0/8 via 10.100.200.200 dev eth0` -- UPF route to campus
- `docker exec upf iptables ...` -- UPF NAT rule scoped to UE pool only

---

## Startup Order

The correct startup order is:

1. make core-up
2. make module-load
3. make topology (Terminal 1, stays open)
4. make network-setup (Terminal 2, after topology CLI appears)
5. make controller (Terminal 2, after network-setup completes)
6. make ue-attach
7. make ue-setup

The controller must start after network-setup because s1-upf must exist in OVS before the controller connects to s1. The framework's OpenFlow handshake discovers s1-upf via OFPPortDescStatsReply and installs return path rules at that point.
