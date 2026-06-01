# infrastructure/controller/meter_manager.py
# Installs and updates OpenFlow meters on aggregation switches (s2, s3).
# Meters enforce dynamic per-slice bandwidth ceilings set by the DRL agent.

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'
_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'

# Meter ID assigned per AP port on each aggregation switch.
# Meter IDs must be unique per datapath.
# s2: ap1=1, ap2=2, ap3=3
# s3: ap4=1, ap5=2
_METER_ID_BY_AP: dict[str, int] = {
	'ap1': 1,
	'ap2': 2,
	'ap3': 3,
	'ap4': 1,
	'ap5': 2,
}

# Cache of datapath objects keyed by switch name, populated by app.py
_datapaths: dict[str, object] = {}


def _load_topology() -> dict:
	with open(_TOPOLOGY_CONFIG) as f:
		return yaml.safe_load(f)


def _load_slices() -> dict:
	with open(_SLICES_CONFIG) as f:
		return yaml.safe_load(f)


def register_datapath(switch_name: str, datapath: object) -> None:
	_datapaths[switch_name] = datapath
	logger.info('Datapath registered: %s', switch_name)


def install_meters(allocations: dict[str, float]) -> None:
	"""
	Install or update OpenFlow meters on s2 and s3 based on DRL allocations.

	allocations: dict mapping slice name to fraction of total bandwidth.
	Example: {'vle': 0.4, 'student_portal': 0.2, 'admin': 0.15, 'iot': 0.05, 'general': 0.2}
	Fractions must sum to 1.0.
	"""
	topology = _load_topology()
	slices = _load_slices()

	total_bw = slices['network']['total_bandwidth_bps']
	ap_slice_map = topology['topology']['ap_slice_map']
	aggregation_ports = topology['topology']['aggregation_ports']

	# Build slice -> AP mapping (inverse of ap_slice_map)
	slice_ap_map = {v: k for k, v in ap_slice_map.items()}

	for switch_name, ap_ports in aggregation_ports.items():
		datapath = _datapaths.get(switch_name)
		if datapath is None:
			logger.error('Datapath not registered for switch %s', switch_name)
			continue

		for ap_name, port_no in ap_ports.items():
			slice_name = ap_slice_map.get(ap_name)
			if slice_name is None:
				logger.error('No slice mapped to AP %s', ap_name)
				continue

			fraction = allocations.get(slice_name, 0.0)
			rate_bps = int(fraction * total_bw)

			# Enforce minimum floor -- never set meter below slice min_throughput
			min_bps = slices['slices'][slice_name]['min_throughput_bps']
			rate_bps = max(rate_bps, min_bps)

			meter_id = _METER_ID_BY_AP[ap_name]
			_install_or_update_meter(datapath, meter_id, port_no, rate_bps)
			logger.info(
				'Meter updated: switch=%s ap=%s slice=%s port=%d meter_id=%d rate=%d bps',
				switch_name,
				ap_name,
				slice_name,
				port_no,
				meter_id,
				rate_bps,
			)


def _install_or_update_meter(
	datapath: object, meter_id: int, port_no: int, rate_kbps_or_bps: int
) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	# OpenFlow meter rates are in kbps
	rate_kbps = max(1, rate_kbps_or_bps // 1000)

	bands = [
		ofp_parser.OFPMeterBandDrop(
			type_=ofp.OFPMBT_DROP,
			rate=rate_kbps,
			burst_size=0,
		)
	]

	# OFPMC_ADD on first install, OFPMC_MODIFY on update.
	# Using OFPMC_MODIFY on a non-existent meter will fail silently on some
	# OVS versions. Send ADD first, ignore error if meter already exists,
	# then use MODIFY for subsequent updates. Simplest approach: always DELETE
	# then ADD to guarantee clean state.
	_delete_meter(datapath, meter_id)

	meter_mod = ofp_parser.OFPMeterMod(
		datapath=datapath,
		command=ofp.OFPMC_ADD,
		flags=ofp.OFPMF_KBPS,
		meter_id=meter_id,
		bands=bands,
	)
	datapath.send_msg(meter_mod)

	# Install flow rule to apply meter to traffic on this port
	match = ofp_parser.OFPMatch(in_port=port_no)
	inst = [
		ofp_parser.OFPInstructionMeter(meter_id),
		ofp_parser.OFPInstructionActions(
			ofp.OFPIT_APPLY_ACTIONS,
			[ofp_parser.OFPActionOutput(ofp.OFPP_NORMAL)],
		),
	]
	flow_mod = ofp_parser.OFPFlowMod(
		datapath=datapath,
		priority=15,
		match=match,
		instructions=inst,
	)
	datapath.send_msg(flow_mod)


def _delete_meter(datapath: object, meter_id: int) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser
	meter_mod = ofp_parser.OFPMeterMod(
		datapath=datapath,
		command=ofp.OFPMC_DELETE,
		flags=ofp.OFPMF_KBPS,
		meter_id=meter_id,
		bands=[],
	)
	datapath.send_msg(meter_mod)
