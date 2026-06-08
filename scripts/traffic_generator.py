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
CONFIG_PATH = Path('config/traffic.yaml')

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('traffic_generator')

SLICE_NETWORK = {
	'vle': {'tunnel': 'ue1tun0', 'bind_ip': '10.60.1.1', 'server_ip': '10.0.1.1'},
	'student_portal': {
		'tunnel': 'ue2tun0',
		'bind_ip': '10.60.2.1',
		'server_ip': '10.0.2.1',
	},
	'admin': {'tunnel': 'ue3tun0', 'bind_ip': '10.60.3.1', 'server_ip': '10.0.3.1'},
	'iot': {'tunnel': 'ue4tun0', 'bind_ip': '10.60.4.1', 'server_ip': '10.0.4.1'},
	'general': {'tunnel': 'ue5tun0', 'bind_ip': '10.60.5.1', 'server_ip': '10.0.5.1'},
}


def load_config() -> tuple[dict, dict]:
	with open(CONFIG_PATH) as f:
		config = yaml.safe_load(f)
	return config['traffic_profiles'], config.get('defaults', {})


def _run_iperf3(
	bind_ip: str,
	server_ip: str,
	port: int,
	duration: int,
	protocol: str,
	target_bps: int,
	packet_size: int | None = None,
) -> dict:
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
		raise RuntimeError(result.stderr.strip())
	return json.loads(result.stdout)


def _extract_summary(
	slice_name: str, protocol: str, data: dict, label: str = ''
) -> dict:
	ts = datetime.now(timezone.utc).isoformat()
	end = data.get('end', {})
	summary = {
		'slice': slice_name,
		'component': label or 'continuous',
		'timestamp': ts,
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
	slice_name: str, profile: dict, network: dict, duration: int
) -> list[dict]:
	try:
		data = _run_iperf3(
			bind_ip=network['bind_ip'],
			server_ip=network['server_ip'],
			port=profile.get('port', 5201),
			duration=duration,
			protocol=profile['protocol'],
			target_bps=profile['target_bps'],
			packet_size=profile.get('packet_size'),
		)
		summary = _extract_summary(slice_name, profile['protocol'], data)
		logger.info(
			'%s: rx=%.2f Mbps loss=%.1f%%',
			slice_name,
			summary.get('receiver_mbps', 0),
			summary.get('loss_pct', 0),
		)
		return [summary]
	except Exception as e:
		logger.error('%s continuous failed: %s', slice_name, e)
		return [{'slice': slice_name, 'component': 'continuous', 'error': str(e)}]


def run_on_off_component(
	slice_name: str,
	profile: dict,
	network: dict,
	duration: int,
	stop_event: threading.Event,
) -> list[dict]:
	results = []
	elapsed = 0
	while elapsed < duration and not stop_event.is_set():
		on_sec = max(1, int(random.expovariate(1.0 / profile['mean_on_sec'])))
		on_sec = min(on_sec, duration - elapsed)
		if on_sec <= 0:
			break
		try:
			data = _run_iperf3(
				bind_ip=network['bind_ip'],
				server_ip=network['server_ip'],
				port=profile.get('on_off_port', 5202),
				duration=on_sec,
				protocol=profile['protocol'],
				target_bps=profile['on_off_bps'],
			)
			summary = _extract_summary(slice_name, profile['protocol'], data, label='on_off')
			logger.info(
				'%s on_off burst: rx=%.2f Mbps', slice_name, summary.get('receiver_mbps', 0)
			)
			results.append(summary)
		except Exception as e:
			logger.error('%s on_off burst failed: %s', slice_name, e)
			results.append({'slice': slice_name, 'component': 'on_off', 'error': str(e)})

		elapsed += on_sec
		if elapsed >= duration or stop_event.is_set():
			break

		off_sec = max(1, int(random.expovariate(1.0 / profile['mean_off_sec'])))
		off_sec = min(off_sec, duration - elapsed)
		stop_event.wait(timeout=off_sec)
		elapsed += off_sec

	return results


def run_mixed_slice(
	slice_name: str, profile: dict, network: dict, duration: int
) -> list[dict]:
	results = []
	stop_event = threading.Event()

	def continuous():
		try:
			data = _run_iperf3(
				bind_ip=network['bind_ip'],
				server_ip=network['server_ip'],
				port=profile.get('continuous_port', 5201),
				duration=duration,
				protocol=profile['protocol'],
				target_bps=profile['continuous_bps'],
			)
			summary = _extract_summary(
				slice_name, profile['protocol'], data, label='continuous'
			)
			logger.info(
				'%s continuous: rx=%.2f Mbps', slice_name, summary.get('receiver_mbps', 0)
			)
			results.append(summary)
		except Exception as e:
			logger.error('%s continuous failed: %s', slice_name, e)
			results.append({'slice': slice_name, 'component': 'continuous', 'error': str(e)})
		finally:
			stop_event.set()

	t = threading.Thread(target=continuous, daemon=True)
	t.start()

	on_off_results = run_on_off_component(
		slice_name, profile, network, duration, stop_event
	)
	results.extend(on_off_results)

	t.join()
	return results


def run_slice(slice_name: str, profile: dict, duration: int) -> list[dict]:
	network = SLICE_NETWORK[slice_name]
	pattern = profile.get('pattern', 'continuous')
	logger.info('Starting %s (%s pattern)', slice_name, pattern)

	if pattern == 'mixed':
		return run_mixed_slice(slice_name, profile, network, duration)
	else:
		return run_continuous_slice(slice_name, profile, network, duration)


def save_results(results: list[dict], output_dir: Path) -> None:
	ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
	path = output_dir / f'results_{ts}.json'
	with open(path, 'w') as f:
		json.dump(results, f, indent=2)
	logger.info('Results saved to %s', path)


def main():
	parser = argparse.ArgumentParser(description='Per-slice iperf3 traffic generator')
	parser.add_argument(
		'--slices',
		nargs='+',
		default=list(SLICE_NETWORK.keys()),
		help='Slices to run (default: all)',
	)
	parser.add_argument(
		'--loops', type=int, default=0, help='Number of loops (0 = run forever)'
	)
	args = parser.parse_args()

	profiles, defaults = load_config()
	default_duration = defaults.get('duration_sec', 60)
	inter_loop_gap = defaults.get('inter_loop_gap_sec', 5)
	LOG_DIR.mkdir(parents=True, exist_ok=True)

	active_slices = [s for s in args.slices if s in profiles]
	if not active_slices:
		logger.error('No valid slices specified')
		return

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

		logger.info('--- Loop %d ---', loop)
		results = []
		slice_results: dict[str, list] = {}

		def run_and_collect(name, prof, dur):
			slice_results[name] = run_slice(name, prof, dur)

		threads = []
		for name in active_slices:
			if not running:
				break
			dur = profiles[name].get('duration_sec', default_duration)
			t = threading.Thread(
				target=run_and_collect, args=(name, profiles[name], dur), daemon=True
			)
			threads.append(t)
			t.start()

		for t in threads:
			t.join()

		for name in active_slices:
			results.extend(slice_results.get(name, []))

		if results:
			save_results(results, LOG_DIR)

		if running and inter_loop_gap > 0:
			logger.info('Waiting %ds before next loop...', inter_loop_gap)
			time.sleep(inter_loop_gap)

	logger.info('Traffic generator stopped.')


if __name__ == '__main__':
	main()
