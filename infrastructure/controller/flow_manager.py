# infrastructure/controller/flow_manager.py
# Installs OpenFlow 1.3 flow rules for VLAN-based slice classification.

import logging
from pathlib import Path

import yaml
from os_ken.ofproto import ofproto_v1_3 as ofproto
from os_ken.ofproto import ofproto_v1_3_parser as parser

logger = logging.getLogger(__name__)

"""
Port layout used by the topology
s1: port 1 -> s2, port 2 -> s3
s2: port 1 -> s1, port 2 -> ap1, port 3 -> ap2, port 4 -> ap3
s3: port 1 -> s1, port 2 -> ap4, port 3 -> ap5
ap*: port 1 -> wireless clients, port 2 -> switch
"""

_AP_SINK_MAC: dict[str, str] = {
	'ap1': '02:00:00:00:02:00',
	'ap2': '02:00:00:00:04:00',
	'ap3': '02:00:00:00:06:00',
	'ap4': '02:00:00:00:08:00',
	'ap5': '02:00:00:00:0a:00',
}

AP_WLAN_PORT = 1
AP_UPLINK_PORT = 2

_ap_vlan_map: dict[str, int] = {}
_dpid_role: dict[int, str] = {}
_subnet_vlan_map: dict[str, int] = {}
_upf_config: dict = {}
_topology: dict = {}
_slices_config: dict = {}

_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'
_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'


def _load_subnet_vlan_map() -> dict[str, int]:
	result = {}
	for slice_cfg in _slices_config.values():
		subnet = slice_cfg.get('ue_subnet')
		vlan = slice_cfg.get('vlan')
		if subnet and vlan:
			result[subnet] = vlan
	return result


def _load_upf_config() -> dict:
	return _topology.get('upf', {})


def set_dpid_map(dpid_to_name: dict[int, str]) -> None:
	global _topology, _slices_config

	with open(_TOPOLOGY_CONFIG) as f:
		_topology = yaml.safe_load(f)
	with open(_SLICES_CONFIG) as f:
		_slices_config = yaml.safe_load(f)['slices']

	_dpid_role.clear()
	for dpid, name in dpid_to_name.items():
		if name == 's1':
			_dpid_role[dpid] = 'core'
		elif name in ('s2', 's3'):
			_dpid_role[dpid] = 'aggregation'
		elif name.startswith('ap'):
			_dpid_role[dpid] = f'ap:{name}'

	logger.info('DPID roles: %s', _dpid_role)


def set_ap_vlan_map(ap_vlan_map: dict[str, int]) -> None:
	_ap_vlan_map.clear()
	_ap_vlan_map.update(ap_vlan_map)
	_subnet_vlan_map.clear()
	_subnet_vlan_map.update(_load_subnet_vlan_map())
	_upf_config.clear()
	_upf_config.update(_load_upf_config())
	logger.info('AP VLAN map registered: %s', _ap_vlan_map)
	logger.info('Subnet VLAN map loaded: %s', _subnet_vlan_map)
	logger.info('UPF config loaded: %s', _upf_config)


def is_core(dpid: int) -> bool:
	return _dpid_role.get(dpid) == 'core'


def is_aggregation(dpid: int) -> bool:
	return _dpid_role.get(dpid) == 'aggregation'


def is_ap(dpid: int) -> bool:
	return _dpid_role.get(dpid, '').startswith('ap:')


def get_ap_name(dpid: int) -> str | None:
	role = _dpid_role.get(dpid, '')
	if role.startswith('ap:'):
		return role[3:]
	return None


def get_ap_vlan(ap_name: str) -> int | None:
	return _ap_vlan_map.get(ap_name)


def reset_state() -> None:
	global _topology, _slices_config
	_dpid_role.clear()
	_ap_vlan_map.clear()
	_subnet_vlan_map.clear()
	_upf_config.clear()
	_topology = {}
	_slices_config = {}


def install_ap_rules(datapath: object, ap_name: str, vlan_id: int) -> None:
	ofp_parser = datapath.ofproto_parser

	match_untagged = ofp_parser.OFPMatch(
		in_port=AP_WLAN_PORT,
		vlan_vid=(0x0000, 0x1FFF),
	)
	actions_tag = [
		ofp_parser.OFPActionPushVlan(0x8100),
		ofp_parser.OFPActionSetField(vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT)),
		ofp_parser.OFPActionOutput(AP_UPLINK_PORT),
	]
	_add_flow(datapath, priority=10, match=match_untagged, actions=actions_tag)

	match_tagged = ofp_parser.OFPMatch(
		in_port=AP_UPLINK_PORT,
		vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT),
	)
	actions_strip = [
		ofp_parser.OFPActionPopVlan(),
		ofp_parser.OFPActionOutput(AP_WLAN_PORT),
	]
	_add_flow(datapath, priority=10, match=match_tagged, actions=actions_strip)

	sink_mac = _AP_SINK_MAC.get(ap_name)
	if sink_mac:
		match_rewrite = ofp_parser.OFPMatch(
			in_port=AP_UPLINK_PORT,
			eth_type=0x0800,
			vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT),
		)
		actions_rewrite = [
			ofp_parser.OFPActionPopVlan(),
			ofp_parser.OFPActionSetField(eth_dst=sink_mac),
			ofp_parser.OFPActionOutput(AP_WLAN_PORT),
		]
		_add_flow(datapath, priority=20, match=match_rewrite, actions=actions_rewrite)

	logger.info(
		'AP rules installed: dpid=%s ap=%s vlan=%s', datapath.id, ap_name, vlan_id
	)


def install_aggregation_rules(switch_name: str, datapath: object) -> None:
	ofp_parser = datapath.ofproto_parser

	aggregation_ports = _topology['topology']['aggregation_ports']
	ap_slice_map = _topology['topology']['ap_slice_map']

	port_config = aggregation_ports.get(switch_name)
	if port_config is None:
		logger.error(
			'No port config found for %s -- skipping aggregation rules', switch_name
		)
		return

	ap_ports = port_config['ap_ports']

	for ap_name in ap_ports:
		slice_name = ap_slice_map.get(ap_name)
		if slice_name is None:
			continue

		if slice_name not in _slices_config:
			logger.warning(
				'Slice %s in ap_slice_map but not in slices config -- skipping', slice_name
			)

	# Per-VLAN forwarding (both directions, meter attached) is installed by
	# meter_manager._install_meter_flow at priority=20. A separate unmetered
	# rule at equal-or-higher priority here would shadow it and the meter
	# would never be evaluated.
	_add_flow(datapath, priority=5, match=ofp_parser.OFPMatch(), actions=[])

	logger.info(
		'Aggregation rules installed: dpid=%s switch=%s', datapath.id, switch_name
	)


def install_core_rules(datapath: object) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	aggregation_ports = _topology['topology']['aggregation_ports']
	ap_slice_map = _topology['topology']['ap_slice_map']

	vlan_ids: set[int] = set()
	for port_config in aggregation_ports.values():
		for ap_name in port_config['ap_ports']:
			slice_name = ap_slice_map.get(ap_name)
			if slice_name and slice_name in _slices_config:
				vlan_ids.add(_slices_config[slice_name]['vlan'])

	for vlan_id in vlan_ids:
		match = ofp_parser.OFPMatch(
			vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT),
		)
		actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
		_add_flow(datapath, priority=10, match=match, actions=actions)
		logger.info(
			'Core VLAN rule installed: dpid=%s vlan=%d -> FLOOD',
			datapath.id,
			vlan_id,
		)

	match = ofp_parser.OFPMatch()
	actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
	_add_flow(datapath, priority=5, match=match, actions=actions)

	logger.info('Core rules installed: dpid=%s', datapath.id)


def install_upf_ingress_rules(datapath: object) -> None:
	if not _subnet_vlan_map:
		logger.warning('Subnet VLAN map is empty -- skipping UPF ingress rules')
		return

	core_ports = _topology['topology']['core_ports']['s1']
	aggregation_map = _topology['topology']['aggregation_map']
	ap_slice_map = _topology['topology']['ap_slice_map']

	vlan_to_port: dict[int, int] = {}
	for agg_switch, aps in aggregation_map.items():
		out_port = core_ports[agg_switch]
		for ap in aps:
			slice_name = ap_slice_map.get(ap)
			if slice_name and slice_name in _slices_config:
				vlan_to_port[_slices_config[slice_name]['vlan']] = out_port

	ofp_parser = datapath.ofproto_parser

	for subnet, vlan_id in _subnet_vlan_map.items():
		out_port = vlan_to_port.get(vlan_id)
		if out_port is None:
			logger.warning(
				'No output port found for vlan=%s subnet=%s -- skipping', vlan_id, subnet
			)
			continue

		ip_address, prefix_len = subnet.split('/')
		match = ofp_parser.OFPMatch(
			eth_type=0x0800,
			ipv4_src=(ip_address, _prefix_to_mask(int(prefix_len))),
		)
		actions = [
			ofp_parser.OFPActionPushVlan(0x8100),
			ofp_parser.OFPActionSetField(vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT)),
			ofp_parser.OFPActionOutput(out_port),
		]
		_add_flow(datapath, priority=20, match=match, actions=actions)
		logger.info(
			'UPF ingress rule installed: dpid=%s subnet=%s vlan=%s out_port=%s',
			datapath.id,
			subnet,
			vlan_id,
			out_port,
		)


def install_return_path_rules(datapath: object, s1_upf_port: int) -> None:
	if not _subnet_vlan_map:
		logger.warning('Subnet VLAN map empty -- skipping return path rules')
		return

	upf_mac = _upf_config.get('eth0_mac')
	if not upf_mac:
		logger.error(
			'UPF eth0_mac not in topology config -- cannot install return path rules'
		)
		return

	ofp_parser = datapath.ofproto_parser

	for subnet, vlan_id in _subnet_vlan_map.items():
		ip_address, prefix_len = subnet.split('/')
		match = ofp_parser.OFPMatch(
			vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT),
			eth_type=0x0800,
			ipv4_dst=(ip_address, _prefix_to_mask(int(prefix_len))),
		)
		actions = [
			ofp_parser.OFPActionPopVlan(),
			ofp_parser.OFPActionSetField(eth_dst=upf_mac),
			ofp_parser.OFPActionOutput(s1_upf_port),
		]
		_add_flow(datapath, priority=25, match=match, actions=actions)
		logger.info(
			'Return path rule installed: dpid=%s vlan=%s subnet=%s -> port=%s',
			datapath.id,
			vlan_id,
			subnet,
			s1_upf_port,
		)


def install_table_miss(datapath: object) -> None:
	match = parser.OFPMatch()
	_add_flow(datapath, priority=0, match=match, actions=[])
	logger.debug('Table-miss installed on dpid=%s', datapath.id)


def _prefix_to_mask(prefix_len: int) -> str:
	mask = (0xFFFFFFFF >> (32 - prefix_len)) << (32 - prefix_len)
	return '{}.{}.{}.{}'.format(
		(mask >> 24) & 0xFF,
		(mask >> 16) & 0xFF,
		(mask >> 8) & 0xFF,
		mask & 0xFF,
	)


def _add_flow(
	datapath: object, priority: int, match: object, actions: list[object]
) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
	mod = ofp_parser.OFPFlowMod(
		datapath=datapath,
		priority=priority,
		match=match,
		instructions=inst,
	)
	datapath.send_msg(mod)
