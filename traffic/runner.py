# traffic/runner.py
# Shared traffic-generation core for scripts/traffic_generator.py (CLI)
# and infrastructure/controller/traffic_manager.py (background thread).
# No signal.signal() here -- only the main-thread CLI adapter may register
# OS signal handlers. stop() is cooperative graceful-drain: checked between
# loops only, does not interrupt an in-flight iperf3 subprocess call.

import fcntl
import json
import logging
import os
import random
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONTROLLER_HEALTH_URL = 'http://localhost:8080/health'
TRAFFIC_CONFIG_PATH = Path('config/traffic.yaml')
SLICES_CONFIG_PATH = Path('config/slices.yaml')
SLICE_PIDS_PATH = Path('config/slice_pids.json')
UE_PROFILES_PATH = Path('config/ue_profiles.yaml')

TRAFFIC_LOCK_PATH = Path('/tmp/sdn-traffic-generator.lock')

logger = logging.getLogger('traffic_runner')


def load_traffic_config(path: Path) -> tuple[dict, dict, dict]:
	with open(path) as f:
		config = yaml.safe_load(f)
	return (
		config['traffic_profiles'],
		config.get('defaults', {}),
		config.get('scenarios', {}),
	)


def load_slice_network(path: Path) -> dict:
	with open(path) as f:
		config = yaml.safe_load(f)
	network = {}
	for name, s in config['slices'].items():
		ue_ip = s['ue_subnet'].replace('.0/24', '.1')
		network[name] = {
			'tunnel': s['probe_interface'],
			'bind_ip': ue_ip,
			'server_ip': s['sink_ip'],
			'ue_ip': ue_ip,
			'dl_port': s['dl_port'],
			'sta': s['sta'],
		}
	return network


def load_slice_pids(path: Path) -> dict[str, int]:
	if not path.exists():
		raise RuntimeError(
			f'Slice PID map not found at {path}. '
			'Ensure campus_topology.py has started and written this file.'
		)
	with open(path) as f:
		return json.load(f)


def load_ue_identity(path: Path) -> tuple[dict[str, str], dict[str, str]]:
	with open(path) as f:
		config = yaml.safe_load(f)
	slice_to_imsi = {}
	slice_to_config_file = {}
	for ue in config['ue_profiles'].values():
		slice_to_imsi[ue['slice']] = ue['imsi']
		slice_to_config_file[ue['slice']] = ue['config_file']
	return slice_to_imsi, slice_to_config_file


def _check_data_pending(imsi: str) -> bool:
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
	return 'data-pending: true' in result.stdout


def _controller_owns_recovery() -> bool:
	try:
		with urllib.request.urlopen(CONTROLLER_HEALTH_URL, timeout=2) as resp:
			return bool(json.loads(resp.read()).get('registry_frozen'))
	except Exception:
		return False


def _wait_for_slice_recovery(
	net: dict, timeout_sec: int = 60, poll_sec: int = 2
) -> bool:
	deadline = time.monotonic() + timeout_sec
	while time.monotonic() < deadline:
		result = subprocess.run(
			[
				'docker',
				'exec',
				'ueransim',
				'ping',
				'-I',
				net['tunnel'],
				'-c',
				'1',
				'-W',
				'2',
				net['server_ip'],
			],
			capture_output=True,
		)
		if result.returncode == 0:
			return True
		time.sleep(poll_sec)
	return False


def _recover_ue(imsi: str, config_file: str, iface: str, timeout_sec: int = 30) -> None:
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
	time.sleep(2)
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
	for _ in range(timeout_sec):
		check = subprocess.run(
			['docker', 'exec', 'ueransim', 'ip', 'link', 'show', iface],
			capture_output=True,
			timeout=5,
		)
		if check.returncode == 0:
			return
		time.sleep(1)
	raise RuntimeError(f'{iface} did not reappear after recovering imsi-{imsi}')


def sample_scenario(
	scenario_name: str, scenario_cfg: dict, profiles: dict, rng: random.Random
) -> dict:
	effective = {}
	for slice_name, profile in profiles.items():
		factors = scenario_cfg.get(slice_name, {})
		ul_lo, ul_hi = factors.get('ul_factor_range', [1.0, 1.0])
		dl_lo, dl_hi = factors.get('dl_factor_range', [1.0, 1.0])
		ul_factor = rng.uniform(ul_lo, ul_hi)
		dl_factor = rng.uniform(dl_lo, dl_hi)

		p = dict(profile)
		if p.get('pattern') == 'mixed':
			p['continuous_bps'] = int(profile['continuous_bps'] * ul_factor)
			p['on_off_bps'] = int(profile['on_off_bps'] * ul_factor)
			p['downlink_bps'] = int(profile['downlink_bps'] * dl_factor)
			if 'downlink_on_off_bps' in profile:
				p['downlink_on_off_bps'] = int(profile['downlink_on_off_bps'] * dl_factor)
		else:
			p['target_bps'] = int(profile['target_bps'] * ul_factor)
			p['downlink_bps'] = int(
				profile.get('downlink_bps', profile['target_bps']) * dl_factor
			)

		effective[slice_name] = p
	return effective


def verify_tunnels(
	slice_network: dict,
	slice_to_imsi: dict[str, str],
	slice_to_config_file: dict[str, str],
) -> None:
	controller_owns_recovery = _controller_owns_recovery()
	if controller_owns_recovery:
		logger.info('Controller detected -- deferring tunnel recovery to stats_collector')

	for slice_name, net in slice_network.items():
		result = subprocess.run(
			['docker', 'exec', 'ueransim', 'ip', 'link', 'show', net['tunnel']],
			capture_output=True,
			text=True,
		)
		if result.returncode != 0:
			if controller_owns_recovery:
				if not _wait_for_slice_recovery(net):
					raise RuntimeError(
						f'Tunnel {net["tunnel"]} for slice {slice_name} does not exist '
						'and controller recovery did not restore it in time.'
					)
				logger.info('Slice %s tunnel recovered by controller.', slice_name)
				continue
			raise RuntimeError(
				f'Tunnel {net["tunnel"]} for slice {slice_name} does not exist. '
				'Ensure UE sessions are attached before starting traffic.'
			)

		ping_result = subprocess.run(
			[
				'docker',
				'exec',
				'ueransim',
				'ping',
				'-I',
				net['tunnel'],
				'-c',
				'1',
				'-W',
				'2',
				net['server_ip'],
			],
			capture_output=True,
			text=True,
		)

		if ping_result.returncode != 0:
			if controller_owns_recovery:
				if not _wait_for_slice_recovery(net):
					raise RuntimeError(
						f'Slice {slice_name}: {net["server_ip"]} unreachable via '
						f'{net["tunnel"]} and controller recovery did not clear it in time.'
					)
				logger.info('Slice %s recovered by controller.', slice_name)
				continue

			imsi = slice_to_imsi.get(slice_name)
			config_file = slice_to_config_file.get(slice_name)
			if imsi is None or config_file is None:
				raise RuntimeError(
					f'Slice {slice_name}: {net["server_ip"]} unreachable via '
					f'{net["tunnel"]}, and no IMSI/config mapping available to attempt recovery.'
				)

			stuck = _check_data_pending(imsi)
			logger.warning(
				'Slice %s: %s unreachable via %s (data-pending=%s) -- attempting recovery',
				slice_name,
				net['server_ip'],
				net['tunnel'],
				stuck,
			)
			_recover_ue(imsi, config_file, net['tunnel'])

			retry = subprocess.run(
				[
					'docker',
					'exec',
					'ueransim',
					'ping',
					'-I',
					net['tunnel'],
					'-c',
					'1',
					'-W',
					'2',
					net['server_ip'],
				],
				capture_output=True,
				text=True,
			)
			if retry.returncode != 0:
				raise RuntimeError(
					f'Slice {slice_name}: {net["server_ip"]} still unreachable via '
					f'{net["tunnel"]} after recovery attempt.'
				)
			logger.info('Slice %s recovered successfully.', slice_name)

	logger.info('All tunnels verified reachable.')


def start_downlink_servers(slice_network: dict) -> None:
	subprocess.run(
		['docker', 'exec', 'ueransim', 'pkill', '-f', 'iperf3 -s'], capture_output=True
	)
	time.sleep(1)

	for slice_name, net in slice_network.items():
		loop_cmd = (
			f'while true; do timeout 300s iperf3 -s -1 -B {net["ue_ip"]} -p {net["dl_port"]} '
			f'-i 1 --json-stream --forceflush --idle-timeout 30; '
			f'done > /tmp/iperf3-{net["tunnel"]}-dl.log 2>&1'
		)
		cmd = ['docker', 'exec', '-d', 'ueransim', 'bash', '-c', loop_cmd]
		result = subprocess.run(cmd, capture_output=True, text=True)
		if result.returncode != 0:
			raise RuntimeError(
				f'Failed to start downlink server for {slice_name}: {result.stderr.strip()}'
			)

	_wait_for_downlink_servers(slice_network)


def _wait_for_downlink_servers(slice_network: dict, timeout_sec: int = 15) -> None:
	deadline = time.monotonic() + timeout_sec
	pending = {net['ue_ip']: net['dl_port'] for net in slice_network.values()}
	while pending and time.monotonic() < deadline:
		result = subprocess.run(
			['docker', 'exec', 'ueransim', 'ss', '-lntp'], capture_output=True, text=True
		)
		listening = result.stdout
		pending = {
			ip: port for ip, port in pending.items() if f'{ip}:{port}' not in listening
		}
		if pending:
			time.sleep(0.5)
	if pending:
		raise RuntimeError(
			f'Downlink servers did not come up within {timeout_sec}s for: {list(pending.keys())}'
		)
	logger.info('All downlink servers listening.')


def _run_iperf3(
	bind_ip, server_ip, port, duration, protocol, target_bps, packet_size=None
):
	start = datetime.now(timezone.utc).isoformat()
	cmd = [
		'docker',
		'exec',
		'ueransim',
		'timeout',
		str(duration + 15),
		'iperf3',
		'-c',
		server_ip,
		'-B',
		bind_ip,
		'-p',
		str(port),
		'-t',
		str(duration),
		'-J',
	]
	if protocol == 'udp':
		cmd += ['-u', '-b', str(target_bps), '-l', str(packet_size or 1400)]
	else:
		cmd += ['-b', str(target_bps)]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 15)
	if result.returncode != 0:
		raise RuntimeError(
			f'exit={result.returncode} stderr={result.stderr.strip()!r} stdout={result.stdout.strip()[:500]!r}'
		)
	end = datetime.now(timezone.utc).isoformat()
	return json.loads(result.stdout), start, end


def _run_iperf3_downlink(
	sta_pid, ue_ip, port, duration, protocol, target_bps, packet_size=None
):
	start = datetime.now(timezone.utc).isoformat()
	cmd = [
		'nice',
		'-n',
		'10',
		'nsenter',
		'-t',
		str(sta_pid),
		'-n',
		'timeout',
		str(duration + 15),
		'iperf3',
		'-c',
		ue_ip,
		'-p',
		str(port),
		'-t',
		str(duration),
		'-J',
	]
	if protocol == 'udp':
		cmd += ['-u', '-b', str(target_bps), '-l', str(packet_size or 1400)]
	else:
		cmd += ['-b', str(target_bps)]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 15)
	if result.returncode != 0:
		raise RuntimeError(
			f'exit={result.returncode} stderr={result.stderr.strip()!r} stdout={result.stdout.strip()[:500]!r}'
		)
	end = datetime.now(timezone.utc).isoformat()
	return json.loads(result.stdout), start, end


def _extract_summary(
	slice_name, protocol, data, start_timestamp, end_timestamp, scenario, label=''
):
	end = data.get('end', {})
	summary = {
		'slice': slice_name,
		'component': label or 'continuous',
		'scenario': scenario,
		'start_timestamp': start_timestamp,
		'end_timestamp': end_timestamp,
		'protocol': protocol,
	}
	if protocol == 'udp':
		sent = end.get('sum_sent', {})
		received = end.get('sum_received', {})
		summary['sender_mbps'] = sent.get('bits_per_second', 0) / 1e6
		summary['receiver_mbps'] = received.get('bits_per_second', 0) / 1e6
		summary['loss_pct'] = received.get('lost_percent', 0)
		summary['jitter_ms'] = received.get('jitter_ms', 0)
		summary['packets_sent'] = sent.get('packets', 0)
		summary['packets_lost'] = received.get('lost_packets', 0)
	else:
		summary['sender_mbps'] = end.get('sum_sent', {}).get('bits_per_second', 0) / 1e6
		summary['receiver_mbps'] = (
			end.get('sum_received', {}).get('bits_per_second', 0) / 1e6
		)
		summary['retransmits'] = end.get('sum_sent', {}).get('retransmits', 0)
		summary['loss_pct'] = 0.0
	return summary


def run_continuous_slice(slice_name, profile, network, duration, scenario):
	try:
		data, start, end = _run_iperf3(
			bind_ip=network['bind_ip'],
			server_ip=network['server_ip'],
			port=profile.get('port', 5201),
			duration=duration,
			protocol=profile['protocol'],
			target_bps=profile['target_bps'],
			packet_size=profile.get('packet_size'),
		)
		summary = _extract_summary(
			slice_name, profile['protocol'], data, start, end, scenario
		)
		logger.info(
			'%s uplink: rx=%.2f Mbps loss=%.1f%%',
			slice_name,
			summary.get('receiver_mbps', 0),
			summary.get('loss_pct', 0),
		)
		return [summary]
	except Exception as e:
		logger.error('%s uplink continuous failed: %s', slice_name, e)
		return [
			{
				'slice': slice_name,
				'component': 'continuous',
				'scenario': scenario,
				'error': str(e),
			}
		]


def run_downlink_slice(slice_name, profile, network, duration, sta_pid, scenario):
	target_bps = profile.get('downlink_bps', profile.get('target_bps'))
	try:
		data, start, end = _run_iperf3_downlink(
			sta_pid=sta_pid,
			ue_ip=network['ue_ip'],
			port=network['dl_port'],
			duration=duration,
			protocol=profile['protocol'],
			target_bps=target_bps,
			packet_size=profile.get('packet_size'),
		)
		summary = _extract_summary(
			slice_name, profile['protocol'], data, start, end, scenario, label='downlink'
		)
		logger.info(
			'%s downlink: rx=%.2f Mbps loss=%.1f%%',
			slice_name,
			summary.get('receiver_mbps', 0),
			summary.get('loss_pct', 0),
		)
		return [summary]
	except Exception as e:
		logger.error('%s downlink failed: %s', slice_name, e)
		return [
			{
				'slice': slice_name,
				'component': 'downlink',
				'scenario': scenario,
				'error': str(e),
			}
		]


def run_on_off_component(
	slice_name, profile, network, duration, stop_event, scenario, rng
):
	results = []
	elapsed = 0
	min_on = profile.get('min_on_sec', 2)
	min_off = profile.get('min_off_sec', 2)

	while elapsed < duration and not stop_event.is_set():
		on_sec = max(min_on, int(rng.expovariate(1.0 / profile['mean_on_sec'])))
		on_sec = min(on_sec, duration - elapsed)
		if on_sec <= 0:
			break
		try:
			data, start, end = _run_iperf3(
				bind_ip=network['bind_ip'],
				server_ip=network['server_ip'],
				port=profile.get('on_off_port', 5202),
				duration=on_sec,
				protocol=profile['protocol'],
				target_bps=profile['on_off_bps'],
			)
			summary = _extract_summary(
				slice_name, profile['protocol'], data, start, end, scenario, label='on_off'
			)
			logger.info(
				'%s on_off burst: rx=%.2f Mbps', slice_name, summary.get('receiver_mbps', 0)
			)
			results.append(summary)
		except Exception as e:
			logger.error('%s on_off burst failed: %s', slice_name, e)
			results.append(
				{
					'slice': slice_name,
					'component': 'on_off',
					'scenario': scenario,
					'error': str(e),
				}
			)

		elapsed += on_sec
		if elapsed >= duration or stop_event.is_set():
			break
		off_sec = max(min_off, int(rng.expovariate(1.0 / profile['mean_off_sec'])))
		off_sec = min(off_sec, duration - elapsed)
		stop_event.wait(timeout=off_sec)
		elapsed += off_sec

	return results


def run_mixed_slice(slice_name, profile, network, duration, scenario, rng):
	results = []
	stop_event = threading.Event()

	def continuous():
		try:
			data, start, end = _run_iperf3(
				bind_ip=network['bind_ip'],
				server_ip=network['server_ip'],
				port=profile.get('continuous_port', 5201),
				duration=duration,
				protocol=profile['protocol'],
				target_bps=profile['continuous_bps'],
			)
			summary = _extract_summary(
				slice_name, profile['protocol'], data, start, end, scenario, label='continuous'
			)
			logger.info(
				'%s continuous: rx=%.2f Mbps', slice_name, summary.get('receiver_mbps', 0)
			)
			results.append(summary)
		except Exception as e:
			logger.error('%s continuous failed: %s', slice_name, e)
			results.append(
				{
					'slice': slice_name,
					'component': 'continuous',
					'scenario': scenario,
					'error': str(e),
				}
			)
		finally:
			stop_event.set()

	t = threading.Thread(target=continuous, daemon=True)
	t.start()
	on_off_results = run_on_off_component(
		slice_name, profile, network, duration, stop_event, scenario, rng
	)
	results.extend(on_off_results)
	t.join()
	return results


def run_slice(slice_name, profile, network, duration, sta_pid, scenario, rng):
	pattern = profile.get('pattern', 'continuous')
	logger.info(
		'Starting %s (%s pattern, bidirectional, scenario=%s)',
		slice_name,
		pattern,
		scenario,
	)

	ul_results: list[dict] = []
	dl_results: list[dict] = []

	def run_ul():
		if pattern == 'mixed':
			ul_results.extend(
				run_mixed_slice(slice_name, profile, network, duration, scenario, rng)
			)
		else:
			ul_results.extend(
				run_continuous_slice(slice_name, profile, network, duration, scenario)
			)

	def run_dl():
		dl_results.extend(
			run_downlink_slice(slice_name, profile, network, duration, sta_pid, scenario)
		)

	ul_thread = threading.Thread(target=run_ul, daemon=True)
	dl_thread = threading.Thread(target=run_dl, daemon=True)
	ul_thread.start()
	dl_thread.start()
	ul_thread.join()
	dl_thread.join()

	return ul_results + dl_results


class TrafficRunner:
	def __init__(
		self,
		slices: list[str] | None = None,
		loops: int = 0,
		scenario: str | None = None,
		seed: int | None = None,
		traffic_config_path: Path = TRAFFIC_CONFIG_PATH,
		slices_config_path: Path = SLICES_CONFIG_PATH,
		slice_pids_path: Path = SLICE_PIDS_PATH,
		ue_profiles_path: Path = UE_PROFILES_PATH,
		lock_path: Path = TRAFFIC_LOCK_PATH,
	):
		self.profiles, self.defaults, self.scenarios = load_traffic_config(
			traffic_config_path
		)
		self.slice_network = load_slice_network(slices_config_path)
		self._slice_pids_path = slice_pids_path
		self._ue_profiles_path = ue_profiles_path
		self._lock_path = lock_path
		self._lock_fd = None

		requested = slices or list(self.slice_network.keys())
		self.active_slices = [
			s for s in requested if s in self.profiles and s in self.slice_network
		]
		if not self.active_slices:
			raise ValueError('No valid slices specified')
		if scenario is not None and scenario not in self.scenarios:
			raise ValueError(f'Unknown scenario: {scenario!r}')

		self._loops = loops
		self._fixed_scenario = scenario
		self._seed = seed
		self._master_rng = random.Random(seed)

		self._stop_event = threading.Event()
		self._scenario_lock = threading.Lock()
		self._scenario_override: str | None = None
		self._current_scenario: str | None = None

		self._slice_pids: dict[str, int] = {}
		self._slice_to_imsi: dict[str, str] = {}
		self._slice_to_config_file: dict[str, str] = {}

	def _acquire_lock(self) -> None:
		self._lock_path.parent.mkdir(parents=True, exist_ok=True)
		fd = open(self._lock_path, 'w')
		try:
			fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
		except BlockingIOError:
			fd.close()
			raise RuntimeError(
				'Another traffic generator instance (CLI or controller) is already '
				'running against this environment. Stop it before starting a new one.'
			) from None
		fd.write(str(os.getpid()))
		fd.flush()
		self._lock_fd = fd

	def _release_lock(self) -> None:
		if self._lock_fd is not None:
			fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
			self._lock_fd.close()
			self._lock_fd = None

	def set_scenario(self, scenario_name: str) -> None:
		if scenario_name not in self.scenarios:
			raise ValueError(f'Unknown scenario: {scenario_name!r}')
		with self._scenario_lock:
			self._scenario_override = scenario_name

	def get_current_scenario(self) -> str | None:
		with self._scenario_lock:
			return self._current_scenario

	def request_stop(self) -> None:
		self._stop_event.set()

	def setup(self) -> None:
		self._acquire_lock()
		try:
			self._slice_pids = load_slice_pids(self._slice_pids_path)
			self._slice_to_imsi, self._slice_to_config_file = load_ue_identity(
				self._ue_profiles_path
			)
			verify_tunnels(
				self.slice_network, self._slice_to_imsi, self._slice_to_config_file
			)
			start_downlink_servers(self.slice_network)
		except Exception:
			self._release_lock()
			raise

	def _current_scenario_name(self) -> str:
		with self._scenario_lock:
			if self._scenario_override is not None:
				return self._scenario_override
		if self._fixed_scenario is not None:
			return self._fixed_scenario
		return self._master_rng.choice(list(self.scenarios.keys()))

	def run(self, on_loop_complete, on_loop_start=None) -> None:
		"""Blocking. Exits on stop() (checked between loops only -- an
		in-flight iperf3 call is not interrupted) or when loops is reached."""
		try:
			loop = 0
			while not self._stop_event.is_set():
				loop += 1
				if self._loops > 0 and loop > self._loops:
					break

				scenario_name = self._current_scenario_name()

				with self._scenario_lock:
					self._current_scenario = scenario_name

				if on_loop_start is not None:
					on_loop_start(loop, scenario_name)

				effective_profiles = sample_scenario(
					scenario_name, self.scenarios[scenario_name], self.profiles, self._master_rng
				)

				slice_results: dict[str, list] = {}
				failed_slices: list[str] = []

				def run_and_collect(name, prof, net, dur, pid, scen, rng):
					result = run_slice(name, prof, net, dur, pid, scen, rng)
					if all('error' in r for r in result):
						failed_slices.append(name)
					slice_results[name] = result

				threads = []
				for name in self.active_slices:
					if self._stop_event.is_set():
						break
					if name not in self._slice_pids:
						logger.error('No PID for slice %s -- skipping', name)
						failed_slices.append(name)
						continue

					dur = self.profiles[name].get(
						'duration_sec', self.defaults.get('duration_sec', 60)
					)
					slice_rng = (
						random.Random(f'{self._seed}:{loop}:{name}')
						if self._seed is not None
						else random.Random()
					)
					t = threading.Thread(
						target=run_and_collect,
						args=(
							name,
							effective_profiles[name],
							self.slice_network[name],
							dur,
							self._slice_pids[name],
							scenario_name,
							slice_rng,
						),
						daemon=True,
					)
					threads.append(t)
					t.start()

				for t in threads:
					t.join()

				results = []
				for name in self.active_slices:
					results.extend(slice_results.get(name, []))

				if failed_slices:
					logger.warning('Slices with complete failure: %s', failed_slices)

				on_loop_complete(loop, scenario_name, results, failed_slices)

				if self._stop_event.is_set():
					break

				gap = self.defaults.get('inter_loop_gap_sec', 5)
				if (self._loops == 0 or loop < self._loops) and gap > 0:
					self._stop_event.wait(timeout=gap)

			logger.info('TrafficRunner stopped.')
		finally:
			self._release_lock()
