# tests/agent/test_sim_env_tcp_modeling.py
import pytest

from agent.sim_env import _TCP_LOSS_PCT_CAP, SimCampusEnv


@pytest.fixture
def env():
	slices_cfg = {
		'slice_order': ['admin', 'vle'],
		'slices': {
			'admin': {
				'min_throughput_bps': 2_000_000,
				'priority': 3,
				'max_latency_ms': 150,
				'max_loss_pct': 1.0,
			},
			'vle': {
				'min_throughput_bps': 5_000_000,
				'priority': 5,
				'max_latency_ms': 100,
				'max_loss_pct': 0.5,
			},
		},
		'network': {'total_bandwidth_bps': 100_000_000},
	}
	e = SimCampusEnv(slices_cfg)
	e.reset(seed=0)
	e._base_latency_ms['admin'] = 10.0
	e._base_latency_ms['vle'] = 10.0
	return e


def test_tcp_under_ceiling_zero_loss(env):
	env._current_rates_kbps['admin'] = 20_000
	env._factors['admin'] = 1.0
	metrics = env._compute_metrics()
	assert metrics['admin']['loss_pct'] == 0.0
	assert metrics['admin']['tx_throughput_bps'] <= 20_000_000


def test_tcp_congested_loss_small_and_bounded(env):
	env._current_rates_kbps['admin'] = 2_000
	env._factors['admin'] = 5.0
	metrics = env._compute_metrics()

	assert metrics['admin']['tx_throughput_bps'] == 2_000_000
	assert 0.0 < metrics['admin']['loss_pct'] <= _TCP_LOSS_PCT_CAP
	assert metrics['admin']['loss_pct'] < 50.0


def test_udp_congested_loss_unchanged_linear(env):
	env._current_rates_kbps['vle'] = 5_000
	env._factors['vle'] = 3.0
	env._on_off_state['vle'] = False

	offered = env._offered_bps('vle')
	env._on_off_timer['vle'] = 999

	metrics = env._compute_metrics()
	ceiling_bps = 5_000_000
	expected_loss = min(100.0 * (offered - ceiling_bps) / offered, 100.0)

	assert abs(metrics['vle']['loss_pct'] - expected_loss) < 1e-6


def test_tcp_extreme_squeeze_respects_loss_cap(env):
	env._current_rates_kbps['admin'] = 1
	env._factors['admin'] = 1000.0
	metrics = env._compute_metrics()

	assert metrics['admin']['loss_pct'] <= _TCP_LOSS_PCT_CAP
