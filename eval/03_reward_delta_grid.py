"""
Compare the policy's chosen allocation against a grid of counter-allocations
(shift X% from one slice to another), scored via the REAL reward function on
REAL in-distribution rollout states -- not synthetic observations.

WHY THIS EXISTS:
Win-rate alone ("counter beats policy 63% of the time") can't tell you
whether a gap is a real convergence problem or noise near a shallow local
optimum. This script reports both win-rate AND mean/median delta magnitude,
plus a step-size sweep, which together locate whether the policy sits near
the true optimum (small delta, sweep peaks and reverses) or is genuinely
far off (large delta, sweep keeps improving as you increase the shift).

IMPORTANT BUG THIS SCRIPT AVOIDS:
Do NOT call env._compute_metrics() directly -- it has a side effect
(advances on/off burst timers). reset() and step() already call it
internally to build the returned observation, and cache the result on
env._last_metrics. Calling _compute_metrics() again after reset()/step()
scores the reward against a traffic state one tick ahead of what the
policy actually observed and acted on -- even a single extra call is a
bug. This script reads env._last_metrics (the cached result), never
calls _compute_metrics() itself.

USAGE:
    uv run python 03_reward_delta_grid.py
"""

import numpy as np
import yaml
from stable_baselines3 import PPO

from agent.project_allocation import project_allocation
from agent.sim_env import _CONGESTION_THRESHOLD, W1, W2, W3, W4, W5, W6, SimCampusEnv

SLICES_CONFIG_PATH = 'config/slices.yaml'
MODEL_PATH = 'models/hawthorn/final'
N_EPISODES = 2000

# (from_slice_index, to_slice_index) pairs to test as counter-allocations.
# Indices follow slice_order in slices.yaml (typically vle, sp, admin, iot, general).
COUNTERS = {
	'VLE->SP': (0, 1),
	'VLE->admin': (0, 2),
	'admin->SP': (2, 1),
	'admin->VLE': (2, 0),
	'general->SP': (4, 1),
	'general->VLE': (4, 0),
}

STEP_SIZES = [0.03, 0.05, 0.10, 0.15, 0.20]
STEP_SIZE_COUNTER = 'VLE->SP'  # which pair to sweep step size for


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


def main() -> None:
	slices_cfg_full = yaml.safe_load(open(SLICES_CONFIG_PATH))
	slice_order = slices_cfg_full['slice_order']
	slices_cfg = slices_cfg_full['slices']
	C_kbps = slices_cfg_full['network']['total_bandwidth_bps'] // 1000
	floors_kbps = [
		max(1, slices_cfg[n]['min_throughput_bps'] // 1000) for n in slice_order
	]

	model = PPO.load(MODEL_PATH)
	env = SimCampusEnv(slices_cfg_full)

	counter_wins = {k: 0 for k in COUNTERS}
	counter_deltas = {k: [] for k in COUNTERS}
	found = 0

	for _ in range(N_EPISODES):
		obs, _ = env.reset()
		metrics = env._last_metrics  # call exactly ONCE, matches obs/predict below
		action, _ = model.predict(obs, deterministic=True)
		exp = np.exp(action)
		fracs = (exp / exp.sum()).tolist()

		rates_policy = dict(
			zip(slice_order, project_allocation(fracs, floors_kbps, C_kbps))
		)
		r_policy = full_reward(rates_policy, metrics, slice_order, slices_cfg)
		found += 1

		for name, (fi, ti) in COUNTERS.items():
			cf = make_counter(fracs, fi, ti)
			rates_c = dict(zip(slice_order, project_allocation(cf, floors_kbps, C_kbps)))
			r_c = full_reward(rates_c, metrics, slice_order, slices_cfg)
			counter_deltas[name].append(r_c - r_policy)
			if r_c > r_policy:
				counter_wins[name] += 1

	print(f'=== Delta analysis over {found} episodes ===')
	print(
		f'{"Counter":<20} {"win_rate":<10} {"mean_delta":<12} {"median_delta":<14} {"mean_win_delta"}'
	)
	print('-' * 70)
	for name, deltas in counter_deltas.items():
		d = np.array(deltas)
		wins = (d > 0).mean()
		mean_win = d[d > 0].mean() if (d > 0).any() else 0.0
		print(
			f'{name:<20} {wins:<10.1%} {d.mean():<12.5f} {np.median(d):<14.5f} {mean_win:.5f}'
		)

	# Step-size sweep for one counter pair -- locates where the true
	# local optimum sits relative to the policy's current allocation.
	fi, ti = COUNTERS[STEP_SIZE_COUNTER]
	print(f'\n=== {STEP_SIZE_COUNTER} step-size sweep ===')
	print(f'{"delta":<10} {"win_rate":<12} {"mean_delta"}')
	print('-' * 35)
	for delta in STEP_SIZES:
		wins, deltas = 0, []
		for _ in range(500):
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
