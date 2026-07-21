# 02_observation_reachability_check.py
"""
Check whether a hand-crafted synthetic observation vector is actually
reachable under real rollouts, before trusting any eval/probe built on it.

USAGE:
    uv run python 02_observation_reachability_check.py --slice-index 1 \
        --latency-threshold 0.15 --loss-exact 0.0 --util-threshold 0.25
"""

import argparse

import numpy as np
import yaml

from agent.sim_env import SimCampusEnv


def main() -> None:
	parser = argparse.ArgumentParser(
		description='Check reachability of a synthetic observation'
	)
	parser.add_argument('--slices-config', default='config/slices.yaml')
	parser.add_argument('--n-episodes', type=int, default=500)
	parser.add_argument('--steps-per-episode', type=int, default=20)
	parser.add_argument(
		'--slice-index',
		type=int,
		default=0,
		help='0=vle 1=student_portal 2=admin 3=iot 4=general (per slice_order)',
	)
	parser.add_argument('--latency-threshold', type=float, default=0.15)
	parser.add_argument('--loss-exact', type=float, default=0.0)
	parser.add_argument('--util-threshold', type=float, default=0.25)
	args = parser.parse_args()

	slices_cfg = yaml.safe_load(open(args.slices_config))
	env = SimCampusEnv(slices_cfg)

	samples = []
	for _ in range(args.n_episodes):
		obs, _ = env.reset()
		for _ in range(args.steps_per_episode):
			action = env.action_space.sample()
			obs, _, terminated, truncated, _ = env.step(action)
			start = args.slice_index * 3
			samples.append(obs[start : start + 3].tolist())
			if terminated or truncated:
				break

	arr = np.array(samples)
	lat, loss, util = arr[:, 0], arr[:, 1], arr[:, 2]

	print(
		f'Observation range over {args.n_episodes} episodes x up to {args.steps_per_episode} steps '
		f'(slice index {args.slice_index}):'
	)
	print(f'  latency_i: min={lat.min():.3f} max={lat.max():.3f} mean={lat.mean():.3f}')
	print(
		f'  loss_i:    min={loss.min():.3f} max={loss.max():.3f} mean={loss.mean():.3f}'
	)
	print(
		f'  util_i:    min={util.min():.3f} max={util.max():.3f} mean={util.mean():.3f}'
	)

	print(
		f'\nFraction matching latency_i < {args.latency_threshold}: {(lat < args.latency_threshold).mean():.3f}'
	)
	print(
		f'Fraction matching loss_i == {args.loss_exact}:          {(loss == args.loss_exact).mean():.3f}'
	)
	print(
		f'Fraction matching util_i < {args.util_threshold}:        {(util < args.util_threshold).mean():.3f}'
	)

	all_match = (
		(lat < args.latency_threshold)
		& (loss == args.loss_exact)
		& (util < args.util_threshold)
	)
	print(f'\nFraction matching ALL THREE synthetic conditions: {all_match.mean():.4f}')
	print('(If this is near 0, the synthetic probe is out-of-distribution --')
	print(" don't trust checkpoint behaviour on it as representative.)")


if __name__ == '__main__':
	main()
