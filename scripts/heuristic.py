#!/usr/bin/env python3
# scripts/heuristic.py
import argparse
import logging
import signal

import yaml

from agent.heuristic_runner import HeuristicRunner

SLICES_CONFIG_PATH = 'config/slices.yaml'
logging.basicConfig(level=logging.INFO)


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'--steps', type=int, default=0, help='Number of steps (0 = infinite)'
	)
	parser.add_argument('--log', type=str, default=None, help='Log file path (optional)')
	args = parser.parse_args()

	with open(SLICES_CONFIG_PATH) as f:
		slices_config = yaml.safe_load(f)
	slice_order = slices_config['slice_order']

	print('Starting rule-based heuristic baseline')
	runner = HeuristicRunner(slice_order)

	def handle_signal(sig, frame):
		print('\nStop requested -- finishing current step, will exit between steps...')
		runner.request_stop()

	signal.signal(signal.SIGINT, handle_signal)
	signal.signal(signal.SIGTERM, handle_signal)

	log_file = open(args.log, 'w') if args.log else None

	def on_step(result) -> None:
		alloc_str = ' '.join(f'{n[:3]}={v}k' for n, v in result.allocation_kbps.items())
		trig_str = f' TRIGGERED={result.triggered}' if result.triggered else ''
		line = f'[{result.timestamp}] step={result.step:04d} | {alloc_str}{trig_str}'
		print(line)
		if log_file:
			log_file.write(line + '\n')
			log_file.flush()

	print(f'steps={"infinite" if args.steps == 0 else args.steps}')
	print('Press Ctrl+C to stop\n')
	try:
		runner.run(on_step, max_steps=args.steps)
	finally:
		if log_file:
			log_file.close()
		runner.close()
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
