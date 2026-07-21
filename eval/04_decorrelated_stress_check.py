# 04_decorrelated_stress_check.py
"""
Filter real 'chaos' scenario episodes for a specific decorrelated stress
combination, and check what the policy actually does in those genuine,
in-distribution states.

USAGE:
    uv run python 04_decorrelated_stress_check.py --model-path models/ironwood/final \
        --slice-a student_portal --slice-a-min-factor 1.1 \
        --slice-b admin --slice-b-max-factor 0.7
"""

import argparse

import numpy as np
import yaml
from stable_baselines3 import PPO

from agent.sim_env import SimCampusEnv


def main() -> None:
	parser = argparse.ArgumentParser(
		description='Check policy behavior on decorrelated stress states'
	)
	parser.add_argument('--slices-config', default='config/slices.yaml')
	parser.add_argument('--model-path', required=True)
	parser.add_argument('--n-episodes', type=int, default=500)
	parser.add_argument('--slice-a', required=True, help='slice you want stressed')
	parser.add_argument('--slice-a-min-factor', type=float, default=1.1)
	parser.add_argument('--slice-b', required=True, help='slice you want NOT stressed')
	parser.add_argument('--slice-b-max-factor', type=float, default=0.7)
	args = parser.parse_args()

	slices_cfg = yaml.safe_load(open(args.slices_config))
	slice_order = slices_cfg['slice_order']
	env = SimCampusEnv(slices_cfg)
	model = PPO.load(args.model_path)

	found = 0
	for _ in range(args.n_episodes):
		obs, _ = env.reset()
		if env._scenario != 'chaos':
			continue
		a_factor = env._factors[args.slice_a]
		b_factor = env._factors[args.slice_b]
		if not (a_factor > args.slice_a_min_factor and b_factor < args.slice_b_max_factor):
			continue

		action, _ = model.predict(obs, deterministic=True)
		exp = np.exp(action)
		fracs = exp / exp.sum()
		alloc_str = '  '.join(
			f'{name}={fracs[i]:.3f}' for i, name in enumerate(slice_order)
		)
		print(
			f'{args.slice_a}_factor={a_factor:.2f} {args.slice_b}_factor={b_factor:.2f} -> {alloc_str}'
		)
		found += 1

	print(
		f'\n{found} matching episodes out of {args.n_episodes} '
		f'({args.slice_a} stressed >{args.slice_a_min_factor}, '
		f'{args.slice_b} light <{args.slice_b_max_factor})'
	)
	if found < 20:
		print('Few matches -- consider raising --n-episodes for a more reliable read.')


if __name__ == '__main__':
	main()
