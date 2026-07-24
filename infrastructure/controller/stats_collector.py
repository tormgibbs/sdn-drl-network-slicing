# infrastructure/controller/stats_collector.py
# Collects per-slice metrics: throughput from OpenFlow port statistics,
# latency and loss from active ICMP probes through UE tunnels.

import asyncio
import json
import logging
import re
import subprocess
import threading
import time
from pathlib import Path

import yaml
from os_ken.lib import hub

from infrastructure.controller import rest_api

logger = logging.getLogger(__name__)

_UE_PROFILES_CONFIG = (
	Path(__file__).resolve().parents[2] / 'config' / 'ue_profiles.yaml'
)

_RELEASE_CONFIRM_TIMEOUT_SEC = 15
_RELEASE_POLL_INTERVAL_SEC = 1

_FAILURE_THRESHOLD = 3
_RECOVERY_SETTLE_SEC = 2
_RECOVERY_TIMEOUT_SEC = 30
_MAX_RECOVERY_ATTEMPTS = 3

_TRAFFIC_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'traffic.yaml'
_TOPOLOGY_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'topology.yaml'
_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'
_SLICE_PIDS_PATH = Path(__file__).resolve().parents[2] / 'config' / 'slice_pids.json'


_PING_COUNT = 4
_PING_INTERVAL = 0.2
_PING_TIMEOUT = 1

_ICMP_LINE_RE = re.compile(r'icmp_seq=(\d+).*?time=([\d.]+)\s*ms')

_EXPECTED_REPLIES = 2
_OFP_REPLY_WAIT_SEC = 1.0

_GIVING_UP_CLEAR_STREAK = 3


class StatsCollector:
	def __init__(
		self,
		topology_config: Path = _TOPOLOGY_CONFIG,
		slices_config: Path = _SLICES_CONFIG,
		interval_sec: int = 5,
	) -> None:
		self._topology_config = topology_config
		self._slices_config = slices_config
		self._interval_sec = interval_sec
		self._datapaths: dict[str, object] = {}
		self._stats_cache: dict[str, dict] = {}
		self._prev_bytes: dict[str, int] = {}
		self._prev_time: dict[str, float] = {}
		self._running = False
		self._topology: dict | None = None
		self._slices: dict | None = None
		self._pending_throughput: dict[str, float] = {}
		self._reply_count: int = 0
		self._reply_event: threading.Event | None = None
		# HUB_TYPE=native: hub.spawn produces real OS threads, not eventlet
		# greenlets. All recovery/failure-tracking state must go through this lock.
		self._cache_lock = hub.BoundedSemaphore(1)
		self._ue_identity: dict | None = None
		self._consecutive_failures: dict[str, int] = {}
		self._recovery_in_progress: set[str] = set()
		self._recovery_outcomes: dict[str, str] = {}
		self._recovery_attempts: dict[str, int] = {}
		self._recovery_events: list[dict] = []
		self._giving_up: set[str] = set()
		self._healthy_streak: dict[str, int] = {}
		self._traffic: dict | None = None

	def _get_topology(self) -> dict:
		if self._topology is None:
			with open(self._topology_config) as f:
				self._topology = yaml.safe_load(f)
		return self._topology

	def _get_slices(self) -> dict:
		if self._slices is None:
			with open(self._slices_config) as f:
				self._slices = yaml.safe_load(f)
		return self._slices

	def _get_traffic(self) -> dict:
		if self._traffic is None:
			with open(_TRAFFIC_CONFIG) as f:
				self._traffic = yaml.safe_load(f)
		return self._traffic

	def _load_slice_pids(self) -> dict[str, int]:
		with open(_SLICE_PIDS_PATH) as f:
			return json.load(f)

	def _get_ue_identity(self) -> dict[str, dict]:
		if self._ue_identity is None:
			with open(_UE_PROFILES_CONFIG) as f:
				config = yaml.safe_load(f)
			self._ue_identity = {
				ue['slice']: {'imsi': ue['imsi'], 'config_file': ue['config_file']}
				for ue in config['ue_profiles'].values()
			}
		return self._ue_identity

	def _read_iperf3_logfile(
		self,
		results: dict,
		key: str,
		logfile: str,
		use_nsenter: bool,
		sta_pid: int | None,
		protocol: str,
	) -> None:
		try:
			if use_nsenter:
				cmd = ['nsenter', '-t', str(sta_pid), '-n', 'tail', '-n', '100', logfile]
			else:
				cmd = ['docker', 'exec', 'ueransim', 'tail', '-n', '100', logfile]

			result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

			if result.returncode != 0 or not result.stdout.strip():
				results[key] = {'loss_pct': None, 'error': f'logfile unreadable: {logfile}'}
				return

			last_interval = None
			for line in result.stdout.splitlines():
				line = line.strip()
				if not line:
					continue
				try:
					obj = json.loads(line)
					if obj.get('event') == 'interval':
						last_interval = obj['data']['sum']
				except (json.JSONDecodeError, KeyError):
					continue

			if last_interval is None:
				results[key] = {'loss_pct': None, 'error': 'no interval data in logfile'}
				return

			if protocol == 'udp':
				loss_pct = float(last_interval.get('lost_percent', 0.0))
			else:
				packets = last_interval.get('bytes', 0) / 1400
				retransmits = last_interval.get('retransmits', 0)
				loss_pct = min(100.0 * retransmits / packets, 100.0) if packets > 0 else 0.0

			results[key] = {'loss_pct': loss_pct, 'error': None}

		except Exception as exc:
			results[key] = {'loss_pct': None, 'error': str(exc)}

	def _check_data_pending(self, imsi: str) -> str:
		try:
			result = subprocess.run(
				[
					'docker',
					'exec',
					'ueransim',
					'/ueransim/nr-cli',
					f'imsi-{imsi}',
					'--exec',
					'ps-list',
				],
				capture_output=True,
				text=True,
				timeout=5,
			)
			if result.returncode != 0:
				return 'check_failed'
			return 'stuck' if 'data-pending: true' in result.stdout else 'healthy'
		except Exception:
			return 'check_failed'

	def _wait_for_smf_release(self, imsi: str, wait_start_ts: float) -> bool:
		deadline = time.time() + _RELEASE_CONFIRM_TIMEOUT_SEC
		since_arg = str(int(wait_start_ts))
		while time.time() < deadline:
			try:
				result = subprocess.run(
					['docker', 'logs', '--since', since_arg, 'smf'],
					capture_output=True,
					text=True,
					timeout=5,
				)
			except Exception:
				hub.sleep(_RELEASE_POLL_INTERVAL_SEC)
				continue
			for line in result.stdout.splitlines():
				if f'imsi-{imsi}' in line and 'Release IP' in line:
					return True
			hub.sleep(_RELEASE_POLL_INTERVAL_SEC)
		return False

	def _recover_slice(
		self, slice_name: str, imsi: str, config_file: str, probe_interface: str
	) -> None:
		try:
			wait_start_ts = time.time()
			subprocess.run(
				[
					'docker',
					'exec',
					'ueransim',
					'/ueransim/nr-cli',
					f'imsi-{imsi}',
					'--exec',
					'deregister switch-off',
				],
				capture_output=True,
				timeout=10,
			)

			released = self._wait_for_smf_release(imsi, wait_start_ts)
			if not released:
				with self._cache_lock:
					self._recovery_outcomes[slice_name] = (
						'release not confirmed by SMF within '
						f'{_RELEASE_CONFIRM_TIMEOUT_SEC}s -- aborting recovery attempt '
						'without killing UE process, to avoid orphaning the IP pool slot'
					)
				return

			subprocess.run(
				['docker', 'exec', 'ueransim', 'pkill', '-f', config_file],
				capture_output=True,
			)
			hub.sleep(_RECOVERY_SETTLE_SEC)
			subprocess.run(
				[
					'docker',
					'exec',
					'-d',
					'ueransim',
					'/ueransim/nr-ue',
					'-c',
					f'/ueransim/config/{config_file}',
				],
				capture_output=True,
				timeout=10,
			)
			recovered = False
			for _ in range(_RECOVERY_TIMEOUT_SEC):
				check = subprocess.run(
					['docker', 'exec', 'ueransim', 'ip', 'link', 'show', probe_interface],
					capture_output=True,
					timeout=5,
				)
				if check.returncode == 0:
					recovered = True
					break
				hub.sleep(1)

			if recovered:
				with self._cache_lock:
					self._recovery_outcomes[slice_name] = 'recovered'
					self._consecutive_failures[slice_name] = 0
					self._recovery_attempts[slice_name] = 0
			else:
				with self._cache_lock:
					attempts_so_far = self._recovery_attempts.get(slice_name, 0)
					self._recovery_outcomes[slice_name] = (
						f'timed out (attempt {attempts_so_far}/{_MAX_RECOVERY_ATTEMPTS})'
					)
				# not resetting consecutive_failures on failure; prevents
				# a non-transient fault from producing infinite retries
		except Exception as exc:
			with self._cache_lock:
				self._recovery_outcomes[slice_name] = f'error: {exc}'
		finally:
			with self._cache_lock:
				self._recovery_in_progress.discard(slice_name)
				outcome = self._recovery_outcomes.get(slice_name, 'unknown')
			self._recovery_events.append(
				{
					'slice': slice_name,
					'timestamp': time.time(),
					'outcome': outcome,
				}
			)

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
			try:
				cycle_start = time.time()
				with self._cache_lock:
					self._pending_throughput.clear()
				self._reply_count = 0
				self._reply_event = threading.Event()

				self._request_stats()

				fired = self._reply_event.wait(
					timeout=min(_OFP_REPLY_WAIT_SEC, self._interval_sec * 0.2)
				)
				if not fired:
					with self._cache_lock:
						reply_count = self._reply_count
					logger.warning(
						'Stats collector: only %d/%d OFP replies received',
						reply_count,
						_EXPECTED_REPLIES,
					)

				self._run_probe_cycle()

				elapsed = time.time() - cycle_start
				remaining = self._interval_sec - elapsed
				if remaining > 0:
					hub.sleep(remaining)

			except Exception:
				logger.exception('Stats collector: unhandled exception in collection loop')
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
					'Stats collector: port counter reset: switch=%s port=%d -- skipping interval',
					switch_name,
					stat.port_no,
				)
				continue

			self._prev_bytes[tx_key] = stat.tx_bytes
			self._prev_bytes[rx_key] = stat.rx_bytes
			self._prev_time[tx_key] = now

			elapsed = now - prev_time
			port_tx_bps = ((stat.tx_bytes - prev_tx) * 8) / elapsed if elapsed > 0 else 0.0

			with self._cache_lock:
				self._pending_throughput[slice_name] = self._pending_throughput.get(
					slice_name, 0.0
				) + max(0.0, port_tx_bps)

		with self._cache_lock:
			self._reply_count += 1
			reply_count = self._reply_count
		if reply_count >= _EXPECTED_REPLIES:
			logger.debug('Stats collector: all OFP replies received')
			if self._reply_event is not None:
				self._reply_event.set()

	def _probe_slice(
		self,
		results: dict,
		slice_name: str,
		sink_ip: str,
		probe_interface: str,
		max_latency_ms: float,
	) -> None:
		# No logging inside this method to avoid lock contention on logging's
		# internal lock across many concurrent probes.
		try:
			result = subprocess.run(
				[
					'docker',
					'exec',
					'ueransim',
					'ping',
					'-I',
					probe_interface,
					'-c',
					str(_PING_COUNT),
					'-i',
					str(_PING_INTERVAL),
					'-W',
					str(_PING_TIMEOUT),
					sink_ip,
				],
				capture_output=True,
				text=True,
				timeout=10,
			)
			output = result.stdout

			seen_seqs: dict[int, float] = {
				int(seq): float(rtt) for seq, rtt in _ICMP_LINE_RE.findall(output)
			}

			rtts_ms: list[float] = []
			for seq in range(1, _PING_COUNT + 1):
				if seq in seen_seqs:
					rtts_ms.append(seen_seqs[seq])
				else:
					rtts_ms.append(max_latency_ms * 2.0)

			latency_ms = sum(rtts_ms) / len(rtts_ms) / 2.0
			results[slice_name] = {'latency_ms': latency_ms, 'error': None}

		except Exception as exc:
			results[slice_name] = {'latency_ms': None, 'error': str(exc)}

	def _run_probe_cycle(self) -> None:
		slices_cfg = self._get_slices()['slices']
		traffic_profiles = self._get_traffic()['traffic_profiles']
		probe_results: dict[str, dict] = {}
		loss_results: dict[str, dict] = {}

		logger.debug(
			'Stats collector: starting probe cycle for slices=%s', list(slices_cfg.keys())
		)

		try:
			slice_pids = self._load_slice_pids()
		except Exception as exc:
			logger.warning('Stats collector: could not load slice PIDs: %s', exc)
			slice_pids = {}

		latency_greenlets = []
		for slice_name, cfg in slices_cfg.items():
			sink_ip = cfg.get('sink_ip')
			probe_interface = cfg.get('probe_interface')
			max_latency_ms = cfg.get('max_latency_ms')
			if not sink_ip or not probe_interface or max_latency_ms is None:
				logger.warning(
					'Stats collector: probe config missing for slice %s -- skipping',
					slice_name,
				)
				continue
			gt = hub.spawn(
				self._probe_slice,
				probe_results,
				slice_name,
				sink_ip,
				probe_interface,
				max_latency_ms,
			)
			latency_greenlets.append(gt)

		loss_greenlets = []
		for slice_name, cfg in slices_cfg.items():
			sta = cfg.get('sta')
			probe_interface = cfg.get('probe_interface')
			protocol = traffic_profiles.get(slice_name, {}).get('protocol', 'udp')
			sta_pid = slice_pids.get(slice_name)

			if not sta or not probe_interface:
				continue

			ul_logfile = f'/tmp/iperf3-{sta}-5201.log'
			dl_logfile = f'/tmp/iperf3-{probe_interface}-dl.log'

			gt_ul = hub.spawn(
				self._read_iperf3_logfile,
				loss_results,
				f'{slice_name}_ul',
				ul_logfile,
				True,
				sta_pid,
				protocol,
			)
			loss_greenlets.append(gt_ul)

			gt_dl = hub.spawn(
				self._read_iperf3_logfile,
				loss_results,
				f'{slice_name}_dl',
				dl_logfile,
				False,
				None,
				protocol,
			)
			loss_greenlets.append(gt_dl)

		for gt in latency_greenlets:
			gt.wait()
		for gt in loss_greenlets:
			gt.wait()

		merged: dict[str, dict] = {}
		for slice_name, cfg in slices_cfg.items():
			latency = probe_results.get(slice_name, {})
			dl = loss_results.get(f'{slice_name}_dl', {})
			ul = loss_results.get(f'{slice_name}_ul', {})

			latency_ms = latency.get('latency_ms')
			max_latency_ms = cfg.get('max_latency_ms', 100.0)
			if latency_ms is None:
				latency_ms = max_latency_ms

			dl_loss = dl.get('loss_pct')
			ul_loss = ul.get('loss_pct')

			if dl_loss is not None and ul_loss is not None:
				loss_pct = max(dl_loss, ul_loss)
			elif dl_loss is not None:
				loss_pct = dl_loss
			elif ul_loss is not None:
				loss_pct = ul_loss
			else:
				loss_pct = 0.0

			error = latency.get('error') or dl.get('error') or ul.get('error')

			merged[slice_name] = {
				'latency_ms': latency_ms,
				'loss_pct': loss_pct,
				'error': error,
			}

			logger.info(
				'Stats collector: probe result: slice=%s latency_ms=%s loss_pct=%s error=%s',
				slice_name,
				latency_ms,
				loss_pct,
				error,
			)

		with self._cache_lock:
			outcomes_to_log = list(self._recovery_outcomes.items())
			for slice_name, _ in outcomes_to_log:
				del self._recovery_outcomes[slice_name]
		for slice_name, outcome in outcomes_to_log:
			logger.warning('Stats collector: recovery for slice %s: %s', slice_name, outcome)

		ue_identity = self._get_ue_identity()
		for slice_name, probe in merged.items():
			is_failure = probe['loss_pct'] == 100.0 or probe['error'] is not None

			with self._cache_lock:
				already_given_up = slice_name in self._giving_up

			if already_given_up:
				identity = ue_identity.get(slice_name)
				ping_ok = probe['loss_pct'] != 100.0
				data_status = (
					self._check_data_pending(identity['imsi']) if (ping_ok and identity) else None
				)
				fully_healthy = ping_ok and data_status == 'healthy'

				with self._cache_lock:
					if fully_healthy:
						self._healthy_streak[slice_name] = (
							self._healthy_streak.get(slice_name, 0) + 1
						)
						streak = self._healthy_streak[slice_name]
						if streak >= _GIVING_UP_CLEAR_STREAK:
							self._giving_up.discard(slice_name)
							self._healthy_streak[slice_name] = 0
							self._consecutive_failures[slice_name] = 0
							self._recovery_attempts[slice_name] = 0
							logger.warning(
								'Stats collector: slice %s cleared giving_up after '
								'%d consecutive healthy polls',
								slice_name,
								streak,
							)
					else:
						self._healthy_streak[slice_name] = 0
					streak_snapshot = self._healthy_streak.get(slice_name, 0)

				logger.debug(
					'Stats collector: slice %s still in giving_up (healthy_streak=%d/%d)',
					slice_name,
					streak_snapshot,
					_GIVING_UP_CLEAR_STREAK,
				)
				continue

			with self._cache_lock:
				self._consecutive_failures[slice_name] = (
					self._consecutive_failures.get(slice_name, 0) + 1 if is_failure else 0
				)
				failures = self._consecutive_failures[slice_name]
				in_progress = slice_name in self._recovery_in_progress
				attempts = self._recovery_attempts.get(slice_name, 0)

			if failures < _FAILURE_THRESHOLD or in_progress:
				continue

			if attempts >= _MAX_RECOVERY_ATTEMPTS:
				logger.error(
					'Stats collector: slice %s exceeded %d recovery attempts -- giving up, manual intervention required',
					slice_name,
					_MAX_RECOVERY_ATTEMPTS,
				)
				with self._cache_lock:
					self._giving_up.add(slice_name)
				continue

			identity = ue_identity.get(slice_name)
			if identity is None:
				continue

			status = self._check_data_pending(identity['imsi'])
			if status == 'check_failed':
				with self._cache_lock:
					self._recovery_attempts[slice_name] = attempts + 1
					escalated = self._recovery_attempts[slice_name] >= _MAX_RECOVERY_ATTEMPTS
					if escalated:
						self._giving_up.add(slice_name)
				if escalated:
					logger.error(
						'Stats collector: slice %s exceeded %d check-failed retries -- '
						'giving up, manual intervention required',
						slice_name,
						_MAX_RECOVERY_ATTEMPTS,
					)
				else:
					logger.warning(
						'Stats collector: health check failed for slice %s -- will retry next cycle',
						slice_name,
					)
				continue
			if status == 'healthy':
				continue

			with self._cache_lock:
				if slice_name in self._recovery_in_progress:
					continue
				self._recovery_in_progress.add(slice_name)
				attempts = self._recovery_attempts.get(slice_name, 0)
				self._recovery_attempts[slice_name] = attempts + 1

			logger.warning(
				'Stats collector: slice %s stuck (data-pending) after %d consecutive failures, attempt %d/%d',
				slice_name,
				failures,
				attempts + 1,
				_MAX_RECOVERY_ATTEMPTS,
			)
			probe_interface = slices_cfg[slice_name]['probe_interface']
			hub.spawn(
				self._recover_slice,
				slice_name,
				identity['imsi'],
				identity['config_file'],
				probe_interface,
			)

		with self._cache_lock:
			for slice_name, probe in merged.items():
				self._stats_cache[slice_name] = {
					'tx_throughput_bps': self._pending_throughput.get(slice_name, 0.0),
					'latency_ms': probe['latency_ms'],
					'loss_pct': probe['loss_pct'],
					'recovering': slice_name in self._recovery_in_progress,
					'giving_up': slice_name in self._giving_up,
				}
			snapshot = {
				slice_name: dict(metrics) for slice_name, metrics in self._stats_cache.items()
			}

		logger.info('Stats collector: cache updated for slices=%s', list(merged.keys()))

		loop = rest_api.registry.loop
		if loop is None:
			logger.debug('Stats collector: rest_api loop not yet ready -- skipping broadcast')
		else:
			asyncio.run_coroutine_threadsafe(rest_api.broadcast_metrics(snapshot), loop)
