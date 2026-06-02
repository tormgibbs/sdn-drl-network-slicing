# infrastructure/controller/meter_manager.py

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'
_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'

# Meter IDs are datapath-scoped. ap4 and ap1 can share ID 1 because they
# are on different switches (s3 and s2 respectively).
_METER_ID_BY_AP: dict[str, int] = {
	'ap1': 1,
	'ap2': 2,
	'ap3': 3,
	'ap4': 1,
	'ap5': 2,
}

_AGGREGATION_SWITCHES = frozenset({'s2', 's3'})

_datapaths: dict[str, object] = {}
_current_allocations: dict[str, float] = {}
_initialized: bool = False


def _load_topology() -> dict:
	with open(_TOPOLOGY_CONFIG) as f:
		return yaml.safe_load(f)


def _load_slices() -> dict:
	with open(_SLICES_CONFIG) as f:
		return yaml.safe_load(f)


def register_datapath(switch_name: str, datapath: object) -> None:
	_datapaths[switch_name] = datapath
	logger.info('Datapath registered: %s', switch_name)

	if _AGGREGATION_SWITCHES.issubset(_datapaths.keys()):
		logger.info('All aggregation switches registered -- installing default meters')
		_install_default_meters()


def _install_default_meters() -> None:
	slices = _load_slices()
	slice_names = list(slices['slices'].keys())
	equal_share = 1.0 / len(slice_names)
	install_meters({name: equal_share for name in slice_names})


def install_meters(allocations: dict[str, float]) -> None:
	"""
	Install or replace OpenFlow meters on s2 and s3.

	allocations maps slice name to a fraction of total bandwidth [0.0, 1.0].
	Rate is floored at min_throughput_bps regardless of the allocated fraction.

	Meters match on vlan_vid + in_port in both directions -- AP-facing ingress
	(uplink) and core-facing ingress (downlink) -- so the ceiling applies to
	the full slice traffic budget.
	"""
	topology = _load_topology()
	slices = _load_slices()

	total_bw = slices['network']['total_bandwidth_bps']
	ap_slice_map = topology['topology']['ap_slice_map']
	aggregation_ports = topology['topology']['aggregation_ports']

	for switch_name, port_config in aggregation_ports.items():
		datapath = _datapaths.get(switch_name)
		if datapath is None:
			logger.error('install_meters called but datapath not registered: %s', switch_name)
			continue

		core_port = port_config['core_port']
		ap_ports = port_config['ap_ports']

		metered_vlans: set[int] = set()

		for ap_name, ap_port_no in ap_ports.items():
			slice_name = ap_slice_map.get(ap_name)
			if slice_name is None:
				logger.error('No slice mapped to AP %s in topology config', ap_name)
				continue

			slice_cfg = slices['slices'][slice_name]
			vlan_id = slice_cfg['vlan']
			fraction = allocations.get(slice_name, 0.0)
			rate_bps = int(fraction * total_bw)
			min_bps = slice_cfg['min_throughput_bps']
			rate_bps = max(rate_bps, min_bps)  # floor at SLA minimum regardless of allocation

			meter_id = _METER_ID_BY_AP[ap_name]
			_replace_meter(datapath, meter_id, rate_bps)

			_install_meter_flow(datapath, meter_id, vlan_id, ap_port_no)

			if vlan_id not in metered_vlans:
				_install_meter_flow(datapath, meter_id, vlan_id, core_port)
				metered_vlans.add(vlan_id)

			logger.info(
				'Meter installed: switch=%s slice=%s vlan=%d meter_id=%d rate=%d bps',
				switch_name,
				slice_name,
				vlan_id,
				meter_id,
				rate_bps,
			)


def _replace_meter(datapath: object, meter_id: int, rate_bps: int) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	# Delete before add -- OFPMC_MODIFY silently fails on non-existent meters in OVS.
	datapath.send_msg(
		ofp_parser.OFPMeterMod(
			datapath=datapath,
			command=ofp.OFPMC_DELETE,
			flags=ofp.OFPMF_KBPS,
			meter_id=meter_id,
			bands=[],
		)
	)

	rate_kbps = max(1, rate_bps // 1000)
	datapath.send_msg(
		ofp_parser.OFPMeterMod(
			datapath=datapath,
			command=ofp.OFPMC_ADD,
			flags=ofp.OFPMF_KBPS,
			meter_id=meter_id,
			bands=[
				ofp_parser.OFPMeterBandDrop(
					type_=ofp.OFPMBT_DROP,
					rate=rate_kbps,
					burst_size=0,
				)
			],
		)
	)


def _install_meter_flow(
	datapath: object, meter_id: int, vlan_id: int, port_no: int
) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser
	# Meter-only instructions drop on OVS — verified on this deployment.
	# Forwarding action must be explicit. FLOOD preserves single-table pipeline
	# without requiring goto-table or duplicate forwarding logic.
	inst = [
		ofp_parser.OFPInstructionMeter(meter_id),
		ofp_parser.OFPInstructionActions(
			ofp.OFPIT_APPLY_ACTIONS,
			[ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)],
		),
	]
	datapath.send_msg(
		ofp_parser.OFPFlowMod(
			datapath=datapath,
			priority=15,
			match=ofp_parser.OFPMatch(
				in_port=port_no,
				vlan_vid=(vlan_id | 0x1000),
			),
			instructions=inst,
		)
	)
