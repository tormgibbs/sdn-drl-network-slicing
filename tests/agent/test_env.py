# tests/agent/test_env.py

import subprocess
from unittest.mock import MagicMock, patch

import httpx2 as httpx
import numpy as np
import pytest
import websockets

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
			'probe_interface': 'ue1tun0',
		},
		'student_portal': {
			'min_throughput_bps': 25_000_000,
			'max_latency_ms': 50,
			'max_loss_pct': 0.1,
			'priority': 4,
			'probe_interface': 'ue2tun0',
		},
		'admin': {
			'min_throughput_bps': 10_000_000,
			'max_latency_ms': 150,
			'max_loss_pct': 1.0,
			'priority': 3,
			'probe_interface': 'ue3tun0',
		},
		'iot': {
			'min_throughput_bps': 64_000,
			'max_latency_ms': 200,
			'max_loss_pct': 5.0,
			'priority': 2,
			'probe_interface': 'ue4tun0',
		},
		'general': {
			'min_throughput_bps': 5_000_000,
			'max_latency_ms': 500,
			'max_loss_pct': 10.0,
			'priority': 1,
			'probe_interface': 'ue5tun0',
		},
	},
}

UE_PROFILES = {
	'ue_profiles': {
		'ue1': {'slice': 'vle', 'config_file': 'uecfg-ue1.yaml'},
		'ue2': {'slice': 'student_portal', 'config_file': 'uecfg-ue2.yaml'},
		'ue3': {'slice': 'admin', 'config_file': 'uecfg-ue3.yaml'},
		'ue4': {'slice': 'iot', 'config_file': 'uecfg-ue4.yaml'},
		'ue5': {'slice': 'general', 'config_file': 'uecfg-ue5.yaml'},
	},
}


@pytest.fixture
def env_with_ue_profiles():
	e = CampusSlicingEnv(SLICES_CONFIG, ue_profiles=UE_PROFILES)
	e._current_rates_kbps = dict(
		zip(SLICES_CONFIG['slice_order'], [51988, 26987, 11987, 2051, 6987])
	)
	yield e
	e.close()


@pytest.fixture
def env():
	e = CampusSlicingEnv(SLICES_CONFIG)
	e._current_rates_kbps = dict(
		zip(SLICES_CONFIG['slice_order'], [51988, 26987, 11987, 2051, 6987])
	)
	yield e
	e.close()


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
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
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
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
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
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
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


class TestResetFailureHandling:
	def test_apply_allocation_failure_raises_runtime_error(self, env):
		with (
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
			patch.object(env, '_apply_allocation', side_effect=httpx.HTTPError('boom')),
		):
			with pytest.raises(RuntimeError, match='reset\\(\\) failed to start episode'):
				env.reset()

	def test_connect_ws_failure_raises_runtime_error(self, env):
		with (
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
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
			patch.object(env, '_connect_ws', side_effect=OSError('connection refused')),
		):
			with pytest.raises(RuntimeError, match='reset\\(\\) failed to start episode'):
				env.reset()

	def test_wait_for_stats_failure_raises_runtime_error(self, env):
		with (
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
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
			patch.object(
				env, '_wait_for_stats', side_effect=websockets.ConnectionClosed(None, None)
			),
		):
			with pytest.raises(RuntimeError, match='reset\\(\\) failed to start episode'):
				env.reset()

	def test_validate_metrics_failure_raises_runtime_error(self, env):
		bad_metrics = _good_metrics()
		bad_metrics['vle']['latency_ms'] = None
		with (
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
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
			patch.object(env, '_wait_for_stats', return_value=bad_metrics),
		):
			with pytest.raises(RuntimeError, match='reset\\(\\) failed to start episode'):
				env.reset()

	def test_original_exception_preserved_as_cause(self, env):
		original = httpx.HTTPError('boom')
		with (
			patch.object(env, '_check_tunnel_interfaces', return_value=[]),
			patch.object(env, '_apply_allocation', side_effect=original),
		):
			with pytest.raises(RuntimeError) as exc_info:
				env.reset()
			assert exc_info.value.__cause__ is original


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


class TestStepFailureHandling:
	def test_http_error_returns_truncated(self, env):
		env._last_obs = np.zeros(15, dtype=np.float32)
		with patch.object(env, '_apply_allocation', side_effect=httpx.HTTPError('boom')):
			obs, reward, terminated, truncated, info = env.step(np.zeros(5))
			assert truncated is True
			assert terminated is False
			assert reward == 0.0
			assert 'failure' in info

	def test_http_error_returns_last_obs(self, env):
		fallback = np.full(15, 0.42, dtype=np.float32)
		env._last_obs = fallback
		with patch.object(env, '_apply_allocation', side_effect=httpx.HTTPError('boom')):
			obs, *_ = env.step(np.zeros(5))
			assert np.array_equal(obs, fallback)

	def test_websocket_exception_returns_truncated(self, env):
		env._last_obs = np.zeros(15, dtype=np.float32)
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
			patch.object(
				env, '_wait_for_stats', side_effect=websockets.ConnectionClosed(None, None)
			),
		):
			obs, reward, terminated, truncated, info = env.step(np.zeros(5))
			assert truncated is True
			assert reward == 0.0

	def test_validate_metrics_failure_returns_truncated(self, env):
		env._last_obs = np.zeros(15, dtype=np.float32)
		bad_metrics = _good_metrics()
		bad_metrics['vle']['latency_ms'] = None
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
			patch.object(env, '_wait_for_stats', return_value=bad_metrics),
		):
			obs, reward, terminated, truncated, info = env.step(np.zeros(5))
			assert truncated is True

	def test_step_count_increments_on_failure(self, env):
		env._last_obs = np.zeros(15, dtype=np.float32)
		env._step_count = 5
		with patch.object(env, '_apply_allocation', side_effect=httpx.HTTPError('boom')):
			env.step(np.zeros(5))
			assert env._step_count == 6

	def test_raises_if_no_fallback_obs_available(self, env):
		env._last_obs = None
		with patch.object(env, '_apply_allocation', side_effect=httpx.HTTPError('boom')):
			with pytest.raises(AssertionError, match='no fallback obs available'):
				env.step(np.zeros(5))


class TestTunnelRecovery:
	def test_no_missing_interfaces_skips_recovery(self, env_with_ue_profiles):
		all_ok = MagicMock(returncode=0)
		with patch('agent.env.subprocess.run', return_value=all_ok) as mock_run:
			result = env_with_ue_profiles._check_tunnel_interfaces()
			assert result == []
			assert mock_run.call_count == 5

	def test_missing_interface_detected(self, env_with_ue_profiles):
		def fake_run(cmd, **kwargs):
			iface = cmd[6]  # ['docker', 'exec', 'ueransim', 'ip', 'link', 'show', <iface>]
			m = MagicMock()
			m.returncode = 1 if iface == 'ue3tun0' else 0
			return m

		with patch('agent.env.subprocess.run', side_effect=fake_run):
			missing = env_with_ue_profiles._check_tunnel_interfaces()
			assert missing == ['admin']

	def test_recovery_triggers_registration_for_missing_slices(
		self, env_with_ue_profiles
	):
		with patch('agent.env.subprocess.run') as mock_run, patch('agent.env.time.sleep'):
			mock_run.return_value = MagicMock(returncode=0)
			env_with_ue_profiles._recover_tunnel_interfaces(['admin', 'iot'])

			registration_calls = [
				c for c in mock_run.call_args_list if '/ueransim/nr-ue' in c.args[0]
			]
			assert len(registration_calls) == 2

			configs_triggered = [c.args[0][-1] for c in registration_calls]
			assert '/ueransim/config/uecfg-ue3.yaml' in configs_triggered
			assert '/ueransim/config/uecfg-ue4.yaml' in configs_triggered

	def test_recovery_waits_for_interface_to_appear(self, env_with_ue_profiles):
		call_count = 0

		def fake_run(cmd, **kwargs):
			nonlocal call_count
			m = MagicMock()
			if 'ip' in cmd and 'link' in cmd:
				call_count += 1
				m.returncode = 0 if call_count >= 3 else 1
			else:
				m.returncode = 0
			return m

		with (
			patch('agent.env.subprocess.run', side_effect=fake_run),
			patch('agent.env.time.sleep'),
		):
			env_with_ue_profiles._recover_tunnel_interfaces(['vle'])

	def test_recovery_raises_after_timeout(self, env_with_ue_profiles):
		def fake_run(cmd, **kwargs):
			m = MagicMock()
			if 'ip' in cmd and 'link' in cmd:
				m.returncode = 1
			else:
				m.returncode = 0
			return m

		with (
			patch('agent.env.subprocess.run', side_effect=fake_run),
			patch('agent.env.time.sleep'),
		):
			with pytest.raises(RuntimeError, match='did not appear after 30s'):
				env_with_ue_profiles._recover_tunnel_interfaces(['vle'])

	def test_recovery_raises_if_no_ue_config_mapped(self, env):
		with pytest.raises(AssertionError, match='ue_profiles was not provided'):
			env._recover_tunnel_interfaces(['vle'])

	def test_reset_calls_tunnel_check(self, env_with_ue_profiles):
		with (
			patch.object(
				env_with_ue_profiles, '_check_tunnel_interfaces', return_value=[]
			) as mock_check,
			patch.object(
				env_with_ue_profiles,
				'_apply_allocation',
				return_value={
					'vle': 20000,
					'student_portal': 20000,
					'admin': 20000,
					'iot': 20000,
					'general': 20000,
				},
			),
			patch.object(env_with_ue_profiles, '_connect_ws'),
			patch.object(
				env_with_ue_profiles, '_wait_for_stats', return_value=_good_metrics()
			),
		):
			env_with_ue_profiles.reset()
			mock_check.assert_called_once()

	def test_reset_triggers_recovery_when_interfaces_missing(self, env_with_ue_profiles):
		with (
			patch.object(
				env_with_ue_profiles, '_check_tunnel_interfaces', return_value=['admin']
			),
			patch.object(env_with_ue_profiles, '_recover_tunnel_interfaces') as mock_recover,
			patch.object(
				env_with_ue_profiles,
				'_apply_allocation',
				return_value={
					'vle': 20000,
					'student_portal': 20000,
					'admin': 20000,
					'iot': 20000,
					'general': 20000,
				},
			),
			patch.object(env_with_ue_profiles, '_connect_ws'),
			patch.object(
				env_with_ue_profiles, '_wait_for_stats', return_value=_good_metrics()
			),
		):
			env_with_ue_profiles.reset()
			mock_recover.assert_called_once_with(['admin'])

	def test_subprocess_timeout_caught_by_reset(self, env_with_ue_profiles):
		with patch.object(
			env_with_ue_profiles,
			'_check_tunnel_interfaces',
			side_effect=subprocess.TimeoutExpired(cmd='docker', timeout=5),
		):
			with pytest.raises(RuntimeError, match='reset\\(\\) failed to start episode'):
				env_with_ue_profiles.reset()
