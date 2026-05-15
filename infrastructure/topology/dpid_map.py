# infrastructure/topology/dpid_map.py
# Handles writing and reading the DPID map file used by the controller.

import json
import os
from collections.abc import Sequence

DPID_MAP_PATH = 'config/dpid_map.json'


def export_dpid_map(switches: Sequence[object], path: str = DPID_MAP_PATH) -> None:
	data = {sw.name: int(sw.dpid, 16) for sw in switches}
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, 'w') as f:
		json.dump(data, f, indent=2)
