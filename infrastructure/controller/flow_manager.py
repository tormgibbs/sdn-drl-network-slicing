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
_upf_config: dict = {}

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


def _load_upf_config() -> dict:
	with open(_TOPOLOGY_CONFIG) as f:
		config = yaml.safe_load(f)
	return config.get('upf', {})


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
	_dpid_role.clear()
	_ap_vlan_map.clear()
	_subnet_vlan_map.clear()
	_upf_config.clear()


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

	if ap_name == 'ap1':
		match_rewrite = ofp_parser.OFPMatch(
			in_port=AP_UPLINK_PORT,
			eth_type=0x0800,
			vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT),
		)
		actions_rewrite = [
			ofp_parser.OFPActionPopVlan(),
			ofp_parser.OFPActionSetField(eth_dst='02:00:00:00:02:00'),
			ofp_parser.OFPActionOutput(AP_WLAN_PORT),
		]
		_add_flow(datapath, priority=20, match=match_rewrite, actions=actions_rewrite)

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
	Install IP-to-VLAN classification rules on s1 for UPF-originated traffic.
	Matches source IP subnet per slice, pushes the correct VLAN tag, and forwards
	out the s1 port toward the aggregation switch responsible for that slice.
	"""
	if not _subnet_vlan_map:
		logger.warning('Subnet VLAN map is empty -- skipping UPF ingress rules')
		return

	topology = _load_topology()
	with open(_SLICES_CONFIG) as f:
		slices_config = yaml.safe_load(f)['slices']

	core_ports = topology['topology']['core_ports']['s1']
	aggregation_map = topology['topology']['aggregation_map']
	ap_slice_map = topology['topology']['ap_slice_map']

	vlan_to_port: dict[int, int] = {}
	for agg_switch, aps in aggregation_map.items():
		out_port = core_ports[agg_switch]
		for ap in aps:
			slice_name = ap_slice_map.get(ap)
			if slice_name and slice_name in slices_config:
				vlan_to_port[slices_config[slice_name]['vlan']] = out_port

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
	"""
	Install return path rules on s1 for campus-to-UE traffic.
	Matches VLAN-tagged frames destined for UE subnets, strips the VLAN tag,
	rewrites eth_dst to UPF eth0 MAC, and forwards out s1-upf port.
	Called after port discovery on the core switch completes.
	"""
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
