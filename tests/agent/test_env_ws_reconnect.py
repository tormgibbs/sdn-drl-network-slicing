# tests/agent/test_env_ws_reconnect.py
from unittest.mock import patch

import pytest

from agent.env import CampusSlicingEnv


def _make_env():
	slices_config = {
		'slice_order': ['vle'],
		'slices': {
			'vle': {'min_throughput_bps': 5_000_000, 'priority': 5, 'max_latency_ms': 100},
		},
		'network': {'total_bandwidth_bps': 100_000_000},
	}
	return CampusSlicingEnv(slices_config=slices_config)


def test_connect_ws_retries_then_succeeds():
	env = _make_env()
	calls = {'n': 0}

	def flaky_connect(url):
		calls['n'] += 1
		if calls['n'] < 3:
			raise ConnectionRefusedError('refused')
		return object()

	with (
		patch('agent.env.ws_connect', side_effect=flaky_connect),
		patch('agent.env.time.sleep'),
	):  # don't actually wait in the test
		env._connect_ws()

	assert calls['n'] == 3


def test_connect_ws_raises_after_max_retries():
	env = _make_env()

	with (
		patch('agent.env.ws_connect', side_effect=ConnectionRefusedError('refused')),
		patch('agent.env.time.sleep'),
	):
		with pytest.raises(RuntimeError, match='could not connect'):
			env._connect_ws()
