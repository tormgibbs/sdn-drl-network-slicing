# infrastructure/controller/stats_collector.py
# Collects OpenFlow port statistics from aggregation switches and maintains
# a per-slice cache for non-blocking reads by the REST layer.

import logging
import threading
import time
from pathlib import Path

import yaml
from os_ken.lib import hub

logger = logging.getLogger(__name__)

_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'

_stats_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
_datapaths: dict[str, object] = {}
_running = False
_interval_sec: int = 5


_prev_bytes: dict[str, int] = {}
_prev_time: dict[str, float] = {}


def _load_topology() -> dict:
	with open(_TOPOLOGY_CONFIG) as f:
		return yaml.safe_load(f)


def register_datapath(switch_name: str, datapath: object) -> None:
	_datapaths[switch_name] = datapath
	logger.info('Stats collector: datapath registered: %s', switch_name)


def get_stats() -> dict[str, dict]:
	with _cache_lock:
		return dict(_stats_cache)


def start(interval_sec: int = 5) -> None:
	global _running, _interval_sec
	_interval_sec = interval_sec
	_running = True
	hub.spawn(_collection_loop)
	logger.info('Stats collector started, interval=%ds', interval_sec)


def stop() -> None:
	global _running
	_running = False
	logger.info('Stats collector stopped')


def _collection_loop() -> None:
	while _running:
		_request_stats()
		hub.sleep(_interval_sec)


def _request_stats() -> None:
	topology = _load_topology()

	aggregation_ports = topology['topology']['aggregation_ports']

	for switch_name in aggregation_ports:
		datapath = _datapaths.get(switch_name)
		if datapath is None:
			logger.warning('Stats collector: datapath not available for %s', switch_name)
			continue
		ofp_parser = datapath.ofproto_parser
		req = ofp_parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY)
		datapath.send_msg(req)


def handle_port_stats_reply(switch_name: str, stats: list) -> None:
	topology = _load_topology()
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
	for stat in stats:
		slice_name = port_slice_map.get(stat.port_no)
		if slice_name is None:
			continue

		tx_key = f'{switch_name}:{stat.port_no}:tx'
		rx_key = f'{switch_name}:{stat.port_no}:rx'

		prev_tx = _prev_bytes.get(tx_key, 0)
		prev_rx = _prev_bytes.get(rx_key, 0)
		prev_time = _prev_time.get(tx_key, now)
		elapsed = now - prev_time

		if elapsed > 0:
			tx_throughput_bps = ((stat.tx_bytes - prev_tx) * 8) / elapsed
			rx_throughput_bps = ((stat.rx_bytes - prev_rx) * 8) / elapsed
		else:
			tx_throughput_bps = 0.0
			rx_throughput_bps = 0.0

		_prev_bytes[tx_key] = stat.tx_bytes
		_prev_bytes[rx_key] = stat.rx_bytes
		_prev_time[tx_key] = now

		with _cache_lock:
			_stats_cache[slice_name] = {
				'tx_bytes': stat.tx_bytes,
				'rx_bytes': stat.rx_bytes,
				'tx_packets': stat.tx_packets,
				'rx_packets': stat.rx_packets,
				'tx_errors': stat.tx_errors,
				'rx_errors': stat.rx_errors,
				'duration_sec': stat.duration_sec,
				'tx_throughput_bps': max(0.0, tx_throughput_bps),
				'rx_throughput_bps': max(0.0, rx_throughput_bps),
			}

	logger.debug('Stats cache updated for switch=%s', switch_name)
