# Known Issues and Workarounds

---

**gtp5g lost after kernel update**
The module is installed per kernel version. After any kernel update, rebuild from source (see setup.md Section 6).

---

**Station auto-association not working**
Mininet-WiFi does not automatically trigger wpa_supplicant per station. Use manual `iw connect` in the topology script. Root cause not yet identified.

---

**OVS meters not enforced on kernel 7.x**
OpenFlow meters are installed but not enforced in the kernel datapath. HTB queues provide the bandwidth floor. Meter enforcement is pending empirical verification.

---

**UPF fails to start with "operation not supported"**
gtp5g module is not loaded. Run `sudo modprobe gtp5g` then `docker restart upf`.

---

**SMF panic: invalid argument to Intn**
Caused by staticPools CIDR matching the full dynamic pool CIDR. Fixed by setting staticPools to /32 per UE. Already applied in smfcfg.yaml.

---

**docker compose version warning**
The `version` attribute in docker-compose.yaml is obsolete in Compose v2. The warning is harmless and can be ignored.

---

**OVS does not emit port status events for ports added via ovs-vsctl**
OFPPR_ADD is unreliable when adding ports to a connected OVS bridge via ovs-vsctl. The controller discovers runtime-added ports via the OpenFlow handshake port description reply instead. Do not rely on EventOFPPortStatus for this purpose. See docs/debugging-5gc.md for full details.

---

**Stale UE IP allocations after unclean teardown**
Symptom: `UE IP pool exhausted for DNN[internet] S-NSSAI[sst: X sd: XXXXXX]` in SMF logs. UE tunnel interface does not appear after `make ue-attach`.

Root cause: SMF rebuilds its in-memory IP pool from existing UPF GTP sessions on startup. If UEs are killed without deregistration, SMF marks their IPs as in use on next startup.

Workaround: always use `make down` followed by `make up` for full teardown and restart. Never restart SMF in isolation while UPF is running with active sessions.

Pending fix: add a UPF health check and `depends_on` ordering in docker-compose.yaml so SMF only establishes PFCP association after UPF has started cleanly.

---

**Stale iperf3 server processes after unclean topology teardown**
`mn -c` does not kill processes running in network namespaces. Multiple iperf3 server instances accumulate across restarts. `make clean-topology` now runs `sudo pkill -f iperf3` to clear them.

---

For 5GC-specific failure modes and diagnostic commands see `docs/debugging-5gc.md`.
