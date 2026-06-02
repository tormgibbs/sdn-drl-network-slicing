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

AP_WLAN_PORT = 1
AP_UPLINK_PORT = 2

_ap_vlan_map: dict[str, int] = {}
_dpid_role: dict[int, str] = {}
_subnet_vlan_map: dict[str, int] = {}

_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'
_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'


def _load_subnet_vlan_map() -> dict[str, int]:
	with open(_SLICES_CONFIG) as f:
		config = yaml.safe_load(f)
	result = {}
	for slice_cfg in config['slices'].values():
		subnet = slice_cfg.get('ue_subnet')
		vlan = slice_cfg.get('vlan')
		if subnet and vlan:
			result[subnet] = vlan
	return result


def _load_topology() -> dict:
	with open(_TOPOLOGY_CONFIG) as f:
		return yaml.safe_load(f)


def set_dpid_map(dpid_to_name: dict[int, str]) -> None:
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
	logger.info('AP VLAN map registered: %s', _ap_vlan_map)
	logger.info('Subnet VLAN map loaded: %s', _subnet_vlan_map)


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
	_dpid_role.clear()
	_ap_vlan_map.clear()
	_subnet_vlan_map.clear()


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

	logger.info(
		'AP rules installed: dpid=%s ap=%s vlan=%s', datapath.id, ap_name, vlan_id
	)


def install_aggregation_rules(datapath: object) -> None:
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	match = ofp_parser.OFPMatch()
	actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
	_add_flow(datapath, priority=5, match=match, actions=actions)

	logger.info('Aggregation rules installed: dpid=%s', datapath.id)


def install_core_rules(datapath: object) -> None:
	"""
	Install VLAN-aware forwarding rules on s1.

	Tagged frames are flooded to reach both aggregation switches and directly
	connected hosts (h1). Tags are preserved end-to-end so downstream meter
	flows on s2/s3 can match on vlan_vid.
	"""

	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	topology = _load_topology()

	aggregation_ports = topology['topology']['aggregation_ports']
	ap_slice_map = topology['topology']['ap_slice_map']

	with open(_SLICES_CONFIG) as f:
		slices_config = yaml.safe_load(f)['slices']

	vlan_ids: set[int] = set()
	for port_config in aggregation_ports.values():
		for ap_name in port_config['ap_ports']:
			slice_name = ap_slice_map.get(ap_name)
			if slice_name:
				vlan_ids.add(slices_config[slice_name]['vlan'])

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
	"""
	Install IP-to-VLAN classification rules on s1 for traffic arriving from UPF.
	Matches on source IP subnet per slice, pushes the correct VLAN tag, floods
	to aggregation switches. Called once at controller startup for s1 only.
	"""
	if not _subnet_vlan_map:
		logger.warning('Subnet VLAN map is empty -- skipping UPF ingress rules')
		return

	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	for subnet, vlan_id in _subnet_vlan_map.items():
		ip_address, prefix_len = subnet.split('/')
		match = ofp_parser.OFPMatch(
			eth_type=0x0800,
			ipv4_src=(ip_address, _prefix_to_mask(int(prefix_len))),
		)
		actions = [
			ofp_parser.OFPActionPushVlan(0x8100),
			ofp_parser.OFPActionSetField(vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT)),
			ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD),
		]
		_add_flow(datapath, priority=20, match=match, actions=actions)
		logger.info(
			'UPF ingress rule installed: dpid=%s subnet=%s vlan=%s',
			datapath.id,
			subnet,
			vlan_id,
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
