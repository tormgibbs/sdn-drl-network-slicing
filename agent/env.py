# agent/env.py


import json
import logging
import subprocess
import time

import gymnasium as gym
import httpx2 as httpx
import numpy as np
import websockets
from gymnasium import spaces
from websockets.sync.client import connect as ws_connect

from agent.project_allocation import validate_floors
from agent.slice_conversion import action_array_to_slice_dict

API_BASE_URL = 'http://localhost:8080'
WS_URL = 'ws://localhost:8080/ws/metrics'

# Default policy input for reset(): uniform fractions across all 5 slices.
EQUAL_SPLIT = [0.2, 0.2, 0.2, 0.2, 0.2]

# Reward function weights (see drl-agent-design.md Reward Function section).
W1, W2, W3, W4, W5 = 0.35, 0.25, 0.20, 0.10, 0.10

logger = logging.getLogger(__name__)


class CampusSlicingEnv(gym.Env):
	def __init__(
		self,
		slices_config: dict,
		ue_profiles: dict | None = None,
		episode_length: int = 100,
	):
		super().__init__()

		self.slice_order: list[str] = slices_config['slice_order']
		self.slices_cfg: dict = slices_config['slices']
		self.n_slices = len(self.slice_order)

		self._slice_to_ue_config: dict[str, str] = {}
		if ue_profiles is not None:
			for ue in ue_profiles['ue_profiles'].values():
				self._slice_to_ue_config[ue['slice']] = ue['config_file']

		self.floors_kbps = [
			self.slices_cfg[name]['min_throughput_bps'] // 1000 for name in self.slice_order
		]
		self.c_kbps = slices_config['network']['total_bandwidth_bps'] // 1000
		validate_floors(self.floors_kbps, self.c_kbps)

		self.max_latency_ms = {
			name: self.slices_cfg[name]['max_latency_ms'] for name in self.slice_order
		}

		self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(self.n_slices * 3,))
		self.action_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.n_slices,))

		self.episode_length = episode_length
		self._step_count = 0
		self._current_rates_kbps: dict[str, int] | None = None

		self._http = httpx.Client(base_url=API_BASE_URL)
		self._ws = None
		self._last_obs: np.ndarray | None = None

	def _softmax(self, logits: np.ndarray) -> list[float]:
		z = logits - np.max(logits)
		exp = np.exp(z)
		return (exp / exp.sum()).tolist()

	def _apply_allocation(self, p: list[float]) -> dict[str, int]:
		allocation_fractions = action_array_to_slice_dict(p, self.slice_order)
		resp = self._http.post('/allocate', json=allocation_fractions)
		resp.raise_for_status()
		return resp.json()['rates_kbps']

	def _connect_ws(self) -> None:
		if self._ws is not None:
			self._ws.close()
		self._ws = ws_connect(WS_URL)

	def _wait_for_stats(self) -> dict:
		raw = self._ws.recv()
		return json.loads(raw)

	def close(self) -> None:
		if self._ws is not None:
			self._ws.close()
			self._ws = None
		self._http.close()

	def _validate_metrics(self, metrics: dict) -> None:
		for name in self.slice_order:
			m = metrics[name]
			assert m['latency_ms'] is not None, f'latency_ms is None for slice {name!r}'
			assert m['loss_pct'] is not None, f'loss_pct is None for slice {name!r}'

	def _check_tunnel_interfaces(self) -> list[str]:
		missing = []
		for name in self.slice_order:
			iface = self.slices_cfg[name]['probe_interface']
			result = subprocess.run(
				['docker', 'exec', 'ueransim', 'ip', 'link', 'show', iface],
				capture_output=True,
				timeout=5,
			)
			if result.returncode != 0:
				missing.append(name)
		return missing

	def _recover_tunnel_interfaces(self, missing: list[str]) -> None:
		for name in missing:
			iface = self.slices_cfg[name]['probe_interface']
			config_file = self._slice_to_ue_config.get(name)
			assert config_file is not None, (
				f'no UE config file mapped for slice {name!r} -- '
				'ue_profiles was not provided or is missing this slice'
			)

			logger.warning(
				'Tunnel interface missing for slice %s (%s) -- '
				're-triggering UERANSIM registration',
				name,
				iface,
			)

			subprocess.run(
				[
					'docker',
					'exec',
					'-d',
					'ueransim',
					'/ueransim/nr-ue',
					'-c',
					f'/ueransim/config/{config_file}',
				],
				capture_output=True,
				timeout=10,
			)

		for name in missing:
			iface = self.slices_cfg[name]['probe_interface']
			for _ in range(30):
				result = subprocess.run(
					['docker', 'exec', 'ueransim', 'ip', 'link', 'show', iface],
					capture_output=True,
					timeout=5,
				)
				if result.returncode == 0:
					break
				time.sleep(1)
			else:
				raise RuntimeError(
					f'tunnel interface {iface} for slice {name!r} did not appear after 30s'
				)

	def _build_observation(self, metrics: dict) -> np.ndarray:
		assert self._current_rates_kbps is not None, (
			'_current_rates_kbps not set -- _build_observation() called before '
			'reset()/step() applied an allocation'
		)
		obs = []
		for name in self.slice_order:
			m = metrics[name]

			latency_i = min(m['latency_ms'] / self.max_latency_ms[name], 1.0)
			loss_i = m['loss_pct'] / 100.0
			a_i_bps = self._current_rates_kbps[name] * 1000
			utilisation_i = min(m['tx_throughput_bps'] / a_i_bps, 1.0)

			obs.extend([latency_i, loss_i, utilisation_i])

		return np.array(obs, dtype=np.float32)

	def _compute_reward(self, metrics: dict) -> float:
		assert self._current_rates_kbps is not None, (
			'_current_rates_kbps not set -- _compute_reward() called before '
			'reset()/step() applied an allocation'
		)
		assert all(r > 0 for r in self._current_rates_kbps.values()), (
			f'all current rates must be positive (floor guarantee from '
			f'project_allocation()) -- got {self._current_rates_kbps}'
		)

		n = self.n_slices
		r_sla = 0.0
		p_latency = 0.0
		p_loss = 0.0
		r_util_sum = 0.0
		fairness_ratios = []

		for name in self.slice_order:
			m = metrics[name]
			cfg = self.slices_cfg[name]
			si = cfg['priority']
			Li = cfg['max_latency_ms']
			Loss_i = cfg['max_loss_pct']

			latency_i = m['latency_ms']
			loss_i = m['loss_pct']

			sla_met = latency_i <= Li and loss_i <= Loss_i
			r_sla += si * (1.0 if sla_met else 0.0)
			p_latency += si * max(0.0, (latency_i - Li) / Li)
			p_loss += si * loss_i

			a_i_bps = self._current_rates_kbps[name] * 1000
			r_util_sum += min(m['tx_throughput_bps'] / a_i_bps, 1.0)

			fairness_ratios.append(self._current_rates_kbps[name] / si)

		r_util = r_util_sum / n

		sum_ratios = sum(fairness_ratios)
		sum_sq_ratios = sum(r**2 for r in fairness_ratios)
		p_fairness = 1.0 - (sum_ratios**2) / (n * sum_sq_ratios)

		return W1 * r_sla - W2 * p_latency - W3 * p_loss + W4 * r_util - W5 * p_fairness

	def reset(self, *, seed=None, options=None):
		super().reset(seed=seed)
		self._step_count = 0

		try:
			missing = self._check_tunnel_interfaces()
			if missing:
				self._recover_tunnel_interfaces(missing)

			self._current_rates_kbps = self._apply_allocation(EQUAL_SPLIT)
			self._connect_ws()
			metrics = self._wait_for_stats()
			self._validate_metrics(metrics)
		except (
			httpx.HTTPError,
			OSError,
			websockets.WebSocketException,
			AssertionError,
			subprocess.SubprocessError,
		) as exc:
			raise RuntimeError(f'reset() failed to start episode: {exc}') from exc

		obs = self._build_observation(metrics)
		self._last_obs = obs
		return obs, {}

	def step(self, action: np.ndarray):
		p = self._softmax(action)

		try:
			self._current_rates_kbps = self._apply_allocation(p)
			metrics = self._wait_for_stats()
			self._validate_metrics(metrics)
		except (
			httpx.HTTPError,
			OSError,
			websockets.WebSocketException,
			AssertionError,
		) as exc:
			assert self._last_obs is not None, (
				'infra failure on the very first step() call, before any '
				'successful observation -- no fallback obs available'
			)
			self._step_count += 1
			return self._last_obs, 0.0, False, True, {'failure': str(exc)}

		obs = self._build_observation(metrics)
		reward = self._compute_reward(metrics)
		self._last_obs = obs

		self._step_count += 1
		terminated = self._step_count >= self.episode_length
		truncated = False

		return obs, reward, terminated, truncated, {}
