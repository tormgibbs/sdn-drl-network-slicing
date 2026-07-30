#!/usr/bin/env python3
"""
scripts/evaluate_baselines.py

Sequentially evaluates static, heuristic, and agent control under a
fixed traffic scenario, sampling /metrics and computing per-slice SLA
satisfaction % and violation counts per policy.

Usage:
  python scripts/evaluate_baselines.py --scenario general_spike \
      --duration 900 --model-path models/selected/magnolia --algo ppo
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

API_BASE = 'http://localhost:8080'
SLICES_CONFIG_PATH = Path('config/slices.yaml')
SAMPLE_INTERVAL_SEC = 5


def _request(method: str, path: str, body: dict | None = None) -> dict:
	url = f'{API_BASE}{path}'
	data = json.dumps(body).encode() if body is not None else None
	headers = {'Content-Type': 'application/json'} if data else {}
	req = urllib.request.Request(url, data=data, method=method, headers=headers)
	with urllib.request.urlopen(req, timeout=15) as resp:
		return json.loads(resp.read())


def load_slice_thresholds() -> dict:
	with open(SLICES_CONFIG_PATH) as f:
		config = yaml.safe_load(f)
	return {
		name: {
			'min_throughput_bps': cfg['min_throughput_bps'],
			'max_latency_ms': cfg['max_latency_ms'],
			'max_loss_pct': cfg['max_loss_pct'],
		}
		for name, cfg in config['slices'].items()
	}


def compute_sla_status(metrics: dict, sla: dict) -> str:
	"""Mirrors frontend/src/lib/sla.ts exactly -- keep these two in
	sync if either changes, so evaluation results and the live
	dashboard never disagree on what counts as a violation."""
	tx = metrics['tx_throughput_bps']
	lat = metrics.get('latency_ms')
	loss = metrics.get('loss_pct')

	if tx < sla['min_throughput_bps']:
		return 'VIOLATION'
	if lat is not None and lat > sla['max_latency_ms']:
		return 'VIOLATION'
	if loss is not None and loss > sla['max_loss_pct']:
		return 'VIOLATION'

	if tx < sla['min_throughput_bps'] * 1.2:
		return 'WARNING'
	if lat is not None and lat > sla['max_latency_ms'] * 0.8:
		return 'WARNING'
	if loss is not None and loss > sla['max_loss_pct'] * 0.8:
		return 'WARNING'

	return 'NOMINAL'


def switch_controller(
	controller: str, model_path: str | None = None, algo: str = 'ppo'
) -> None:
	body = {'controller': controller}
	if controller == 'agent':
		if not model_path:
			raise ValueError('model_path required to switch to agent')
		body['model_path'] = model_path
		body['algo'] = algo
	print(f'  switching controller -> {controller} ...')
	result = _request('POST', '/controller/switch', body)
	print(f'  switched: {result["previous_controller"]} -> {result["active_controller"]}')


def run_policy_window(duration_sec: int, thresholds: dict) -> dict:
	slice_names = list(thresholds.keys())
	per_slice_counts = {
		name: {'NOMINAL': 0, 'WARNING': 0, 'VIOLATION': 0} for name in slice_names
	}
	overall_counts = {'NOMINAL': 0, 'WARNING': 0, 'VIOLATION': 0}

	deadline = time.monotonic() + duration_sec
	while time.monotonic() < deadline:
		try:
			metrics = _request('GET', '/metrics')
		except (urllib.error.URLError, urllib.error.HTTPError) as exc:
			print(f'  warning: /metrics fetch failed ({exc}), skipping sample')
			time.sleep(SAMPLE_INTERVAL_SEC)
			continue

		for name in slice_names:
			if name not in metrics:
				continue
			status = compute_sla_status(metrics[name], thresholds[name])
			per_slice_counts[name][status] += 1
			overall_counts[status] += 1

		time.sleep(SAMPLE_INTERVAL_SEC)

	per_slice = {}
	for name in slice_names:
		total = sum(per_slice_counts[name].values())
		per_slice[name] = {
			'sla_pct': round(per_slice_counts[name]['NOMINAL'] / total * 100, 1)
			if total
			else None,
			'violations': per_slice_counts[name]['VIOLATION'],
			'samples': total,
		}

	overall_total = sum(overall_counts.values())
	overall_sla_pct = (
		round(overall_counts['NOMINAL'] / overall_total * 100, 1) if overall_total else None
	)

	return {
		'overall_sla_pct': overall_sla_pct,
		'per_slice': per_slice,
	}


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--scenario', required=True)
	parser.add_argument('--duration', type=int, default=900)
	parser.add_argument('--model-path', default=None)
	parser.add_argument('--algo', default='ppo', choices=['ppo', 'sac'])
	parser.add_argument(
		'--policies',
		nargs='+',
		default=['static', 'heuristic', 'agent'],
		choices=['static', 'heuristic', 'agent'],
	)
	parser.add_argument('--output', default=None)
	args = parser.parse_args()

	if 'agent' in args.policies and not args.model_path:
		parser.error("--model-path is required when evaluating 'agent'")

	print('Checking traffic generator is running...')
	traffic_status = _request('GET', '/traffic/state')
	if not traffic_status['running']:
		raise RuntimeError(
			'Traffic generator is not running. Start it first (dashboard or '
			'CLI) so all policies are evaluated under real traffic.'
		)

	print(f'Setting traffic scenario -> {args.scenario}')
	_request('POST', '/traffic/scenario', {'scenario': args.scenario})

	thresholds = load_slice_thresholds()
	results = {}

	for controller in args.policies:
		print(f'\n=== Evaluating: {controller} ===')
		switch_controller(controller, model_path=args.model_path, algo=args.algo)
		print(f'  running for {args.duration}s, sampling every {SAMPLE_INTERVAL_SEC}s...')
		window_result = run_policy_window(args.duration, thresholds)
		results[controller] = window_result
		print(f'  {controller}: overall_sla_pct={window_result["overall_sla_pct"]}')

	output_path = (
		Path(args.output)
		if args.output
		else Path(
			f'logs/eval/eval_{args.scenario}_'
			f'{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.json'
		)
	)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	payload = {
		'scenario': args.scenario,
		'duration_sec': args.duration,
		'algo': args.algo,
		'policies_evaluated': args.policies,
		'runs': results,
		'timestamp': datetime.now(timezone.utc).isoformat(),
	}
	with open(output_path, 'w') as f:
		json.dump(payload, f, indent=2)

	print(f'\nResults written to {output_path}')


if __name__ == '__main__':
	main()
