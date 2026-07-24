import logging
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3

logger = logging.getLogger(__name__)


class BarrierTimingTest(app_manager.OSKenApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	@set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
	def on_barrier_reply(self, ev):
		dpid = ev.msg.datapath.id
		logger.warning('[BARRIER TEST] BarrierReply dpid=%s at %.6f', dpid, time.time())
