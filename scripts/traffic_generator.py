#!/usr/bin/env python3
# scripts/traffic_generator.py
# CLI adapter over traffic.runner.TrafficRunner. Foreground process;
# SIGINT/SIGTERM call runner.request_stop() -- only safe here because
# signal.signal() requires the main thread, which this script owns.

import argparse
import json
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path

from traffic.runner import TRAFFIC_CONFIG_PATH, TrafficRunner, load_traffic_config

LOG_DIR = Path('logs/traffic')

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger('traffic_generator')


def save_results(results: list[dict], output_dir: Path) -> None:
	ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
	path = output_dir / f'results_{ts}.json'
	with open(path, 'w') as f:
		json.dump(results, f, indent=2)
	logger.info('Results saved to %s', path)


def main():
	_, _, scenarios = load_traffic_config(TRAFFIC_CONFIG_PATH)
	logger.info('Using traffic profile: %s', TRAFFIC_CONFIG_PATH.resolve().name)

	parser = argparse.ArgumentParser(
		description='Per-slice bidirectional iperf3 traffic generator'
	)
	parser.add_argument('--slices', nargs='+', default=None)
	parser.add_argument('--loops', type=int, default=0)
	parser.add_argument(
		'--scenario',
		choices=list(scenarios.keys()),
		default=None,
		help='Fix scenario for all loops. Omit to sample randomly each loop.',
	)
	parser.add_argument(
		'--seed',
		type=int,
		default=None,
		help='Seed for scenario/factor/burst-timing RNG. Omit for a nondeterministic run.',
	)
	args = parser.parse_args()

	LOG_DIR.mkdir(parents=True, exist_ok=True)

	try:
		runner = TrafficRunner(
			slices=args.slices,
			loops=args.loops,
			scenario=args.scenario,
			seed=args.seed,
		)
	except ValueError as e:
		logger.error(str(e))
		return

	def handle_signal(sig, frame):
		logger.info('Shutting down...')
		runner.request_stop()

	signal.signal(signal.SIGINT, handle_signal)
	signal.signal(signal.SIGTERM, handle_signal)

	logger.info('Verifying tunnels and starting downlink servers...')
	runner.setup()

	def on_loop_start(loop, scenario_name):
		logger.info('--- Loop %d | scenario=%s ---', loop, scenario_name)

	def on_loop_complete(loop, scenario_name, results, failed_slices):
		logger.info('--- Loop %d complete | scenario=%s ---', loop, scenario_name)
		if failed_slices:
			logger.warning('Slices with complete failure: %s', failed_slices)
		if results:
			save_results(results, LOG_DIR)

	runner.run(on_loop_complete, on_loop_start=on_loop_start)

	logger.info('Traffic generator stopped.')


if __name__ == '__main__':
	main()
