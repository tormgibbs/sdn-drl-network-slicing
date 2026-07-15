.PHONY: topology clean-topology core-up core-down core-status controller module-load test ue-attach ue-status network-setup ue-setup up down traffic-start traffic-stop ue-detach smf-restart

topology:
	sudo python3 infrastructure/topology/campus_topology.py

clean-topology:
	sudo mn -c
	sudo pkill -f iper'f3' 2>/dev/null || true
	sudo ovs-vsctl --if-exists del-br s1
	sudo ovs-vsctl --if-exists del-br s2
	sudo ovs-vsctl --if-exists del-br s3
	sudo ovs-vsctl --if-exists del-br ap1
	sudo ovs-vsctl --if-exists del-br ap2
	sudo ovs-vsctl --if-exists del-br ap3
	sudo ovs-vsctl --if-exists del-br ap4
	sudo ovs-vsctl --if-exists del-br ap5
	sudo ovs-vsctl --all destroy QoS
	sudo ovs-vsctl --all destroy Queue
	sudo ip link del s1-upf 2>/dev/null || true

core-up:
	cd infrastructure/free5gc && docker compose up -d

core-down:
	cd infrastructure/free5gc && docker compose down

core-status:
	cd infrastructure/free5gc && docker compose ps

controller:
	mkdir -p logs
	sudo $(shell which uv) run infrastructure/controller/run.py

module-load:
	sudo modprobe gtp5g
	sudo modprobe mac80211_hwsim
	lsmod | grep -E "gtp5g|mac80211_hwsim"

ue-attach:
	docker exec -d ueransim /ueransim/nr-ue -c /ueransim/config/uecfg-ue1.yaml
	docker exec -d ueransim /ueransim/nr-ue -c /ueransim/config/uecfg-ue2.yaml
	docker exec -d ueransim /ueransim/nr-ue -c /ueransim/config/uecfg-ue3.yaml
	docker exec -d ueransim /ueransim/nr-ue -c /ueransim/config/uecfg-ue4.yaml
	docker exec -d ueransim /ueransim/nr-ue -c /ueransim/config/uecfg-ue5.yaml

ue-detach:
	docker exec ueransim /ueransim/nr-cli imsi-208930000000001 --exec "deregister switch-off" 2>/dev/null || true
	docker exec ueransim /ueransim/nr-cli imsi-208930000000002 --exec "deregister switch-off" 2>/dev/null || true
	docker exec ueransim /ueransim/nr-cli imsi-208930000000003 --exec "deregister switch-off" 2>/dev/null || true
	docker exec ueransim /ueransim/nr-cli imsi-208930000000004 --exec "deregister switch-off" 2>/dev/null || true
	docker exec ueransim /ueransim/nr-cli imsi-208930000000005 --exec "deregister switch-off" 2>/dev/null || true
	@echo "Waiting for UEs to deregister..."
	@i=0; until [ "$$(docker exec ueransim /ueransim/nr-cli --dump 2>/dev/null | grep -c '^imsi-')" -eq 0 ]; do \
		i=$$((i+1)); [ $$i -ge 15 ] && echo "WARNING: not all UEs deregistered after 15s, proceeding" && break; \
		sleep 1; \
	done
	docker exec ueransim pkill -f nr-ue 2>/dev/null || true

ue-status:
	docker exec ueransim ps aux | grep nr-ue

smf-restart:
	make ue-detach
	docker restart upf
	@echo "Waiting for UPF PFCP listener..."
	@i=0; until docker exec upf ss -lnup 2>/dev/null | grep -q ':8805'; do \
		i=$$((i+1)); [ $$i -ge 30 ] && echo "ERROR: UPF did not become ready after 30s" && exit 1; \
		sleep 1; \
	done
	@echo "Reapplying UPF route and NAT rules (lost on container restart)..."
	docker exec upf ip route add 10.0.0.0/8 via 10.100.200.200 dev eth0 2>&1 || \
		echo "    WARN: UPF route add failed or already exists"
	docker exec upf iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || true
	docker exec upf iptables -t nat -A POSTROUTING -s 10.60.0.0/16 -o eth0 ! -d 10.0.0.0/8 -j MASQUERADE
	@SMF_TS=$$(date +%s); \
	docker restart smf; \
	echo "Waiting for SMF-UPF PFCP association..."; \
	i=0; until docker logs smf --since $$SMF_TS 2>&1 | grep -q "setup association"; do \
		i=$$((i+1)); [ $$i -ge 60 ] && echo "ERROR: SMF association not established after 60s" && exit 1; \
		sleep 1; \
	done; \
	echo "SMF-UPF association established."
	make ue-attach
	make ue-setup

test:
	uv run pytest tests/ -v

network-setup:
	sudo bash scripts/network-setup.sh

ue-setup:
	@for ue in ue1tun0 ue2tun0 ue3tun0 ue4tun0 ue5tun0; do \
		echo "Waiting for $$ue..."; \
		i=0; until docker exec ueransim ip link show $$ue >/dev/null 2>&1; do \
			i=$$((i+1)); [ $$i -ge 30 ] && echo "ERROR: $$ue did not appear after 30s" && exit 1; \
			sleep 1; \
		done; \
		echo "    $$ue ready"; \
	done
	docker exec ueransim ip addr change 10.60.1.1/24 dev ue1tun0
	docker exec ueransim ip addr change 10.60.2.1/24 dev ue2tun0
	docker exec ueransim ip addr change 10.60.3.1/24 dev ue3tun0
	docker exec ueransim ip addr change 10.60.4.1/24 dev ue4tun0
	docker exec ueransim ip addr change 10.60.5.1/24 dev ue5tun0
	docker exec ueransim ip route add 10.0.1.0/24 dev ue1tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.2.0/24 dev ue2tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.3.0/24 dev ue3tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.4.0/24 dev ue4tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.5.0/24 dev ue5tun0 2>/dev/null || true

up: core-up module-load
	@echo ""
	@echo "Run the following in order:"
	@echo "  1. make topology          (Terminal 1 - stays open)"
	@echo "  2. make network-setup     (Terminal 2 - after topology CLI appears)"
	@echo "  3. make controller        (Terminal 2 - after network-setup completes)"
	@echo "  4. make ue-attach         (Terminal 2)"
	@echo "  5. make ue-setup          (Terminal 2)"

down:
	-make ue-detach
	make clean-topology
	make core-down


traffic-start:
	sudo $(shell which uv) run scripts/traffic_generator.py

traffic-stop:
	pkill -f traffic_generator.py || true
