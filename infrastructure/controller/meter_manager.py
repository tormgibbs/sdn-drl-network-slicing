# infrastructure/controller/meter_manager.py

import logging
from pathlib import Path

import yaml

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
		self._current_allocations: dict[str, float] = {}
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

	def register_datapath(self, switch_name: str, datapath: object) -> None:
		self._datapaths[switch_name] = datapath
		logger.info('Datapath registered: %s', switch_name)

		if not _AGGREGATION_SWITCHES.issubset(self._datapaths.keys()):
			return

		if not self._initialized:
			logger.info('All aggregation switches registered -- installing default meters')
			self._install_default_meters()
			self._initialized = True
		else:
			logger.warning(
				'Aggregation switch reconnected: %s -- re-applying current allocations',
				switch_name,
			)
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

		for switch_name in aggregation_ports:
			self._install_meters_for_switch(switch_name, rates_kbps, topology, slices)

		return rates_kbps

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

			self._replace_meter(datapath, meter_id, rate_kbps)
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

	def _replace_meter(self, datapath: object, meter_id: int, rate_kbps: int) -> None:
		"""
		Replace an OpenFlow meter. rate_kbps must already be a final,
		floor-respecting rate -- this function does not clamp or convert units.
		"""
		ofp = datapath.ofproto
		ofp_parser = datapath.ofproto_parser

		# OFPMC_MODIFY silently fails on OVS when the meter does not exist yet.
		# Delete unconditionally before adding to guarantee consistent state.
		datapath.send_msg(
			ofp_parser.OFPMeterMod(
				datapath=datapath,
				command=ofp.OFPMC_DELETE,
				flags=ofp.OFPMF_KBPS,
				meter_id=meter_id,
				bands=[],
			)
		)

		rate_kbps = max(1, rate_kbps)
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
