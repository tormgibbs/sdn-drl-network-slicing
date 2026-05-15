#!/usr/bin/env python3
# infrastructure/controller/app.py
"""
Main entry point for the OS-Ken SDN controller.
Handles OpenFlow 1.3 switch connections.
"""

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3


class CampusController(app_manager.OSKenApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.logger.info('CampusController starting...')

	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		datapath = ev.msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		self.logger.info('Switch connected: dpid=%s', datapath.id)

		# install table miss flow entry to forward unmatched packets to the controller
		match = parser.OFPMatch()
		actions = [
			parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
		]
		self.add_flow(datapath, priority=0, match=match, actions=actions)

	def add_flow(self, datapath, priority, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(
			datapath=datapath, priority=priority, match=match, instructions=inst
		)
		datapath.send_msg(mod)
		self.logger.info('Flow installed on dpid=%s priority=%s', datapath.id, priority)
