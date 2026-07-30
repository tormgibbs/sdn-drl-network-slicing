#!/usr/bin/env python3
# scripts/train_sac.py
#
# SAC training path, separate model lineage from train.py's PPO
# (models_sac/, not models/). SAC cannot load PPO checkpoints, so this
# starts fresh: sim-pretrain, then fine-tune the same SAC policy on
# real traffic, reusing transitions via the replay buffer instead of
# discarding each batch after one PPO update.
#
# VecNormalize stays on (norm_obs=True, norm_reward=False). SB3 stores
# unnormalized values in the replay buffer and re-normalizes at sample
# time using current stats, so it's safe to use with off-policy methods.

import argparse
import os
import time
from pathlib import Path

import numpy as np
import yaml
from gymnasium import spaces
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

SLICES_CONFIG_PATH = 'config/slices.yaml'
MODELS_ROOT = Path('models_sac')
LOG_DIR = Path('logs/tensorboard_sac')

SEED = 42


def _atomic_save(model: SAC, path: Path, vec_env: VecNormalize | None = None) -> None:
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
		save_every_n_steps: int,
		save_dir: Path,
		vec_env: VecNormalize,
		name_prefix: str = 'sac_slicing',
		verbose: int = 1,
	):
		super().__init__(verbose)
		self.save_every_n_steps = save_every_n_steps
		self.save_dir = save_dir
		self.vec_env = vec_env
		self.name_prefix = name_prefix
		self._last_save_step = 0
		self.save_dir.mkdir(parents=True, exist_ok=True)

	def _on_step(self) -> bool:
		if self.num_timesteps - self._last_save_step >= self.save_every_n_steps:
			self._save()
			self._last_save_step = self.num_timesteps
		return True

	def _save(self) -> None:
		timesteps = self.num_timesteps
		timestamped_path = self.save_dir / f'{self.name_prefix}_{timesteps}.zip'
		_atomic_save(self.model, timestamped_path, self.vec_env)
		_atomic_save(self.model, self.save_dir / 'latest.zip', self.vec_env)
		if self.verbose:
			print(
				f'[checkpoint] saved {timestamped_path.name}, updated latest.zip '
				f'(timesteps={timesteps})'
			)


def make_vec_env(
	monitor_path: Path, override_existing: bool, sim: bool = False
) -> DummyVecEnv:
	with open(SLICES_CONFIG_PATH) as f:
		slices_config = yaml.safe_load(f)

	monitor_path.parent.mkdir(parents=True, exist_ok=True)

	def make_single_env():
		if sim:
			from agent.sim_env import SimCampusEnv

			env = SimCampusEnv(slices_cfg=slices_config, episode_length=100)
		else:
			from agent.env import CampusSlicingEnv

			env = CampusSlicingEnv(
				slices_config=slices_config, ue_profiles=None, episode_length=100
			)
		return Monitor(env, filename=str(monitor_path), override_existing=override_existing)

	return DummyVecEnv([make_single_env])


def build_model(
	env: VecNormalize,
	buffer_size: int,
	learning_starts: int,
	batch_size: int,
	train_freq: int,
	gradient_steps: int,
	resume_path: Path | None,
) -> SAC:
	LOG_DIR.mkdir(parents=True, exist_ok=True)
	if resume_path is not None:
		print(f'Resuming from {resume_path}')
		return SAC.load(str(resume_path), env=env, tensorboard_log=str(LOG_DIR))
	return SAC(
		'MlpPolicy',
		env,
		buffer_size=buffer_size,
		learning_starts=learning_starts,
		batch_size=batch_size,
		train_freq=train_freq,
		gradient_steps=gradient_steps,
		seed=SEED,
		verbose=1,
		tensorboard_log=str(LOG_DIR),
	)


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'--sim',
		action='store_true',
		help='train on fast simulation instead of live network',
	)
	parser.add_argument('--total-timesteps', type=int, default=20_000)
	parser.add_argument(
		'--buffer-size',
		type=int,
		default=100_000,
		help='replay buffer capacity; unused capacity costs little, no need to '
		'shrink this to match total_timesteps',
	)
	parser.add_argument(
		'--learning-starts',
		type=int,
		default=1000,
		help='random-action warmup steps before learning begins. Leave at SB3 '
		'default unless this is a continuation of an *existing SAC* run '
		'via --resume, since a fresh policy has no prior knowledge to '
		'fall back on regardless of whether this is the sim or real phase',
	)
	parser.add_argument('--batch-size', type=int, default=256)
	parser.add_argument('--train-freq', type=int, default=1)
	parser.add_argument(
		'--gradient-steps',
		type=int,
		default=1,
		help='gradient updates per training call; raise this (e.g. 4-8) for '
		'the real-environment phase specifically, to extract more '
		'learning per expensive real step',
	)
	parser.add_argument(
		'--eval-freq',
		type=int,
		default=2000,
		help='run eval episodes every N steps; set higher for real runs '
		'since eval episodes also cost real wall-clock time',
	)
	parser.add_argument('--n-eval-episodes', type=int, default=5)
	parser.add_argument('--resume', action='store_true')
	parser.add_argument('--checkpoint-every-n-steps', type=int, default=1000)
	parser.add_argument('--run-name', type=str, default=time.strftime('%Y%m%d_%H%M%S'))
	args = parser.parse_args()

	model_dir = MODELS_ROOT / args.run_name
	model_dir.mkdir(parents=True, exist_ok=True)

	raw_vec_env = make_vec_env(
		monitor_path=model_dir / 'monitor.csv',
		override_existing=not args.resume,
		sim=args.sim,
	)

	stats_path = model_dir / 'latest.pkl'
	if args.resume and stats_path.exists():
		env = VecNormalize.load(str(stats_path), raw_vec_env)
		env.training = True
		print(f'Loaded VecNormalize stats from {stats_path}')
	else:
		if args.resume:
			print(f'Warning: no VecNormalize stats found at {stats_path} -- starting fresh')
		env = VecNormalize(raw_vec_env, norm_obs=True, norm_reward=False)

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

	model = build_model(
		env,
		buffer_size=args.buffer_size,
		learning_starts=args.learning_starts,
		batch_size=args.batch_size,
		train_freq=args.train_freq,
		gradient_steps=args.gradient_steps,
		resume_path=resume_path,
	)

	# Separate eval env, same VecNormalize stats but training=False so
	# reward/obs stats aren't perturbed by evaluation rollouts.
	eval_raw_env = make_vec_env(
		monitor_path=model_dir / 'eval_monitor.csv',
		override_existing=True,
		sim=args.sim,
	)
	eval_env = VecNormalize(
		eval_raw_env, norm_obs=True, norm_reward=False, training=False
	)
	eval_env.obs_rms = env.obs_rms

	callbacks = [
		AtomicCheckpointCallback(
			save_every_n_steps=args.checkpoint_every_n_steps,
			save_dir=model_dir,
			vec_env=env,
			verbose=1,
		),
		EvalCallback(
			eval_env,
			best_model_save_path=str(model_dir / 'best'),
			log_path=str(model_dir / 'eval_logs'),
			eval_freq=args.eval_freq,
			n_eval_episodes=args.n_eval_episodes,
			deterministic=True,
			verbose=1,
		),
	]

	print(
		f'Training (SAC): run_name={args.run_name} total_timesteps={args.total_timesteps} '
		f'sim={args.sim} resume={args.resume} buffer_size={args.buffer_size} '
		f'learning_starts={args.learning_starts} gradient_steps={args.gradient_steps} '
		f'eval_freq={args.eval_freq}'
	)
	model.learn(
		total_timesteps=args.total_timesteps,
		callback=callbacks,
		reset_num_timesteps=not args.resume,
	)

	final_path = model_dir / 'final.zip'
	_atomic_save(model, final_path, vec_env=env)
	print(f'Training complete. Final model saved to {final_path}')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
