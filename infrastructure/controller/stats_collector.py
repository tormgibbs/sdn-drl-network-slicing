# infrastructure/controller/stats_collector.py
# Collects OpenFlow port statistics from aggregation switches and maintains
# a per-slice cache for non-blocking reads by the REST layer.

import logging
import time
from pathlib import Path

import yaml
from os_ken.lib import hub

logger = logging.getLogger(__name__)

_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'


class StatsCollector:
	def __init__(
		self,
		topology_config: Path = _TOPOLOGY_CONFIG,
		interval_sec: int = 5,
	) -> None:
		self._topology_config = topology_config
		self._interval_sec = interval_sec
		self._datapaths: dict[str, object] = {}
		self._stats_cache: dict[str, dict] = {}
		self._prev_bytes: dict[str, int] = {}
		self._prev_time: dict[str, float] = {}
		self._running = False
		self._topology: dict | None = None
		# hub.BoundedSemaphore is hub-aware. threading.Lock is not safe here
		# because get_stats() may be called from the REST handler, which may
		# run outside the hub's greenlet pool depending on WSGI configuration.
		self._cache_lock = hub.BoundedSemaphore(1)

	def _get_topology(self) -> dict:
		if self._topology is None:
			with open(self._topology_config) as f:
				self._topology = yaml.safe_load(f)
		return self._topology

	def register_datapath(self, switch_name: str, datapath: object) -> None:
		self._datapaths[switch_name] = datapath
		logger.info('Stats collector: datapath registered: %s', switch_name)

	def get_stats(self) -> dict[str, dict]:
		with self._cache_lock:
			return {
				slice_name: dict(metrics) for slice_name, metrics in self._stats_cache.items()
			}

	def start(self) -> None:
		if self._running:
			logger.warning('Stats collector already running -- ignoring start()')
			return
		self._running = True
		hub.spawn(self._collection_loop)
		logger.info('Stats collector started, interval=%ds', self._interval_sec)

	def stop(self) -> None:
		self._running = False
		logger.info('Stats collector stopped')

	def _collection_loop(self) -> None:
		while self._running:
			self._request_stats()
			hub.sleep(self._interval_sec)

	def _request_stats(self) -> None:
		topology = self._get_topology()
		aggregation_ports = topology['topology']['aggregation_ports']

		for switch_name in aggregation_ports:
			datapath = self._datapaths.get(switch_name)
			if datapath is None:
				logger.warning('Stats collector: datapath not available for %s', switch_name)
				continue
			ofp_parser = datapath.ofproto_parser
			req = ofp_parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY)
			datapath.send_msg(req)

	def handle_port_stats_reply(self, switch_name: str, stats: list) -> None:
		topology = self._get_topology()
		aggregation_ports = topology['topology']['aggregation_ports']
		ap_slice_map = topology['topology']['ap_slice_map']

		port_config = aggregation_ports.get(switch_name)
		if port_config is None:
			return

		ap_ports = port_config['ap_ports']
		port_slice_map: dict[int, str] = {}
		for ap_name, port_no in ap_ports.items():
			slice_name = ap_slice_map.get(ap_name)
			if slice_name:
				port_slice_map[port_no] = slice_name

		now = time.time()

		slice_accum: dict[str, dict] = {}

		for stat in stats:
			slice_name = port_slice_map.get(stat.port_no)
			if slice_name is None:
				continue

			tx_key = f'{switch_name}:{stat.port_no}:tx'
			rx_key = f'{switch_name}:{stat.port_no}:rx'

			prev_tx = self._prev_bytes.get(tx_key, 0)
			prev_rx = self._prev_bytes.get(rx_key, 0)
			prev_time = self._prev_time.get(tx_key, now)

			if stat.tx_bytes < prev_tx or stat.rx_bytes < prev_rx:
				self._prev_bytes[tx_key] = stat.tx_bytes
				self._prev_bytes[rx_key] = stat.rx_bytes
				self._prev_time[tx_key] = now
				logger.warning(
					'Port counter reset detected: switch=%s port=%d -- skipping interval',
					switch_name,
					stat.port_no,
				)
				continue

			self._prev_bytes[tx_key] = stat.tx_bytes
			self._prev_bytes[rx_key] = stat.rx_bytes
			self._prev_time[tx_key] = now

			elapsed = now - prev_time
			if elapsed > 0:
				port_tx_bps = ((stat.tx_bytes - prev_tx) * 8) / elapsed
				port_rx_bps = ((stat.rx_bytes - prev_rx) * 8) / elapsed
			else:
				port_tx_bps = 0.0
				port_rx_bps = 0.0

			if slice_name not in slice_accum:
				slice_accum[slice_name] = {
					'tx_bytes': 0,
					'rx_bytes': 0,
					'tx_packets': 0,
					'rx_packets': 0,
					'tx_errors': 0,
					'rx_errors': 0,
					'duration_sec': stat.duration_sec,
					'tx_throughput_bps': 0.0,
					'rx_throughput_bps': 0.0,
				}

			acc = slice_accum[slice_name]
			acc['tx_bytes'] += stat.tx_bytes
			acc['rx_bytes'] += stat.rx_bytes
			acc['tx_packets'] += stat.tx_packets
			acc['rx_packets'] += stat.rx_packets
			acc['tx_errors'] += stat.tx_errors
			acc['rx_errors'] += stat.rx_errors
			acc['tx_throughput_bps'] += port_tx_bps
			acc['rx_throughput_bps'] += port_rx_bps

		updated: dict[str, dict] = {}
		for slice_name, acc in slice_accum.items():
			updated[slice_name] = {
				'tx_bytes': acc['tx_bytes'],
				'rx_bytes': acc['rx_bytes'],
				'tx_packets': acc['tx_packets'],
				'rx_packets': acc['rx_packets'],
				'tx_errors': acc['tx_errors'],
				'rx_errors': acc['rx_errors'],
				'duration_sec': acc['duration_sec'],
				'tx_throughput_bps': max(0.0, acc['tx_throughput_bps']),
				'rx_throughput_bps': max(0.0, acc['rx_throughput_bps']),
			}

		with self._cache_lock:
			self._stats_cache.update(updated)

		logger.debug('Stats cache updated for switch=%s', switch_name)
