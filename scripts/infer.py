#!/usr/bin/env python3
# scripts/infer.py
import argparse
import time

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from agent.env import CampusSlicingEnv

SLICES_CONFIG_PATH = 'config/slices.yaml'


def make_env() -> CampusSlicingEnv:
	with open(SLICES_CONFIG_PATH) as f:
		slices_config = yaml.safe_load(f)
	return CampusSlicingEnv(
		slices_config=slices_config, ue_profiles=None, episode_length=999999
	)


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument('--model', type=str, required=True, help='Path to model zip file')
	parser.add_argument(
		'--vecnorm', type=str, default=None, help='Path to VecNormalize stats pkl'
	)
	parser.add_argument(
		'--steps', type=int, default=0, help='Number of steps (0 = infinite)'
	)
	parser.add_argument('--log', type=str, default=None, help='Log file path (optional)')
	args = parser.parse_args()

	model_path = args.model
	if not model_path.endswith('.zip'):
		model_path = model_path + '.zip'

	print(f'Loading model from {model_path}')

	env = make_env()
	vec_env = DummyVecEnv([lambda: Monitor(env)])

	if args.vecnorm:
		print(f'Loading VecNormalize stats from {args.vecnorm}')
		vec_env = VecNormalize.load(args.vecnorm, vec_env)
		vec_env.training = False
		vec_env.norm_reward = False

	model = PPO.load(model_path, env=vec_env)
	obs = vec_env.reset()
	step = 0

	log_file = open(args.log, 'w') if args.log else None

	def log(line: str) -> None:
		print(line)
		if log_file:
			log_file.write(line + '\n')
			log_file.flush()

	log(
		f'Starting inference: model={model_path} steps={"infinite" if args.steps == 0 else args.steps}'
	)
	log('Press Ctrl+C to stop\n')

	try:
		while True:
			action, _ = model.predict(obs, deterministic=True)
			obs, reward, done, info = vec_env.step(action)
			step += 1

			ts = time.strftime('%H:%M:%S')
			raw_env = env

			alloc = {
				name: raw_env._current_rates_kbps.get(name, 0) for name in raw_env.slice_order
			}
			alloc_str = ' '.join(f'{n[:3]}={v}k' for n, v in alloc.items())

			log(f'[{ts}] step={step:04d} reward={reward[0]:.4f} | {alloc_str}')

			if done[0]:
				obs = vec_env.reset()

			if args.steps > 0 and step >= args.steps:
				break

	except KeyboardInterrupt:
		log('\nStopped.')
	finally:
		if log_file:
			log_file.close()

	return 0


if __name__ == '__main__':
	raise SystemExit(main())
