#!/usr/bin/env python3
# scripts/traffic_generator.py
# Runs continuous per-slice iperf3 traffic through the 5G GTP tunnels.
# All slices run concurrently. Reads config/traffic.yaml.
# Outputs JSON results per loop to logs/traffic/.

import argparse
import json
import logging
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
	defaults = config.get('defaults', {})
	return config['traffic_profiles'], defaults


def build_cmd(
	slice_name: str, profile: dict, network: dict, duration: int
) -> list[str]:
	cmd = [
		'docker',
		'exec',
		'ueransim',
		'iperf3',
		'-c',
		network['server_ip'],
		'-B',
		network['bind_ip'],
		'-t',
		str(duration),
		'-J',
	]
	if profile['protocol'] == 'udp':
		cmd += [
			'-u',
			'-b',
			str(profile['target_bps']),
			'-l',
			str(profile.get('packet_size', 1400)),
		]
	else:
		cmd += ['-P', str(profile['parallel_flows'])]
	return cmd


def extract_summary(slice_name: str, protocol: str, data: dict) -> dict:
	ts = datetime.now(timezone.utc).isoformat()
	end = data.get('end', {})
	summary = {'slice': slice_name, 'timestamp': ts, 'protocol': protocol}

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


def run_slice(slice_name: str, profile: dict, duration: int) -> dict:
	network = SLICE_NETWORK[slice_name]
	cmd = build_cmd(slice_name, profile, network, duration)
	logger.info(
		'Starting %s: %s → %s (%s)',
		slice_name,
		network['bind_ip'],
		network['server_ip'],
		profile['protocol'],
	)
	try:
		result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 15)
		if result.returncode != 0:
			logger.error('%s failed: %s', slice_name, result.stderr.strip())
			return {'slice': slice_name, 'error': result.stderr.strip()}
		data = json.loads(result.stdout)
		summary = extract_summary(slice_name, profile['protocol'], data)
		logger.info(
			'%s: rx=%.2f Mbps loss=%.1f%%',
			slice_name,
			summary.get('receiver_mbps', 0),
			summary.get('loss_pct', 0),
		)
		return summary
	except subprocess.TimeoutExpired:
		logger.error('%s timed out', slice_name)
		return {'slice': slice_name, 'error': 'timeout'}
	except json.JSONDecodeError as e:
		logger.error('%s JSON parse error: %s', slice_name, e)
		return {'slice': slice_name, 'error': 'json_parse_error'}


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

		with ThreadPoolExecutor(max_workers=len(active_slices)) as executor:
			futures = {
				executor.submit(
					run_slice,
					name,
					profiles[name],
					profiles[name].get('duration_sec', default_duration),
				): name
				for name in active_slices
				if running
			}
			for future in as_completed(futures):
				results.append(future.result())

		if results:
			save_results(results, LOG_DIR)

		if running and inter_loop_gap > 0:
			logger.info('Waiting %ds before next loop...', inter_loop_gap)
			time.sleep(inter_loop_gap)

	logger.info('Traffic generator stopped.')


if __name__ == '__main__':
	main()
