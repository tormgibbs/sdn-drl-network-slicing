# 03_reward_delta_grid.py
"""
Compare the policy's chosen allocation against a grid of counter-allocations
(shift X% from one slice to another), scored via the REAL reward function on
REAL in-distribution rollout states -- not synthetic observations.

IMPORTANT: reads env._last_metrics (cached by reset()/step()), never calls
env._compute_metrics() directly -- that has a side effect (advances on/off
timers) and would score against a different tick than the policy observed.

USAGE:
    uv run python 03_reward_delta_grid.py --model-path models/ironwood/final \
        --n-episodes 2000 --counters VLE:SP VLE:admin admin:SP \
        --sweep-counter VLE:SP --sweep-sizes 0.03 0.05 0.10 0.15 0.20
"""

import argparse

import numpy as np
import yaml
from stable_baselines3 import PPO

from agent.project_allocation import project_allocation
from agent.sim_env import _CONGESTION_THRESHOLD, W1, W2, W3, W4, W5, W6, SimCampusEnv


def full_reward(rates_kbps, metrics, slice_order, slices_cfg):
	n = len(slice_order)
	r_sla = p_lat = p_loss = p_cong = r_util = 0.0
	fr = []
	for name in slice_order:
		m = metrics[name]
		s = slices_cfg[name]
		si, Li, Li_loss = s['priority'], s['max_latency_ms'], s['max_loss_pct']
		p_lat += si * max(0.0, (m['latency_ms'] - Li) / Li)
		sla_met = m['latency_ms'] <= Li and m['loss_pct'] <= Li_loss
		r_sla += si * (1.0 if sla_met else 0.0)
		p_loss += si * (m['loss_pct'] / 100.0)
		ceil = rates_kbps[name] * 1000
		util = min(m['tx_throughput_bps'] / ceil, 1.0) if ceil > 0 else 0.0
		r_util += util
		p_cong += si * max(0.0, util - _CONGESTION_THRESHOLD)
		fr.append(rates_kbps[name] / si)
	r_util /= n
	sr, ssq = sum(fr), sum(x**2 for x in fr)
	pf = 1.0 - (sr**2) / (n * ssq) if ssq > 0 else 0.0
	return W1 * r_sla - W2 * p_lat - W3 * p_loss - W4 * p_cong + W5 * r_util - W6 * pf


def make_counter(fracs, from_idx, to_idx, delta=0.10):
	c = fracs.copy()
	c[from_idx] = max(0.05, c[from_idx] - delta)
	c[to_idx] = min(0.60, c[to_idx] + delta)
	s = sum(c)
	return [x / s for x in c]


def parse_counters(
	pairs: list[str], slice_order: list[str]
) -> dict[str, tuple[int, int]]:
	"""Parse 'FROM:TO' strings (slice names) into {label: (from_idx, to_idx)}."""
	result = {}
	for pair in pairs:
		frm, to = pair.split(':')
		result[f'{frm}->{to}'] = (
			slice_order.index(frm.lower()),
			slice_order.index(to.lower()),
		)
	return result


def main() -> None:
	parser = argparse.ArgumentParser(
		description='Reward-delta grid vs counter-allocations'
	)
	parser.add_argument('--slices-config', default='config/slices.yaml')
	parser.add_argument('--model-path', required=True)
	parser.add_argument('--n-episodes', type=int, default=2000)
	parser.add_argument(
		'--counters',
		nargs='+',
		default=[
			'vle:student_portal',
			'vle:admin',
			'admin:student_portal',
			'admin:vle',
			'general:student_portal',
			'general:vle',
		],
		help='FROM:TO slice-name pairs, e.g. vle:student_portal',
	)
	parser.add_argument(
		'--sweep-counter',
		default='vle:student_portal',
		help='FROM:TO pair to run the step-size sweep on',
	)
	parser.add_argument(
		'--sweep-sizes', nargs='+', type=float, default=[0.03, 0.05, 0.10, 0.15, 0.20]
	)
	parser.add_argument('--sweep-episodes', type=int, default=500)
	args = parser.parse_args()

	slices_cfg_full = yaml.safe_load(open(args.slices_config))
	slice_order = slices_cfg_full['slice_order']
	slices_cfg = slices_cfg_full['slices']
	C_kbps = slices_cfg_full['network']['total_bandwidth_bps'] // 1000
	floors_kbps = [
		max(1, slices_cfg[n]['min_throughput_bps'] // 1000) for n in slice_order
	]

	counters = parse_counters(args.counters, slice_order)

	model = PPO.load(args.model_path)
	env = SimCampusEnv(slices_cfg_full)

	counter_wins = {k: 0 for k in counters}
	counter_deltas = {k: [] for k in counters}
	found = 0

	for _ in range(args.n_episodes):
		obs, _ = env.reset()
		metrics = env._last_metrics
		action, _ = model.predict(obs, deterministic=True)
		exp = np.exp(action)
		fracs = (exp / exp.sum()).tolist()

		rates_policy = dict(
			zip(slice_order, project_allocation(fracs, floors_kbps, C_kbps))
		)
		r_policy = full_reward(rates_policy, metrics, slice_order, slices_cfg)
		found += 1

		for name, (fi, ti) in counters.items():
			cf = make_counter(fracs, fi, ti)
			rates_c = dict(zip(slice_order, project_allocation(cf, floors_kbps, C_kbps)))
			r_c = full_reward(rates_c, metrics, slice_order, slices_cfg)
			counter_deltas[name].append(r_c - r_policy)
			if r_c > r_policy:
				counter_wins[name] += 1

	print(f'=== Delta analysis over {found} episodes ===')
	print(
		f'{"Counter":<25} {"win_rate":<10} {"mean_delta":<12} {"median_delta":<14} {"mean_win_delta"}'
	)
	print('-' * 75)
	for name, deltas in counter_deltas.items():
		d = np.array(deltas)
		wins = (d > 0).mean()
		mean_win = d[d > 0].mean() if (d > 0).any() else 0.0
		print(
			f'{name:<25} {wins:<10.1%} {d.mean():<12.5f} {np.median(d):<14.5f} {mean_win:.5f}'
		)

	fi, ti = counters.get(
		args.sweep_counter.replace(':', '->'),
		parse_counters([args.sweep_counter], slice_order)[
			args.sweep_counter.replace(':', '->')
		],
	)
	print(f'\n=== {args.sweep_counter} step-size sweep ===')
	print(f'{"delta":<10} {"win_rate":<12} {"mean_delta"}')
	print('-' * 35)
	for delta in args.sweep_sizes:
		wins, deltas = 0, []
		for _ in range(args.sweep_episodes):
			obs, _ = env.reset()
			metrics = env._last_metrics
			action, _ = model.predict(obs, deterministic=True)
			exp = np.exp(action)
			fracs = (exp / exp.sum()).tolist()
			rates_policy = dict(
				zip(slice_order, project_allocation(fracs, floors_kbps, C_kbps))
			)
			r_policy = full_reward(rates_policy, metrics, slice_order, slices_cfg)
			cf = make_counter(fracs, fi, ti, delta=delta)
			rates_c = dict(zip(slice_order, project_allocation(cf, floors_kbps, C_kbps)))
			r_c = full_reward(rates_c, metrics, slice_order, slices_cfg)
			deltas.append(r_c - r_policy)
			if r_c > r_policy:
				wins += 1
		d = np.array(deltas)
		print(f'{delta:<10} {wins / len(deltas):<12.1%} {d.mean():.5f}')


if __name__ == '__main__':
	main()
