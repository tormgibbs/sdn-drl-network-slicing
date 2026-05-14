.PHONY: topology clean-topology core-up core-down core-status module-load

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

module-load:
	sudo modprobe gtp5g
	sudo modprobe mac80211_hwsim
