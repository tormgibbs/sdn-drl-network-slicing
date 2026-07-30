# agent/runner.py
# Shared inference core used by both scripts/infer.py and
# infrastructure/controller/agent_manager.py. No printing, no logging
# to files, no REST/WS serving -- callers get results via on_step().

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from stable_baselines3 import PPO, SAC
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from agent.env import CampusSlicingEnv

logger = logging.getLogger(__name__)
_ALGO_CLASSES = {'ppo': PPO, 'sac': SAC}


class StepResult:
	__slots__ = ('timestamp', 'step', 'reward', 'allocation_kbps', 'done')

	def __init__(self, timestamp, step, reward, allocation_kbps, done):
		self.timestamp = timestamp
		self.step = step
		self.reward = reward
		self.allocation_kbps = allocation_kbps
		self.done = done

	def to_dict(self) -> dict:
		return {
			'timestamp': self.timestamp,
			'step': self.step,
			'reward': self.reward,
			'allocation_kbps': self.allocation_kbps,
			'done': self.done,
		}


class AgentRunner:
	def __init__(
		self,
		slices_config: dict,
		model_path: str,
		vecnorm_path: str | None = None,
		algo: str = 'ppo',
	):
		algo = algo.lower()
		if algo not in _ALGO_CLASSES:
			raise ValueError(f'Unknown algo {algo!r}, expected one of {list(_ALGO_CLASSES)}')

		if not model_path.endswith('.zip'):
			model_path = model_path + '.zip'

		self._env = CampusSlicingEnv(
			slices_config=slices_config, ue_profiles=None, episode_length=999999
		)
		vec_env = DummyVecEnv([lambda: Monitor(self._env)])

		if vecnorm_path:
			vec_env = VecNormalize.load(vecnorm_path, vec_env)
			vec_env.training = False
			vec_env.norm_reward = False

		self._vec_env = vec_env
		self._model = _ALGO_CLASSES[algo].load(model_path, env=vec_env)
		self._stop_requested = False
		self._step_count = 0

	def get_current_allocation(self) -> dict[str, int]:
		return self._env.get_current_allocation()

	def request_stop(self) -> None:
		# Cooperative only -- checked between steps, not mid-step, since a
		# step() may be blocked applying an allocation or waiting on the
		# metrics socket. Interrupting there risks a half-applied allocation.
		self._stop_requested = True

	def run(self, on_step: Callable[['StepResult'], None], max_steps: int = 0) -> None:
		self._stop_requested = False
		obs = self._vec_env.reset()

		while not self._stop_requested:
			action, _ = self._model.predict(obs, deterministic=True)
			obs, reward, done, info = self._vec_env.step(action)
			self._step_count += 1

			on_step(
				StepResult(
					timestamp=datetime.now(timezone.utc).isoformat(),
					step=self._step_count,
					reward=float(reward[0]),
					allocation_kbps=self.get_current_allocation(),
					done=bool(done[0]),
				)
			)

			if done[0]:
				obs = self._vec_env.reset()
			if max_steps > 0 and self._step_count >= max_steps:
				break

	def close(self) -> None:
		self._env.close()
