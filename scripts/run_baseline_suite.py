#!/usr/bin/env python3
"""
scripts/run_baseline_suite.py

Runs evaluate_baselines.py across multiple scenarios and repeats,
writing all results into one timestamped (or named) subdirectory
under logs/eval/, so repeated suite runs never collide or overwrite
each other's results.

Usage:
  uv run python scripts/run_baseline_suite.py \
      --scenarios normal general_spike chaos \
      --repeats 3 --duration 300 \
      --model-path models/selected/magnolia.zip \
      --algo ppo \
      [--suite-name my_label]
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--scenarios', nargs='+', required=True)
	parser.add_argument('--repeats', type=int, default=3)
	parser.add_argument('--duration', type=int, default=300)
	parser.add_argument('--model-path', required=True)
	parser.add_argument('--algo', default='ppo', choices=['ppo', 'sac'])
	parser.add_argument('--policies', nargs='+', default=['static', 'heuristic', 'agent'])
	parser.add_argument(
		'--suite-name',
		default=None,
		help='defaults to a timestamp, e.g. 20260729_101500',
	)
	args = parser.parse_args()

	suite_name = args.suite_name or datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
	suite_dir = Path('logs/eval') / suite_name
	suite_dir.mkdir(parents=True, exist_ok=True)

	total_runs = len(args.scenarios) * args.repeats
	print(f'Suite: {suite_dir}')
	print(
		f'Running {total_runs} total runs '
		f'({len(args.scenarios)} scenarios x {args.repeats} repeats)'
	)

	run_num = 0
	for scenario in args.scenarios:
		for repeat in range(1, args.repeats + 1):
			run_num += 1
			print(f'\n{"#" * 70}')
			print(f'# Run {run_num}/{total_runs}: scenario={scenario} repeat={repeat}')
			print(f'{"#" * 70}\n')

			output_path = suite_dir / f'{scenario}_repeat{repeat}.json'

			cmd = [
				sys.executable,
				'scripts/evaluate_baselines.py',
				'--scenario',
				scenario,
				'--duration',
				str(args.duration),
				'--model-path',
				args.model_path,
				'--algo',
				args.algo,
				'--policies',
				*args.policies,
				'--output',
				str(output_path),
			]
			result = subprocess.run(cmd)
			if result.returncode != 0:
				print(
					f'WARNING: run {run_num} failed (scenario={scenario} '
					f'repeat={repeat}) -- continuing with remaining runs'
				)

	print(f'\nSuite complete. Results in {suite_dir}/')


if __name__ == '__main__':
	main()
