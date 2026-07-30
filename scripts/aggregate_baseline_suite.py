#!/usr/bin/env python3
"""
scripts/aggregate_baseline_suite.py

Reads all *.json files in a given suite directory (produced by
run_baseline_suite.py) and produces a markdown summary table: mean
+/- std overall_sla_pct per policy per scenario, across repeats.

Usage:
  uv run python scripts/aggregate_baseline_suite.py logs/eval/20260729_101500
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('suite_dir', help='e.g. logs/eval/20260729_101500')
	args = parser.parse_args()

	suite_dir = Path(args.suite_dir)
	files = sorted(suite_dir.glob('*.json'))
	if not files:
		print(f'No .json files found in {suite_dir}')
		return

	data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
	per_slice: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
		lambda: defaultdict(lambda: defaultdict(list))
	)

	for f in files:
		payload = json.loads(f.read_text())
		scenario = payload['scenario']
		for policy, run in payload['runs'].items():
			if run['overall_sla_pct'] is not None:
				data[scenario][policy].append(run['overall_sla_pct'])
			for slice_name, slice_result in run['per_slice'].items():
				if slice_result['sla_pct'] is not None:
					per_slice[scenario][policy][slice_name].append(slice_result['sla_pct'])

	print('# Baseline Evaluation Suite -- Summary\n')
	print(f'Source: {suite_dir} ({len(files)} run(s) across {len(data)} scenario(s))\n')

	for scenario, policies in data.items():
		print(f'## Scenario: {scenario}\n')
		print('| Policy | Mean SLA% | Std | N runs |')
		print('|---|---|---|---|')
		for policy, values in policies.items():
			arr = np.array(values)
			print(f'| {policy} | {arr.mean():.1f} | {arr.std():.1f} | {len(arr)} |')
		print()

		print('### Per-slice mean SLA% (across repeats)\n')
		slice_names = sorted(next(iter(per_slice[scenario].values())).keys())
		header = '| Policy | ' + ' | '.join(slice_names) + ' |'
		sep = '|---|' + '---|' * len(slice_names)
		print(header)
		print(sep)
		for policy in policies:
			row = [policy]
			for slice_name in slice_names:
				vals = per_slice[scenario][policy].get(slice_name, [])
				row.append(f'{np.mean(vals):.1f}' if vals else 'N/A')
			print('| ' + ' | '.join(row) + ' |')
		print()


if __name__ == '__main__':
	main()
