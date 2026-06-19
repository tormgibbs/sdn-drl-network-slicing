# tests/agent/test_env.py

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from agent.env import EQUAL_SPLIT, CampusSlicingEnv

SLICES_CONFIG = {
	'slice_order': ['vle', 'student_portal', 'admin', 'iot', 'general'],
	'network': {'total_bandwidth_bps': 100_000_000},
	'slices': {
		'vle': {
			'min_throughput_bps': 50_000_000,
			'max_latency_ms': 100,
			'max_loss_pct': 0.5,
			'priority': 5,
		},
		'student_portal': {
			'min_throughput_bps': 25_000_000,
			'max_latency_ms': 50,
			'max_loss_pct': 0.1,
			'priority': 4,
		},
		'admin': {
			'min_throughput_bps': 10_000_000,
			'max_latency_ms': 150,
			'max_loss_pct': 1.0,
			'priority': 3,
		},
		'iot': {
			'min_throughput_bps': 64_000,
			'max_latency_ms': 200,
			'max_loss_pct': 5.0,
			'priority': 2,
		},
		'general': {
			'min_throughput_bps': 5_000_000,
			'max_latency_ms': 500,
			'max_loss_pct': 10.0,
			'priority': 1,
		},
	},
}


def _good_metrics() -> dict[str, dict[str, float | None]]:
	return {
		'vle': {'latency_ms': 40.0, 'loss_pct': 0.1, 'tx_throughput_bps': 48_000_000.0},
		'student_portal': {
			'latency_ms': 20.0,
			'loss_pct': 0.05,
			'tx_throughput_bps': 24_000_000.0,
		},
		'admin': {'latency_ms': 60.0, 'loss_pct': 0.5, 'tx_throughput_bps': 9_000_000.0},
		'iot': {'latency_ms': 80.0, 'loss_pct': 1.0, 'tx_throughput_bps': 60_000.0},
		'general': {'latency_ms': 200.0, 'loss_pct': 2.0, 'tx_throughput_bps': 4_000_000.0},
	}


@pytest.fixture
def env():
	e = CampusSlicingEnv(SLICES_CONFIG)
	e._current_rates_kbps = dict(
		zip(SLICES_CONFIG['slice_order'], [51988, 26987, 11987, 2051, 6987])
	)
	yield e
	e.close()


class TestInit:
	def test_observation_space_shape(self, env):
		assert env.observation_space.shape == (15,)

	def test_action_space_shape(self, env):
		assert env.action_space.shape == (5,)

	def test_floors_match_config(self, env):
		assert env.floors_kbps == [50000, 25000, 10000, 64, 5000]

	def test_capacity_matches_config(self, env):
		assert env.c_kbps == 100000


class TestSoftmax:
	def test_sums_to_one(self, env):
		p = env._softmax(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
		assert abs(sum(p) - 1.0) < 1e-6

	def test_all_positive(self, env):
		p = env._softmax(np.array([-5.0, 0.0, 5.0, -2.0, 2.0]))
		assert all(pi > 0 for pi in p)

	def test_equal_logits_give_equal_probability(self, env):
		p = env._softmax(np.array([0.0, 0.0, 0.0, 0.0, 0.0]))
		assert all(abs(pi - 0.2) < 1e-6 for pi in p)


class TestApplyAllocation:
	def test_posts_dict_keyed_by_slice_name(self, env):
		mock_resp = MagicMock()
		mock_resp.json.return_value = {'rates_kbps': {'vle': 1000}}
		env._http = MagicMock()
		env._http.post.return_value = mock_resp

		env._apply_allocation([0.5, 0.2, 0.15, 0.05, 0.1])

		called_payload = env._http.post.call_args.kwargs['json']
		assert called_payload == {
			'vle': 0.5,
			'student_portal': 0.2,
			'admin': 0.15,
			'iot': 0.05,
			'general': 0.1,
		}

	def test_returns_rates_kbps_from_response(self, env):
		mock_resp = MagicMock()
		mock_resp.json.return_value = {'rates_kbps': {'vle': 51988, 'iot': 2051}}
		env._http = MagicMock()
		env._http.post.return_value = mock_resp

		result = env._apply_allocation([0.5, 0.2, 0.15, 0.05, 0.1])
		assert result == {'vle': 51988, 'iot': 2051}

	def test_raises_on_http_error(self, env):
		mock_resp = MagicMock()
		mock_resp.raise_for_status.side_effect = RuntimeError('422')
		env._http = MagicMock()
		env._http.post.return_value = mock_resp

		with pytest.raises(RuntimeError):
			env._apply_allocation([0.2] * 5)


class TestValidateMetrics:
	def test_passes_on_complete_metrics(self, env):
		env._validate_metrics(_good_metrics())

	def test_raises_on_missing_latency(self, env):
		metrics = _good_metrics()
		metrics['vle']['latency_ms'] = None
		with pytest.raises(AssertionError, match='latency_ms'):
			env._validate_metrics(metrics)

	def test_raises_on_missing_loss(self, env):
		metrics = _good_metrics()
		metrics['iot']['loss_pct'] = None
		with pytest.raises(AssertionError, match='loss_pct'):
			env._validate_metrics(metrics)


class TestBuildObservation:
	def test_shape_and_bounds(self, env):
		obs = env._build_observation(_good_metrics())
		assert obs.shape == (15,)
		assert obs.min() >= 0.0
		assert obs.max() <= 1.0

	def test_known_values_for_vle(self, env):
		obs = env._build_observation(_good_metrics())
		# vle is slice_order[0] -> obs[0:3] = [latency_i, loss_i, utilisation_i]
		latency_i, loss_i, utilisation_i = obs[0], obs[1], obs[2]
		assert abs(latency_i - (40.0 / 100)) < 1e-5
		assert abs(loss_i - (0.1 / 100)) < 1e-5
		assert abs(utilisation_i - (48_000_000.0 / (51988 * 1000))) < 1e-5

	def test_latency_clamped_at_one(self, env):
		metrics = _good_metrics()
		metrics['vle']['latency_ms'] = 500.0  # 5x its max_latency_ms of 100
		obs = env._build_observation(metrics)
		assert obs[0] == 1.0

	def test_utilisation_clamped_at_one(self, env):
		metrics = _good_metrics()
		metrics['vle']['tx_throughput_bps'] = 999_000_000.0  # far above its ceiling
		obs = env._build_observation(metrics)
		assert obs[2] == 1.0

	def test_raises_if_rates_not_set(self, env):
		env._current_rates_kbps = None
		with pytest.raises(AssertionError, match='_current_rates_kbps'):
			env._build_observation(_good_metrics())


class TestComputeReward:
	def test_returns_float(self, env):
		reward = env._compute_reward(_good_metrics())
		assert isinstance(reward, float)

	def test_all_slices_meeting_sla_gives_positive_r_sla_component(self, env):
		metrics = _good_metrics()
		reward_met = env._compute_reward(metrics)

		metrics['vle']['latency_ms'] = 500.0  # blows VLE's SLA
		reward_violated = env._compute_reward(metrics)

		assert reward_met > reward_violated

	def test_raises_if_rates_not_set(self, env):
		env._current_rates_kbps = None
		with pytest.raises(AssertionError, match='_current_rates_kbps'):
			env._compute_reward(_good_metrics())

	def test_raises_if_rates_not_positive(self, env):
		env._current_rates_kbps = dict.fromkeys(SLICES_CONFIG['slice_order'], 0)
		with pytest.raises(AssertionError, match='floor guarantee'):
			env._compute_reward(_good_metrics())


class TestConnectWs:
	def test_connects_to_expected_url(self, env):
		with patch('agent.env.ws_connect') as mock_connect:
			env._connect_ws()
			mock_connect.assert_called_once_with('ws://localhost:8080/ws/metrics')

	def test_closes_existing_connection_before_reconnecting(self, env):
		old_ws = MagicMock()
		env._ws = old_ws
		with patch('agent.env.ws_connect') as mock_connect:
			mock_connect.return_value = MagicMock()
			env._connect_ws()
			old_ws.close.assert_called_once()


class TestWaitForStats:
	def test_parses_json_from_recv(self, env):
		env._ws = MagicMock()
		env._ws.recv.return_value = '{"vle": {"latency_ms": 40.0}}'
		result = env._wait_for_stats()
		assert result == {'vle': {'latency_ms': 40.0}}


class TestClose:
	def test_closes_ws_and_http(self, env):
		env._ws = MagicMock()
		env._http = MagicMock()
		env.close()
		assert env._ws is None

	def test_no_error_when_ws_already_none(self, env):
		env._ws = None
		env._http = MagicMock()
		env.close()


class TestReset:
	def test_calls_apply_allocation_with_equal_split(self, env):
		with (
			patch.object(env, '_apply_allocation') as mock_apply,
			patch.object(env, '_connect_ws'),
			patch.object(env, '_wait_for_stats', return_value=_good_metrics()),
		):
			mock_apply.return_value = {
				'vle': 20000,
				'student_portal': 20000,
				'admin': 20000,
				'iot': 20000,
				'general': 20000,
			}
			env.reset()
			mock_apply.assert_called_once_with(EQUAL_SPLIT)

	def test_returns_observation_and_empty_info(self, env):
		with (
			patch.object(
				env,
				'_apply_allocation',
				return_value={
					'vle': 20000,
					'student_portal': 20000,
					'admin': 20000,
					'iot': 20000,
					'general': 20000,
				},
			),
			patch.object(env, '_connect_ws'),
			patch.object(env, '_wait_for_stats', return_value=_good_metrics()),
		):
			obs, info = env.reset()
			assert obs.shape == (15,)
			assert info == {}

	def test_resets_step_count(self, env):
		env._step_count = 42
		with (
			patch.object(
				env,
				'_apply_allocation',
				return_value={
					'vle': 20000,
					'student_portal': 20000,
					'admin': 20000,
					'iot': 20000,
					'general': 20000,
				},
			),
			patch.object(env, '_connect_ws'),
			patch.object(env, '_wait_for_stats', return_value=_good_metrics()),
		):
			env.reset()
			assert env._step_count == 0


class TestStep:
	def test_terminates_after_episode_length(self, env):
		env.episode_length = 1
		env._step_count = 0
		with (
			patch.object(
				env,
				'_apply_allocation',
				return_value={
					'vle': 20000,
					'student_portal': 20000,
					'admin': 20000,
					'iot': 20000,
					'general': 20000,
				},
			),
			patch.object(env, '_wait_for_stats', return_value=_good_metrics()),
		):
			obs, reward, terminated, truncated, info = env.step(np.zeros(5))
			assert terminated is True
			assert truncated is False

	def test_returns_five_tuple_with_correct_shapes(self, env):
		with (
			patch.object(
				env,
				'_apply_allocation',
				return_value={
					'vle': 20000,
					'student_portal': 20000,
					'admin': 20000,
					'iot': 20000,
					'general': 20000,
				},
			),
			patch.object(env, '_wait_for_stats', return_value=_good_metrics()),
		):
			obs, reward, terminated, truncated, info = env.step(np.zeros(5))
			assert obs.shape == (15,)
			assert isinstance(reward, float)
