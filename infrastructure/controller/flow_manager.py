# infrastructure/controller/flow_manager.py
# # Installs OpenFlow 1.3 flow rules for VLAN-based slice classification.

import logging

from os_ken.ofproto import ofproto_v1_3 as ofproto
from os_ken.ofproto import ofproto_v1_3_parser as parser

logger = logging.getLogger(__name__)

CORE_DPIDS = {1}
AGG_DPIDS = {2, 3}

_ap_vlan_map = {}
_ap_dpid_map = {}


def set_ap_vlan_map(ap_vlan_map):
	global _ap_vlan_map
	_ap_vlan_map = ap_vlan_map
	logger.info('AP VLAN map registered: %s', _ap_vlan_map)


def register_ap_dpid(ap_name, dpid):
	_ap_dpid_map[dpid] = ap_name
	logger.info('Registered AP dpid=%s -> %s', dpid, ap_name)


def is_core(dpid):
	return dpid in CORE_DPIDS


def is_aggregation(dpid):
	return dpid in AGG_DPIDS


def is_ap(dpid):
	return dpid in _ap_dpid_map


def install_table_miss(datapath):
	match = parser.OFPMatch()
	_add_flow(datapath, priority=0, match=match, actions=[])
	logger.debug('Table-miss installed on dpid=%s', datapath.id)


def install_ap_rules(datapath, ap_name, vlan_id):
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	match_untagged = ofp_parser.OFPMatch(vlan_vid=0x0000)
	actions_tag = [
		ofp_parser.OFPActionPushVlan(0x8100),
		ofp_parser.OFPActionSetField(vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT)),
		ofp_parser.OFPActionOutput(ofp.OFPP_NORMAL),
	]
	_add_flow(datapath, priority=10, match=match_untagged, actions=actions_tag)

	match_tagged = ofp_parser.OFPMatch(vlan_vid=(vlan_id | ofproto.OFPVID_PRESENT))
	actions_strip = [
		ofp_parser.OFPActionPopVlan(),
		ofp_parser.OFPActionOutput(ofp.OFPP_NORMAL),
	]
	_add_flow(datapath, priority=10, match=match_tagged, actions=actions_strip)

	logger.info(
		'AP rules installed: dpid=%s ap=%s vlan=%s', datapath.id, ap_name, vlan_id
	)


def install_aggregation_rules(datapath):
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	match = ofp_parser.OFPMatch()
	actions = [ofp_parser.OFPActionOutput(ofp.OFPP_NORMAL)]
	_add_flow(datapath, priority=5, match=match, actions=actions)

	logger.info('Aggregation rules installed: dpid=%s', datapath.id)


def install_core_rules(datapath):
	ofp = datapath.ofproto
	ofp_parser = datapath.ofproto_parser

	match = ofp_parser.OFPMatch()
	actions = [ofp_parser.OFPActionOutput(ofp.OFPP_NORMAL)]
	_add_flow(datapath, priority=5, match=match, actions=actions)

	logger.info('Core rules installed: dpid=%s', datapath.id)


def _add_flow(datapath, priority, match, actions):
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
