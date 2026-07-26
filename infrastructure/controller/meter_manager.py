# infrastructure/controller/meter_manager.py

import logging
import threading
import time
from pathlib import Path

import yaml
from os_ken.lib import hub

from agent.project_allocation import project_allocation, validate_floors

logger = logging.getLogger(__name__)

_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'
_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'

# Meter IDs are datapath-scoped. ap1 and ap4 share ID 1 because they
# are on different datapaths (s2 and s3 respectively).
_METER_ID_BY_AP: dict[str, int] = {
	'ap1': 1,
	'ap2': 2,
	'ap3': 3,
	'ap4': 1,
	'ap5': 2,
}

_AGGREGATION_SWITCHES = frozenset({'s2', 's3'})


class MeterManager:
	def __init__(
		self,
		topology_config: Path = _TOPOLOGY_CONFIG,
		slices_config: Path = _SLICES_CONFIG,
	) -> None:
		self._topology_config = topology_config
		self._slices_config = slices_config
		self._datapaths: dict[str, object] = {}
		self._installed_meter_ids: set[tuple[str, int]] = set()
		self._meter_query_events: dict[str, threading.Event] = {}
		self._meter_query_done: set[str] = set()
		self._current_allocations: dict[str, float] = {}
		self._pending_barriers: dict[int, str] = {}
		self._change_confirmed_time: float = 0.0
		self._pending_since: float = 0.0
		self._last_pending_warning: float = 0.0
		self._initialized = False
		slices = self._load_slices()
		self.slice_order: list[str] = slices['slice_order']
		self.slice_names: frozenset[str] = frozenset(self.slice_order)

	def _load_topology(self) -> dict:
		with open(self._topology_config) as f:
			return yaml.safe_load(f)

	def _load_slices(self) -> dict:
		with open(self._slices_config) as f:
			data = yaml.safe_load(f)
		assert set(data['slice_order']) == set(data['slices'].keys()), (
			'slice_order and slices keys have diverged -- '
			f'slice_order={data["slice_order"]}, slices.keys()={list(data["slices"].keys())}'
		)
		return data

	def _query_existing_meters(self, switch_name: str, datapath: object) -> None:
		"""Controller restarts reset in-memory state but not OVS
		so meters must be discovered, not assumed empty."""
		ofp = datapath.ofproto
		ofp_parser = datapath.ofproto_parser
		event = threading.Event()
		self._meter_query_events[switch_name] = event

		req = ofp_parser.OFPMeterConfigStatsRequest(datapath, 0, ofp.OFPM_ALL)
		datapath.send_msg(req)

		if not event.wait(timeout=3.0):
			logger.warning(
				'Meter config query timed out for %s -- assuming no existing meters',
				switch_name,
			)

	def handle_meter_config_reply(self, switch_name: str, body: list) -> None:
		for meter in body:
			self._installed_meter_ids.add((switch_name, meter.meter_id))
		self._meter_query_done.add(switch_name)
		event = self._meter_query_events.pop(switch_name, None)
		if event is not None:
			event.set()
		logger.info(
			'Existing meters discovered on %s: %s',
			switch_name,
			[m.meter_id for m in body],
		)
		self._maybe_install_default_meters()

	def _maybe_install_default_meters(self) -> None:
		if not self._initialized and _AGGREGATION_SWITCHES.issubset(self._meter_query_done):
			logger.info('All meter queries complete -- installing default meters')
			self._install_default_meters()
			self._initialized = True

	def register_datapath(self, switch_name: str, datapath: object) -> None:
		self._datapaths[switch_name] = datapath
		logger.info('Datapath registered: %s', switch_name)

		if switch_name in _AGGREGATION_SWITCHES:
			hub.spawn(self._query_existing_meters, switch_name, datapath)

		if not _AGGREGATION_SWITCHES.issubset(self._datapaths.keys()):
			return

		if self._initialized:
			logger.warning(
				'Aggregation switch reconnected: %s -- re-applying current allocations',
				switch_name,
			)

			self._installed_meter_ids = {
				(sw, mid) for (sw, mid) in self._installed_meter_ids if sw != switch_name
			}
			self._meter_query_done.discard(switch_name)

			slices = self._load_slices()
			self._install_meters_for_switch(
				switch_name,
				self._compute_rates_kbps(self._current_allocations, slices),
				self._load_topology(),
				slices,
			)

	def _compute_rates_kbps(
		self, allocations: dict[str, float], slices: dict
	) -> dict[str, int]:
		slice_order = slices['slice_order']
		total_bw_kbps = slices['network']['total_bandwidth_bps'] // 1000
		floors_kbps = [
			slices['slices'][name]['min_throughput_bps'] // 1000 for name in slice_order
		]
		validate_floors(floors_kbps, total_bw_kbps)
		p = [allocations.get(name, 0.0) for name in slice_order]
		rates = project_allocation(p, floors_kbps, total_bw_kbps)
		return dict(zip(slice_order, rates))

	def _install_default_meters(self) -> None:
		slices = self._load_slices()
		slice_order = slices['slice_order']
		equal_share = 1.0 / len(slice_order)
		self.install_meters({name: equal_share for name in slice_order})

	def install_meters(self, allocations: dict[str, float]) -> dict[str, int]:
		"""
		Install or replace OpenFlow meters on all aggregation switches.

		allocations maps slice name to a fraction of total bandwidth [0.0, 1.0],
		as produced by the agent's policy. This function projects that fraction
		onto the floor-constrained simplex via project_allocation() and installs
		the resulting kbps rates -- floor enforcement happens exactly once,
		here, not in _install_meters_for_switch.

		Returns the actual installed rates in kbps, keyed by slice name. This
		is the single source of truth for what was installed -- callers (e.g.
		the REST API) should return this to the agent rather than letting it
		re-derive the projection independently.
		"""
		self._current_allocations = dict(allocations)
		topology = self._load_topology()
		slices = self._load_slices()
		aggregation_ports = topology['topology']['aggregation_ports']

		rates_kbps = self._compute_rates_kbps(allocations, slices)

		# Superseded by this call. Any barrier replies still in flight for a
		# prior allocation must not be mistaken for confirmation of this one.
		self._pending_barriers.clear()

		for switch_name in aggregation_ports:
			self._install_meters_for_switch(switch_name, rates_kbps, topology, slices)
			datapath = self._datapaths.get(switch_name)
			if datapath is None:
				continue
			ofp_parser = datapath.ofproto_parser
			barrier = ofp_parser.OFPBarrierRequest(datapath)
			datapath.send_msg(barrier)
			self._pending_barriers[barrier.xid] = switch_name

		if not self._pending_barriers:
			# No datapaths were available to barrier against. Treat as
			# confirmed immediately rather than waiting on nothing.
			self._change_confirmed_time = time.time()

		return rates_kbps

	def handle_barrier_reply(self, xid: int) -> None:
		switch_name = self._pending_barriers.pop(xid, None)
		if switch_name is None:
			return  # unknown or already-superseded xid
		if not self._pending_barriers:
			self._change_confirmed_time = time.time()
			logger.info(
				'Allocation change confirmed via barrier at %.6f', self._change_confirmed_time
			)

	def handle_datapath_disconnect(self, switch_name: str) -> None:
		# A disconnected switch can never send its barrier reply. Waiting
		# for one that will never arrive would wedge the collector forever.
		gone_xids = [x for x, sw in self._pending_barriers.items() if sw == switch_name]

		for xid in gone_xids:
			del self._pending_barriers[xid]

		if gone_xids and not self._pending_barriers:
			self._change_confirmed_time = time.time()
			logger.warning(
				'Barrier for %s abandoned -- switch disconnected before reply', switch_name
			)

	def check_barrier_watchdog(self) -> None:
		"""Logs, but never confirms. A stuck barrier must be fixed by a
		disconnect event or a fresh allocation, not by this check timing out."""
		if not self._pending_barriers:
			return

		topology = self._load_topology()
		controller_cfg = topology['controller']
		timeout_sec = controller_cfg.get('barrier_timeout_sec', 5.0)
		warn_interval_sec = controller_cfg.get('barrier_warn_interval_sec', 30.0)

		now = time.time()
		if now - self._pending_since < timeout_sec:
			return
		if now - self._last_pending_warning < warn_interval_sec:
			return
		self._last_pending_warning = now
		logger.warning(
			'Barrier still pending after %.1fs for switches: %s',
			now - self._pending_since,
			sorted(set(self._pending_barriers.values())),
		)

	def get_change_confirmed_time(self) -> float:
		return self._change_confirmed_time

	def _install_meters_for_switch(
		self,
		switch_name: str,
		rates_kbps: dict[str, int],
		topology: dict,
		slices: dict,
	) -> None:
		"""
		Install or replace OpenFlow meters on a single aggregation switch.

		rates_kbps maps slice name to its already-projected kbps rate, as
		produced by _compute_rates_kbps(). This function does not clamp or
		compute rates -- floor enforcement happens exactly once, upstream.
		"""
		ap_slice_map = topology['topology']['ap_slice_map']
		aggregation_ports = topology['topology']['aggregation_ports']

		datapath = self._datapaths.get(switch_name)
		if datapath is None:
			logger.error('No registered datapath for switch: %s', switch_name)
			return

		port_config = aggregation_ports[switch_name]
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

			rate_kbps = rates_kbps.get(slice_name)
			assert rate_kbps is not None, (
				f'no projected rate for slice {slice_name!r}: rates_kbps was built from '
				'slice_order and must cover every slice referenced in topology.yaml -- '
				'a missing key here means topology.yaml and slices.yaml have diverged'
			)

			meter_id = _METER_ID_BY_AP[ap_name]

			self._replace_meter(datapath, switch_name, meter_id, rate_kbps)
			self._install_meter_flow(datapath, meter_id, vlan_id, ap_port_no, core_port)

			if vlan_id not in metered_vlans:
				self._install_meter_flow(datapath, meter_id, vlan_id, core_port, ap_port_no)
				metered_vlans.add(vlan_id)

			logger.info(
				'Meter installed: switch=%s slice=%s vlan=%d meter_id=%d rate=%d kbps',
				switch_name,
				slice_name,
				vlan_id,
				meter_id,
				rate_kbps,
			)

	def _replace_meter(
		self, datapath: object, switch_name: str, meter_id: int, rate_kbps: int
	) -> None:
		"""Modifies rate in place; avoids the delete/add gap where meter_id briefly doesn't exist."""
		ofp = datapath.ofproto
		ofp_parser = datapath.ofproto_parser
		rate_kbps = max(1, rate_kbps)
		key = (switch_name, meter_id)

		command = ofp.OFPMC_MODIFY if key in self._installed_meter_ids else ofp.OFPMC_ADD

		datapath.send_msg(
			ofp_parser.OFPMeterMod(
				datapath=datapath,
				command=command,
				flags=ofp.OFPMF_KBPS,
				meter_id=meter_id,
				bands=[
					ofp_parser.OFPMeterBandDrop(
						type_=ofp.OFPMBT_DROP, rate=rate_kbps, burst_size=0
					)
				],
			)
		)
		self._installed_meter_ids.add(key)

	def _install_meter_flow(
		self, datapath: object, meter_id: int, vlan_id: int, in_port: int, out_port: int
	) -> None:
		ofp = datapath.ofproto
		ofp_parser = datapath.ofproto_parser
		# OVS requires an explicit output action alongside OFPInstructionMeter.
		# A meter instruction without a forwarding action causes silent drops.
		inst = [
			ofp_parser.OFPInstructionMeter(meter_id),
			ofp_parser.OFPInstructionActions(
				ofp.OFPIT_APPLY_ACTIONS,
				[ofp_parser.OFPActionOutput(out_port)],
			),
		]
		datapath.send_msg(
			ofp_parser.OFPFlowMod(
				datapath=datapath,
				priority=20,
				match=ofp_parser.OFPMatch(
					in_port=in_port,
					vlan_vid=(vlan_id | 0x1000),
				),
				instructions=inst,
			)
		)
