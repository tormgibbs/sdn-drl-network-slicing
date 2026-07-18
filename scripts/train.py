#!/usr/bin/env python3
# scripts/train.py

import argparse
import os
import time
from pathlib import Path

import numpy as np
import yaml
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from agent.env import CampusSlicingEnv

SLICES_CONFIG_PATH = 'config/slices.yaml'
MODELS_ROOT = Path('models')
LOG_DIR = Path('logs/tensorboard')

SEED = 42


def _atomic_save(model: PPO, path: Path, vec_env: VecNormalize | None = None) -> None:
	tmp_path = path.with_suffix('.tmp.zip')
	model.save(str(tmp_path))
	os.replace(tmp_path, path)
	if vec_env is not None:
		stats_path = path.with_suffix('.pkl')
		tmp_stats = stats_path.with_suffix('.tmp.pkl')
		vec_env.save(str(tmp_stats))
		os.replace(tmp_stats, stats_path)


class AtomicCheckpointCallback(BaseCallback):
	def __init__(
		self,
		save_every_n_rollouts: int,
		save_dir: Path,
		vec_env: VecNormalize,
		name_prefix: str = 'ppo_slicing',
		verbose: int = 1,
	):
		super().__init__(verbose)
		self.save_every_n_rollouts = save_every_n_rollouts
		self.save_dir = save_dir
		self.vec_env = vec_env
		self.name_prefix = name_prefix
		self._rollout_count = 0
		self.save_dir.mkdir(parents=True, exist_ok=True)

	def _on_step(self) -> bool:
		return True

	def _on_rollout_start(self) -> None:
		self._rollout_count += 1
		if (
			self._rollout_count > 1
			and (self._rollout_count - 1) % self.save_every_n_rollouts == 0
		):
			self._save()

	def _save(self) -> None:
		timesteps = self.num_timesteps
		timestamped_path = self.save_dir / f'{self.name_prefix}_{timesteps}.zip'
		_atomic_save(self.model, timestamped_path, self.vec_env)
		_atomic_save(self.model, self.save_dir / 'latest.zip', self.vec_env)
		if self.verbose:
			print(
				f'[checkpoint] saved {timestamped_path.name}, updated latest.zip '
				f'(timesteps={timesteps}, post-update)'
			)


class TimingCallback(BaseCallback):
	def __init__(self, verbose: int = 1):
		super().__init__(verbose)
		self._rollout_end_time = None
		self._logged_first_actions = False

	def _on_step(self) -> bool:
		if not self._logged_first_actions and self.verbose:
			actions = self.locals.get('actions')
			if actions is not None:
				print(
					f'[action-check] sample actions (pre-clip from policy): '
					f'min={actions.min():.3f} max={actions.max():.3f}'
				)
				self._logged_first_actions = True
		return True

	def _on_rollout_start(self) -> None:
		if self._rollout_end_time is not None:
			update_dt = time.monotonic() - self._rollout_end_time
			if self.verbose:
				print(f'[timing] policy update took {update_dt:.2f}s')

	def _on_rollout_end(self) -> None:
		self._rollout_end_time = time.monotonic()


def build_model(env: VecNormalize, n_steps: int, resume_path: Path | None) -> PPO:
	LOG_DIR.mkdir(parents=True, exist_ok=True)
	if resume_path is not None:
		print(f'Resuming from {resume_path}')
		model = PPO.load(str(resume_path), env=env, tensorboard_log=str(LOG_DIR))
		if model.n_steps != n_steps:
			raise ValueError(
				f'--n-steps={n_steps} does not match resumed model.n_steps={model.n_steps} -- '
				f'checkpoint cadence would misalign with actual rollout boundaries. '
				f'Pass --n-steps {model.n_steps} to match, or omit --n-steps to use the default.'
			)
		return model
	return PPO(
		'MlpPolicy',
		env,
		n_steps=n_steps,
		n_epochs=20,
		batch_size=200,
		seed=SEED,
		verbose=1,
		tensorboard_log=str(LOG_DIR),
	)


def make_vec_env(monitor_path: Path, override_existing: bool) -> DummyVecEnv:
	with open(SLICES_CONFIG_PATH) as f:
		slices_config = yaml.safe_load(f)
	env = CampusSlicingEnv(
		slices_config=slices_config, ue_profiles=None, episode_length=100
	)
	monitor_path.parent.mkdir(parents=True, exist_ok=True)
	monitored = Monitor(
		env, filename=str(monitor_path), override_existing=override_existing
	)
	return DummyVecEnv([lambda: monitored])


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument('--total-timesteps', type=int, default=20_000)
	parser.add_argument('--n-steps', type=int, default=2048)
	parser.add_argument('--instrument', action='store_true')
	parser.add_argument('--resume', action='store_true')
	parser.add_argument('--checkpoint-every-n-rollouts', type=int, default=1)
	parser.add_argument(
		'--run-name',
		type=str,
		default=time.strftime('%Y%m%d_%H%M%S'),
	)
	args = parser.parse_args()
	model_dir = MODELS_ROOT / args.run_name
	model_dir.mkdir(parents=True, exist_ok=True)

	raw_vec_env = make_vec_env(
		monitor_path=model_dir / 'monitor.csv',
		override_existing=not args.resume,
	)

	stats_path = model_dir / 'latest.pkl'
	if args.resume and stats_path.exists():
		env = VecNormalize.load(str(stats_path), raw_vec_env)
		env.training = True
		env.norm_reward = True
		print(f'Loaded VecNormalize stats from {stats_path}')
	else:
		if args.resume:
			print(
				f'Warning: no VecNormalize stats found at {stats_path} -- starting fresh normaliser'
			)
		# norm_obs=False: observation is already normalised [0,1] in env.py.
		env = VecNormalize(raw_vec_env, norm_obs=False, norm_reward=True, clip_reward=10.0)

	env.reset()

	raw_env = env.unwrapped
	for space, name in (
		(raw_env.action_space, 'action'),
		(raw_env.observation_space, 'observation'),
	):
		assert isinstance(space, spaces.Box), f'{name}_space must be a Box'
		assert np.all(np.isfinite(space.low)) and np.all(np.isfinite(space.high)), (
			f'{name}_space must have finite bounds'
		)
	print(
		'[space-check] action_space and observation_space have finite, well-formed bounds.'
	)

	resume_path = model_dir / 'latest.zip' if args.resume else None
	if args.resume and not resume_path.exists():
		raise FileNotFoundError(f'--resume given but {resume_path} does not exist')

	model = build_model(env, n_steps=args.n_steps, resume_path=resume_path)

	total_timesteps = args.n_steps * 2 if args.instrument else args.total_timesteps

	callbacks = [
		TimingCallback(verbose=1),
		AtomicCheckpointCallback(
			save_every_n_rollouts=args.checkpoint_every_n_rollouts,
			save_dir=model_dir,
			vec_env=env,
			verbose=1,
		),
	]

	print(
		f'Training: run_name={args.run_name} total_timesteps={total_timesteps} '
		f'n_steps={args.n_steps} instrument={args.instrument} resume={args.resume}'
	)
	model.learn(
		total_timesteps=total_timesteps,
		callback=callbacks,
		reset_num_timesteps=not args.resume,
	)

	final_path = model_dir / 'final.zip'
	_atomic_save(model, final_path, vec_env=env)
	print(f'Training complete. Final model saved to {final_path}')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
