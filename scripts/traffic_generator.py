#!/usr/bin/env python3
# scripts/traffic_generator.py
# Runs continuous per-slice iperf3 traffic through the 5G GTP tunnels.
# Supports continuous and mixed (continuous + ON/OFF burst) traffic patterns.
# All slices run concurrently. Reads config/traffic.yaml.
# Outputs JSON results per loop to logs/traffic/.

import argparse
import json
import logging
import random
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

LOG_DIR = Path('logs/traffic')
TRAFFIC_CONFIG_PATH = Path('config/traffic.yaml')
SLICES_CONFIG_PATH = Path('config/slices.yaml')
SLICE_PIDS_PATH = Path('config/slice_pids.json')

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('traffic_generator')


def load_traffic_config() -> tuple[dict, dict, dict]:
	with open(TRAFFIC_CONFIG_PATH) as f:
		config = yaml.safe_load(f)
	return (
		config['traffic_profiles'],
		config.get('defaults', {}),
		config.get('scenarios', {}),
	)


def load_slice_network() -> dict:
	with open(SLICES_CONFIG_PATH) as f:
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


def load_slice_pids() -> dict[str, int]:
	if not SLICE_PIDS_PATH.exists():
		raise RuntimeError(
			f'Slice PID map not found at {SLICE_PIDS_PATH}. '
			'Ensure campus_topology.py has started and written this file.'
		)
	with open(SLICE_PIDS_PATH) as f:
		return json.load(f)


def sample_scenario(
	scenario_name: str,
	scenario_cfg: dict,
	profiles: dict,
) -> dict:
	effective = {}
	for slice_name, profile in profiles.items():
		factors = scenario_cfg.get(slice_name, {})
		ul_lo, ul_hi = factors.get('ul_factor_range', [1.0, 1.0])
		dl_lo, dl_hi = factors.get('dl_factor_range', [1.0, 1.0])
		ul_factor = random.uniform(ul_lo, ul_hi)
		dl_factor = random.uniform(dl_lo, dl_hi)

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


def verify_tunnels(slice_network: dict) -> None:
	for slice_name, net in slice_network.items():
		result = subprocess.run(
			['docker', 'exec', 'ueransim', 'ip', 'link', 'show', net['tunnel']],
			capture_output=True,
			text=True,
		)
		if result.returncode != 0:
			raise RuntimeError(
				f'Tunnel {net["tunnel"]} for slice {slice_name} does not exist. '
				'Ensure UE sessions are attached before starting traffic.'
			)
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
			text=True,
		)
		if result.returncode != 0:
			raise RuntimeError(
				f'Slice {slice_name}: {net["server_ip"]} unreachable via '
				f'{net["tunnel"]}. Check UPF forwarding and OVS flow rules.'
			)
	logger.info('All tunnels verified reachable.')


def start_downlink_servers(slice_network: dict) -> None:
	subprocess.run(
		['docker', 'exec', 'ueransim', 'pkill', '-f', 'iperf3 -s'],
		capture_output=True,
	)
	time.sleep(1)

	for slice_name, net in slice_network.items():
		# -B is required: without it iperf3 replies via the container default
		# route instead of the GTP tunnel, breaking the downlink data path.
		loop_cmd = (
			f'while true; do timeout 90s iperf3 -s -1 -B {net["ue_ip"]} -p {net["dl_port"]} '
			f'--logfile /tmp/iperf3-{net["tunnel"]}-dl.log; done'
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
			['docker', 'exec', 'ueransim', 'ss', '-lntp'],
			capture_output=True,
			text=True,
		)
		listening = result.stdout
		pending = {
			ip: port for ip, port in pending.items() if f'{ip}:{port}' not in listening
		}
		if pending:
			time.sleep(0.5)

	if pending:
		raise RuntimeError(
			f'Downlink servers did not come up within {timeout_sec}s '
			f'for: {list(pending.keys())}'
		)
	logger.info('All downlink servers listening.')


def _run_iperf3(
	bind_ip: str,
	server_ip: str,
	port: int,
	duration: int,
	protocol: str,
	target_bps: int,
	packet_size: int | None = None,
) -> tuple[dict, str, str]:
	start = datetime.now(timezone.utc).isoformat()
	cmd = [
		'docker',
		'exec',
		'ueransim',
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
			f'exit={result.returncode} stderr={result.stderr.strip()!r} '
			f'stdout={result.stdout.strip()[:500]!r}'
		)
	end = datetime.now(timezone.utc).isoformat()
	return json.loads(result.stdout), start, end


def _run_iperf3_downlink(
	sta_pid: int,
	ue_ip: str,
	port: int,
	duration: int,
	protocol: str,
	target_bps: int,
	packet_size: int | None = None,
) -> tuple[dict, str, str]:
	start = datetime.now(timezone.utc).isoformat()
	# Mininet-WiFi stations don't have named namespaces in /var/run/netns/,
	# so nsenter by PID is the only way in.
	cmd = [
		'nsenter',
		'-t',
		str(sta_pid),
		'-n',
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
			f'exit={result.returncode} stderr={result.stderr.strip()!r} '
			f'stdout={result.stdout.strip()[:500]!r}'
		)
	end = datetime.now(timezone.utc).isoformat()
	return json.loads(result.stdout), start, end


def _extract_summary(
	slice_name: str,
	protocol: str,
	data: dict,
	start_timestamp: str,
	end_timestamp: str,
	scenario: str,
	label: str = '',
) -> dict:
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


def run_continuous_slice(
	slice_name: str, profile: dict, network: dict, duration: int, scenario: str
) -> list[dict]:
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


def run_downlink_slice(
	slice_name: str,
	profile: dict,
	network: dict,
	duration: int,
	sta_pid: int,
	scenario: str,
) -> list[dict]:
	# Downlink target rate: use explicit downlink_bps if configured,
	# otherwise match the uplink target. VLE and Student Portal are
	# downlink-dominant in reality so downlink_bps should be set higher.
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
	slice_name: str,
	profile: dict,
	network: dict,
	duration: int,
	stop_event: threading.Event,
	scenario: str,
) -> list[dict]:
	results = []
	elapsed = 0
	min_on = profile.get('min_on_sec', 2)
	min_off = profile.get('min_off_sec', 2)

	while elapsed < duration and not stop_event.is_set():
		on_sec = max(min_on, int(random.expovariate(1.0 / profile['mean_on_sec'])))
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

		off_sec = max(min_off, int(random.expovariate(1.0 / profile['mean_off_sec'])))
		off_sec = min(off_sec, duration - elapsed)
		stop_event.wait(timeout=off_sec)
		elapsed += off_sec

	return results


def run_mixed_slice(
	slice_name: str, profile: dict, network: dict, duration: int, scenario: str
) -> list[dict]:
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
		slice_name, profile, network, duration, stop_event, scenario
	)
	results.extend(on_off_results)
	t.join()
	return results


def run_slice(
	slice_name: str,
	profile: dict,
	network: dict,
	duration: int,
	sta_pid: int,
	scenario: str,
) -> list[dict]:
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
				run_mixed_slice(slice_name, profile, network, duration, scenario)
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


def save_results(results: list[dict], output_dir: Path) -> None:
	ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
	path = output_dir / f'results_{ts}.json'
	with open(path, 'w') as f:
		json.dump(results, f, indent=2)
	logger.info('Results saved to %s', path)


def main():
	parser = argparse.ArgumentParser(
		description='Per-slice bidirectional iperf3 traffic generator'
	)
	parser.add_argument('--slices', nargs='+', default=None)
	parser.add_argument('--loops', type=int, default=0)
	parser.add_argument(
		'--scenario',
		choices=['lecture', 'registration', 'off_peak'],
		default=None,
		help='Fix scenario for all loops. Omit to sample randomly each loop.',
	)
	args = parser.parse_args()

	profiles, defaults, scenarios = load_traffic_config()
	slice_network = load_slice_network()
	default_duration = defaults.get('duration_sec', 60)
	inter_loop_gap = defaults.get('inter_loop_gap_sec', 5)
	LOG_DIR.mkdir(parents=True, exist_ok=True)

	requested = args.slices or list(slice_network.keys())
	active_slices = [s for s in requested if s in profiles and s in slice_network]
	if not active_slices:
		logger.error('No valid slices specified')
		return

	slice_pids = load_slice_pids()
	verify_tunnels(slice_network)
	start_downlink_servers(slice_network)

	running = True

	def handle_signal(sig, frame):
		nonlocal running
		logger.info('Shutting down...')
		running = False

	signal.signal(signal.SIGINT, handle_signal)
	signal.signal(signal.SIGTERM, handle_signal)

	loop = 0
	while running:
		loop += 1
		if args.loops > 0 and loop > args.loops:
			break

		scenario_name = args.scenario or random.choice(list(scenarios.keys()))
		effective_profiles = sample_scenario(
			scenario_name, scenarios[scenario_name], profiles
		)
		logger.info('--- Loop %d | scenario=%s ---', loop, scenario_name)

		slice_results: dict[str, list] = {}
		failed_slices: list[str] = []

		def run_and_collect(name, prof, net, dur, pid, scen):
			result = run_slice(name, prof, net, dur, pid, scen)
			if all('error' in r for r in result):
				failed_slices.append(name)
			slice_results[name] = result

		threads = []
		for name in active_slices:
			if not running:
				break
			if name not in slice_pids:
				logger.error('No PID for slice %s — skipping', name)
				failed_slices.append(name)
				continue
			dur = profiles[name].get('duration_sec', default_duration)
			t = threading.Thread(
				target=run_and_collect,
				args=(
					name,
					effective_profiles[name],
					slice_network[name],
					dur,
					slice_pids[name],
					scenario_name,
				),
				daemon=True,
			)
			threads.append(t)
			t.start()

		for t in threads:
			t.join()

		results = []
		for name in active_slices:
			results.extend(slice_results.get(name, []))

		if failed_slices:
			logger.warning('Slices with complete failure: %s', failed_slices)

		if results:
			save_results(results, LOG_DIR)

		if running and (args.loops == 0 or loop < args.loops) and inter_loop_gap > 0:
			logger.info('Waiting %ds before next loop...', inter_loop_gap)
			time.sleep(inter_loop_gap)

	logger.info('Traffic generator stopped.')


if __name__ == '__main__':
	main()
