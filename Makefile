.PHONY: topology clean-topology core-up core-down core-status controller controller-bg module-load test ue-attach ue-status network-setup ue-setup up logs down

topology:
	sudo python3 infrastructure/topology/campus_topology.py

clean-topology:
	sudo mn -c
	sudo ovs-vsctl --if-exists del-port s1 s1-upf
	sudo ovs-vsctl --if-exists del-port s1 upf-gw
	sudo ovs-vsctl --all destroy QoS
	sudo ovs-vsctl --all destroy Queue

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

ue-status:
	docker exec ueransim ps aux | grep nr-ue

test:
	uv run pytest tests/ -v

network-setup:
	sudo bash scripts/network-setup.sh

ue-setup:
	@echo "Waiting for ue1tun0..."
	@i=0; until docker exec ueransim ip link show ue1tun0 >/dev/null 2>&1; do \
		i=$$((i+1)); [ $$i -ge 30 ] && echo "ERROR: ue1tun0 did not appear after 30s" && exit 1; \
		sleep 1; \
	done
	docker exec ueransim ip route add 10.0.0.0/8 dev ue1tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.2.0/24 dev ue2tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.3.0/24 dev ue3tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.4.0/24 dev ue4tun0 2>/dev/null || true
	docker exec ueransim ip route add 10.0.5.0/24 dev ue5tun0 2>/dev/null || true

logs:
	mkdir -p logs

controller-bg: logs
	sudo $(shell which uv) run infrastructure/controller/run.py > logs/controller.log 2>&1 &
	@echo "Controller started. Monitoring: tail -f logs/controller.log"

up: core-up module-load
	@echo ""
	@echo "Run the following in order:"
	@echo "  1. make topology          (Terminal 1 - stays open)"
	@echo "  2. make network-setup     (Terminal 2 - after topology CLI appears)"
	@echo "  3. make controller        (Terminal 2 - after network-setup completes)"
	@echo "  4. make ue-attach         (Terminal 2)"
	@echo "  5. make ue-setup          (Terminal 2)"

down:
	-docker exec ueransim pkill -f nr-ue 2>/dev/null || true
	make clean-topology
	make core-down
