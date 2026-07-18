# agent/sim_env.py
from __future__ import annotations

import random

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from agent.project_allocation import project_allocation, validate_floors

W1, W2, W3, W4, W5 = 0.35, 0.20, 0.25, 0.10, 0.10

_SCENARIOS = {
	'lecture': {
		'vle': {'ul': (0.80, 1.00), 'dl': (0.80, 1.00)},
		'student_portal': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'admin': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'iot': {'ul': (0.80, 1.00), 'dl': (0.80, 1.00)},
		'general': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
	},
	'registration': {
		'vle': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'student_portal': {'ul': (0.80, 1.00), 'dl': (0.80, 1.00)},
		'admin': {'ul': (0.80, 1.00), 'dl': (0.80, 1.00)},
		'iot': {'ul': (0.80, 1.00), 'dl': (0.80, 1.00)},
		'general': {'ul': (0.80, 1.00), 'dl': (0.80, 1.00)},
	},
	'off_peak': {
		'vle': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'student_portal': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'admin': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'iot': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
		'general': {'ul': (0.60, 0.70), 'dl': (0.60, 0.70)},
	},
}

_TRAFFIC_PROFILES = {
	'vle': {
		'continuous_bps': 15_000_000,
		'on_off_bps': 18_000_000,
		'pattern': 'mixed',
		'mean_on': 25,
		'mean_off': 15,
	},
	'student_portal': {
		'continuous_bps': 5_000_000,
		'on_off_bps': 20_000_000,
		'pattern': 'mixed',
		'mean_on': 10,
		'mean_off': 10,
	},
	'admin': {'target_bps': 10_000_000, 'pattern': 'continuous'},
	'iot': {'target_bps': 64_000, 'pattern': 'continuous'},
	'general': {'target_bps': 5_000_000, 'pattern': 'continuous'},
}


class SimCampusEnv(gym.Env):
	"""Fast simulation of CampusSlicingEnv for rapid policy training.
	Mirrors observation space, action space, and reward function exactly.
	No network calls; demand and loss computed analytically.
	"""

	metadata = {'render_modes': []}

	def __init__(self, slices_cfg: dict, episode_length: int = 100) -> None:
		super().__init__()

		self.slice_order: list[str] = slices_cfg['slice_order']
		self.slices_cfg: dict = slices_cfg['slices']
		self.episode_length = episode_length
		self._n = len(self.slice_order)
		self._C_kbps = slices_cfg['network']['total_bandwidth_bps'] // 1000

		self._floors_kbps: list[int] = [
			max(1, self.slices_cfg[n]['min_throughput_bps'] // 1000) for n in self.slice_order
		]
		validate_floors(self._floors_kbps, self._C_kbps)

		self.max_latency_ms = {
			n: self.slices_cfg[n]['max_latency_ms'] for n in self.slice_order
		}
		self.max_loss_pct = {
			n: self.slices_cfg[n]['max_loss_pct'] for n in self.slice_order
		}

		self.action_space = spaces.Box(
			low=-10.0, high=10.0, shape=(self._n,), dtype=np.float32
		)
		self.observation_space = spaces.Box(
			low=0.0, high=1.0, shape=(self._n * 3,), dtype=np.float32
		)

		self._current_rates_kbps: dict[str, int] = {}
		self._step_count = 0
		self._on_off_state: dict[str, bool] = {}
		self._on_off_timer: dict[str, float] = {}
		self._scenario: str = 'lecture'
		self._factors: dict[str, float] = {}
		self._base_latency_ms: dict[str, float] = {}

	def _sample_scenario(self) -> None:
		self._scenario = random.choice(list(_SCENARIOS.keys()))
		scenario = _SCENARIOS[self._scenario]
		for name in self.slice_order:
			lo, hi = scenario[name]['ul']
			self._factors[name] = random.uniform(lo, hi)

		for name in self.slice_order:
			profile = _TRAFFIC_PROFILES[name]
			if profile['pattern'] == 'mixed':
				self._on_off_state[name] = False
				self._on_off_timer[name] = random.expovariate(1.0 / profile['mean_off'])
			# Baseline one-way latency — emulates GTP tunnel + OVS pipeline overhead
			self._base_latency_ms[name] = random.uniform(5.0, 20.0)

	def _offered_bps(self, name: str) -> float:
		profile = _TRAFFIC_PROFILES[name]
		factor = self._factors[name]

		if profile['pattern'] == 'continuous':
			return profile['target_bps'] * factor

		continuous = profile['continuous_bps'] * factor
		if self._on_off_state[name]:
			burst = profile['on_off_bps'] * factor
		else:
			burst = 0.0

		self._on_off_timer[name] -= 1.0
		if self._on_off_timer[name] <= 0:
			self._on_off_state[name] = not self._on_off_state[name]
			if self._on_off_state[name]:
				self._on_off_timer[name] = random.expovariate(
					1.0 / _TRAFFIC_PROFILES[name]['mean_on']
				)
			else:
				self._on_off_timer[name] = random.expovariate(
					1.0 / _TRAFFIC_PROFILES[name]['mean_off']
				)

		return continuous + burst

	def _compute_metrics(self) -> dict[str, dict]:
		metrics = {}
		for name in self.slice_order:
			ceiling_bps = self._current_rates_kbps[name] * 1000
			offered = self._offered_bps(name)

			if ceiling_bps <= 0 or offered <= 0:
				loss_pct = 0.0
				utilisation = 0.0
			elif offered > ceiling_bps:
				loss_pct = min(100.0 * (offered - ceiling_bps) / offered, 100.0)
				utilisation = 1.0
			else:
				loss_pct = 0.0
				utilisation = offered / ceiling_bps

			# Latency rises slightly under high utilisation — emulates kernel forwarding pressure
			latency_ms = self._base_latency_ms[name] * (1.0 + 0.5 * utilisation)
			latency_ms += random.gauss(0, 2.0)
			latency_ms = max(1.0, latency_ms)

			metrics[name] = {
				'latency_ms': latency_ms,
				'loss_pct': loss_pct,
				'tx_throughput_bps': min(offered, ceiling_bps),
			}
		return metrics

	def _build_observation(self, metrics: dict) -> np.ndarray:
		obs = []
		for name in self.slice_order:
			m = metrics[name]
			latency_i = min(m['latency_ms'] / self.max_latency_ms[name], 1.0)
			loss_i = m['loss_pct'] / 100.0
			ceiling_bps = self._current_rates_kbps[name] * 1000
			utilisation_i = (
				min(m['tx_throughput_bps'] / ceiling_bps, 1.0) if ceiling_bps > 0 else 0.0
			)
			obs.extend([latency_i, loss_i, utilisation_i])
		return np.array(obs, dtype=np.float32)

	def _compute_reward(self, metrics: dict) -> float:
		n_active = self._n
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
			loss_i = m['loss_pct']

			latency_ms_ok = m['latency_ms'] <= Li
			p_latency += si * max(0.0, (m['latency_ms'] - Li) / Li)

			sla_met = latency_ms_ok and loss_i <= Loss_i
			r_sla += si * (1.0 if sla_met else 0.0)
			p_loss += si * (loss_i / 100.0)

			ceiling_bps = self._current_rates_kbps[name] * 1000
			util = min(m['tx_throughput_bps'] / ceiling_bps, 1.0) if ceiling_bps > 0 else 0.0
			r_util_sum += util
			fairness_ratios.append(self._current_rates_kbps[name] / si)

		r_util = r_util_sum / n_active
		sum_ratios = sum(fairness_ratios)
		sum_sq = sum(r**2 for r in fairness_ratios)
		p_fairness = 1.0 - (sum_ratios**2) / (n_active * sum_sq) if sum_sq > 0 else 0.0

		return W1 * r_sla - W2 * p_latency - W3 * p_loss + W4 * r_util - W5 * p_fairness

	def reset(self, *, seed=None, options=None):
		super().reset(seed=seed)
		self._step_count = 0
		self._sample_scenario()

		equal_frac = [1.0 / self._n] * self._n
		self._current_rates_kbps = dict(
			zip(
				self.slice_order,
				project_allocation(equal_frac, self._floors_kbps, self._C_kbps),
			)
		)

		metrics = self._compute_metrics()
		return self._build_observation(metrics), {}

	def step(self, action: np.ndarray):
		raw = action.tolist()
		exp_raw = [float(np.exp(x)) for x in raw]
		total = sum(exp_raw)
		fracs = [e / total for e in exp_raw]

		rates = project_allocation(fracs, self._floors_kbps, self._C_kbps)
		self._current_rates_kbps = dict(zip(self.slice_order, rates))

		metrics = self._compute_metrics()
		obs = self._build_observation(metrics)
		reward = self._compute_reward(metrics)

		self._step_count += 1
		terminated = self._step_count >= self.episode_length

		return obs, reward, terminated, False, {}
