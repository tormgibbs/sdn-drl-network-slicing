#!/usr/bin/env python3
# infrastructure/controller/app.py
"""
Main entry point for the OS-Ken SDN controller.
Handles OpenFlow 1.3 switch connections.
"""

import json
import os

import yaml
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3

from infrastructure.controller.agent_manager import AgentManager
from infrastructure.controller.flow_manager import (
	get_ap_name,
	get_ap_vlan,
	install_aggregation_rules,
	install_ap_rules,
	install_core_rules,
	install_return_path_rules,
	install_table_miss,
	install_upf_ingress_rules,
	is_aggregation,
	is_ap,
	is_core,
	set_ap_vlan_map,
	set_dpid_map,
)
from infrastructure.controller.meter_manager import MeterManager
from infrastructure.controller.rest_api import registry, start_api_server
from infrastructure.controller.stats_collector import StatsCollector
from infrastructure.controller.traffic_manager import TrafficManager

DPID_MAP_PATH = 'config/dpid_map.json'
SLICES_CONFIG_PATH = 'config/slices.yaml'
TOPOLOGY_CONFIG_PATH = 'config/topology.yaml'


def load_dpid_map() -> dict[int, str]:
	if not os.path.exists(DPID_MAP_PATH):
		raise RuntimeError(
			f'DPID map not found at {DPID_MAP_PATH}. Run the topology script first.'
		)
	with open(DPID_MAP_PATH) as f:
		raw = json.load(f)
	return {v: k for k, v in raw.items()}


def load_ap_vlan_map() -> dict[str, int]:
	with open(SLICES_CONFIG_PATH) as f:
		config = yaml.safe_load(f)
	return {slice_cfg['ap']: slice_cfg['vlan'] for slice_cfg in config['slices'].values()}


def load_stats_interval() -> int:
	with open(TOPOLOGY_CONFIG_PATH) as f:
		config = yaml.safe_load(f)
	return config['controller']['stats_interval_sec']


class CampusController(app_manager.OSKenApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.logger.info('CampusController starting...')
		self.dpid_to_name = load_dpid_map()
		self.logger.info('DPID map loaded: %s', self.dpid_to_name)
		set_dpid_map(self.dpid_to_name)
		set_ap_vlan_map(load_ap_vlan_map())
		self.meter_manager = MeterManager()
		self.stats_collector = StatsCollector(interval_sec=load_stats_interval())
		self.agent_manager = AgentManager()
		self.traffic_manager = TrafficManager()
		self.stats_collector.start()
		registry.register(
			self.stats_collector, self.meter_manager, self.agent_manager, self.traffic_manager
		)
		start_api_server(host='0.0.0.0', port=8080)

	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		datapath = ev.msg.datapath
		dpid = ev.msg.datapath_id
		if dpid is None:
			return
		datapath.id = dpid
		name = self.dpid_to_name.get(dpid, f'unknown({dpid})')
		self.logger.info('Switch connected: dpid=%s name=%s', dpid, name)

		if is_core(dpid):
			install_core_rules(datapath)
			install_upf_ingress_rules(datapath)
		elif is_aggregation(dpid):
			install_aggregation_rules(name, datapath)
			self.meter_manager.register_datapath(name, datapath)
			self.stats_collector.register_datapath(name, datapath)
		elif is_ap(dpid):
			ap_name = get_ap_name(dpid)
			if ap_name is None:
				self.logger.error('No AP name found for dpid=%s', dpid)
				return
			vlan_id = get_ap_vlan(ap_name)
			if vlan_id is None:
				self.logger.error('No VLAN configured for AP %s', ap_name)
				return
			install_ap_rules(datapath, ap_name, vlan_id)
		else:
			self.logger.warning('Unknown switch: dpid=%s', dpid)
			install_table_miss(datapath)

	@set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
	def port_stats_reply_handler(self, ev):
		datapath = ev.msg.datapath
		dpid = datapath.id
		name = self.dpid_to_name.get(dpid, '')
		if name in ('s2', 's3'):
			self.stats_collector.handle_port_stats_reply(name, ev.msg.body)

	@set_ev_cls(
		ofp_event.EventOFPMeterConfigStatsReply, [CONFIG_DISPATCHER, MAIN_DISPATCHER]
	)
	def meter_config_reply_handler(self, ev):
		datapath = ev.msg.datapath
		dpid = datapath.id
		name = self.dpid_to_name.get(dpid, '')
		if name in ('s2', 's3'):
			self.meter_manager.handle_meter_config_reply(name, ev.msg.body)

	@set_ev_cls(
		ofp_event.EventOFPPortDescStatsReply, [CONFIG_DISPATCHER, MAIN_DISPATCHER]
	)
	def port_desc_reply_handler(self, ev):
		datapath = ev.msg.datapath
		if not is_core(datapath.id):
			return
		for port in ev.msg.body:
			if port.name.decode('utf-8') == 's1-upf':
				self.logger.info('Discovered s1-upf port: %s', port.port_no)
				install_return_path_rules(datapath, port.port_no)
				return
		self.logger.error(
			'Port s1-upf not found on core switch -- return path rules not installed'
		)

	@set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
	def port_status_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		if not is_core(datapath.id):
			return
		desc = msg.desc
		port_name = desc.name.decode('utf-8')
		self.logger.info(
			'Port status event: name=%s port_no=%s reason=%s',
			port_name,
			desc.port_no,
			msg.reason,
		)
		if port_name == 's1-upf' and msg.reason in (
			datapath.ofproto.OFPPR_ADD,
			datapath.ofproto.OFPPR_MODIFY,
		):
			self.logger.info('s1-upf port added: port_no=%s', desc.port_no)
			install_return_path_rules(datapath, desc.port_no)

	@set_ev_cls(ofp_event.EventOFPErrorMsg, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
	def error_msg_handler(self, ev):
		msg = ev.msg
		dpid = msg.datapath.id
		name = self.dpid_to_name.get(dpid, f'unknown({dpid})')
		self.logger.error(
			'OFPErrorMsg: dpid=%s name=%s type=0x%02x code=0x%02x data=%s',
			dpid,
			name,
			msg.type,
			msg.code,
			msg.data,
		)
