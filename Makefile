.PHONY: topology clean-topology core-up core-down core-status controller module-load test

topology:
	sudo python3 infrastructure/topology/campus_topology.py

clean-topology:
	sudo mn -c

core-up:
	cd infrastructure/free5gc && docker compose up -d

core-down:
	cd infrastructure/free5gc && docker compose down

core-status:
	cd infrastructure/free5gc && docker compose ps

controller:
	uv run infrastructure/controller/run.py

module-load:
	sudo modprobe gtp5g
	sudo modprobe mac80211_hwsim

test:
	uv run pytest tests/ -v