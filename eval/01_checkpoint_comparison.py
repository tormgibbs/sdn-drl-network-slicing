# 01_checkpoint_comparison.py
"""
Compare PPO checkpoints via real multi-episode rollouts through SimCampusEnv,
using a shared seed sequence so every checkpoint is scored against the exact
same episodes (paired comparison -> much lower variance than independent
random rollouts per checkpoint).

USAGE:
    uv run python 01_checkpoint_comparison.py --models-root models/ironwood \
        --checkpoints ppo_slicing_80000 ppo_slicing_160000 final --n-episodes 1000
"""

import argparse

import numpy as np
import yaml
from stable_baselines3 import PPO

from agent.sim_env import SimCampusEnv


def run_checkpoint(model_path: str, slices_cfg: dict, seeds: list[int]) -> np.ndarray:
	model = PPO.load(model_path)
	env = SimCampusEnv(slices_cfg)
	episode_rewards = []
	for seed in seeds:
		obs, _ = env.reset(seed=seed)
		total = 0.0
		for _ in range(env.episode_length):
			action, _ = model.predict(obs, deterministic=True)
			obs, reward, terminated, truncated, _ = env.step(action)
			total += reward
			if terminated or truncated:
				break
		episode_rewards.append(total)
	return np.array(episode_rewards)


def main() -> None:
	parser = argparse.ArgumentParser(
		description='Compare PPO checkpoints via real rollouts'
	)
	parser.add_argument('--slices-config', default='config/slices.yaml')
	parser.add_argument('--models-root', required=True, help='e.g. models/ironwood')
	parser.add_argument(
		'--checkpoints',
		nargs='+',
		required=True,
		help='checkpoint filenames without .zip, e.g. ppo_slicing_80000 final',
	)
	parser.add_argument('--n-episodes', type=int, default=1000)
	args = parser.parse_args()

	slices_cfg = yaml.safe_load(open(args.slices_config))
	seeds = list(range(args.n_episodes))

	results = {}
	for ckpt in args.checkpoints:
		try:
			r = run_checkpoint(f'{args.models_root}/{ckpt}', slices_cfg, seeds)
			results[ckpt] = r
		except Exception as e:
			print(f'{ckpt:<25} FAILED: {e}')

	print(f'\n=== Unpaired stats (n={args.n_episodes} episodes each) ===')
	for ckpt, r in results.items():
		sem = r.std() / np.sqrt(len(r))
		print(f'{ckpt:<25} mean={r.mean():.3f} std={r.std():.3f} SEM={sem:.3f}')

	baseline_name = args.checkpoints[0]
	if baseline_name in results:
		baseline = results[baseline_name]
		print(f'\n=== Paired diff vs {baseline_name} ===')
		for ckpt, r in results.items():
			diff = r - baseline
			se = diff.std(ddof=1) / np.sqrt(len(diff))
			print(
				f'{ckpt:<25} mean_diff={diff.mean():+.4f} paired_SE={se:.4f} '
				f'({"significant" if abs(diff.mean()) > 2 * se else "not significant"} at ~2SE)'
			)


if __name__ == '__main__':
	main()
