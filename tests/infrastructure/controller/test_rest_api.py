# tests/infrastructure/controller/test_rest_api.py
# Unit tests for the REST API endpoints covering health, metrics, and allocation
# validation. Uses FastAPI TestClient for in-process route testing without a
# running server.

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from infrastructure.controller.rest_api import (
	_Registry,
	app,
	broadcast_metrics,
	registry,
)


@pytest.fixture(autouse=True)
def reset_registry():
	registry.reset()
	registry.ws_clients = set()
	yield
	registry.reset()
	registry.ws_clients = set()


def _make_stats_collector(stats: dict):
	sc = MagicMock()
	sc.get_stats.return_value = stats
	return sc


def _make_meter_manager(slice_names: frozenset):
	mm = MagicMock()
	mm.slice_names = slice_names
	mm.install_meters.return_value = {name: 1000 for name in slice_names}
	return mm


def _make_agent_manager(running=False, last_result=None):
	am = MagicMock()
	am.status.return_value = {'running': running, 'last_result': last_result}
	return am


def _make_traffic_manager(running=False, last_loop=None):
	tm = MagicMock()
	tm.status.return_value = {'running': running, 'last_loop': last_loop}
	return tm


SLICE_NAMES = frozenset({'vle', 'student_portal', 'admin', 'iot', 'general'})

SAMPLE_STATS = {
	'vle': {
		'tx_bytes': 1000,
		'rx_bytes': 500,
		'tx_packets': 10,
		'rx_packets': 5,
		'tx_errors': 0,
		'rx_errors': 0,
		'duration_sec': 30,
		'tx_throughput_bps': 8000.0,
		'rx_throughput_bps': 4000.0,
	}
}

client = TestClient(app)


class TestRegistryIsolation:
	def test_reset_clears_registry_state(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		registry.reset()
		resp = client.get('/metrics')
		assert resp.status_code == 503

	def test_frozen_false_after_reset(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		registry.reset()
		resp = client.get('/health')
		assert resp.json()['registry_frozen'] is False


class TestHealth:
	def test_returns_ok_when_registry_empty(self):
		resp = client.get('/health')
		assert resp.status_code == 200
		assert resp.json()['status'] == 'ok'

	def test_frozen_false_before_register(self):
		resp = client.get('/health')
		assert resp.json()['registry_frozen'] is False

	def test_frozen_true_after_register(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.get('/health')
		assert resp.json()['registry_frozen'] is True


class TestMetrics:
	def test_returns_503_when_registry_empty(self):
		resp = client.get('/metrics')
		assert resp.status_code == 503

	def test_returns_empty_dict_when_no_stats(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.get('/metrics')
		assert resp.status_code == 200
		assert resp.json() == {}

	def test_duration_sec_stripped_from_response(self):
		registry.register(
			_make_stats_collector(SAMPLE_STATS),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.get('/metrics')
		assert resp.status_code == 200
		assert 'duration_sec' not in resp.json()['vle']

	def test_throughput_fields_present(self):
		registry.register(
			_make_stats_collector(SAMPLE_STATS),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.get('/metrics')
		vle = resp.json()['vle']
		assert 'tx_throughput_bps' in vle
		assert 'rx_throughput_bps' in vle

	def test_all_slice_fields_preserved_except_duration(self):
		registry.register(
			_make_stats_collector(SAMPLE_STATS),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.get('/metrics')
		vle = resp.json()['vle']
		expected_keys = {
			'tx_bytes',
			'rx_bytes',
			'tx_packets',
			'rx_packets',
			'tx_errors',
			'rx_errors',
			'tx_throughput_bps',
			'rx_throughput_bps',
		}
		assert set(vle.keys()) == expected_keys


class TestAllocate:
	VALID_ALLOC = {
		'vle': 0.4,
		'student_portal': 0.2,
		'admin': 0.2,
		'iot': 0.1,
		'general': 0.1,
	}

	def test_returns_503_when_registry_empty(self):
		resp = client.post('/allocate', json=self.VALID_ALLOC)
		assert resp.status_code == 503

	def test_valid_allocation_returns_200(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.post('/allocate', json=self.VALID_ALLOC)
		assert resp.status_code == 200
		assert resp.json()['status'] == 'ok'

	def test_valid_allocation_calls_install_meters(self):
		mm = _make_meter_manager(SLICE_NAMES)
		registry.register(
			_make_stats_collector({}),
			mm,
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		client.post('/allocate', json=self.VALID_ALLOC)
		mm.install_meters.assert_called_once_with(self.VALID_ALLOC)

	def test_missing_slice_returns_422(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		alloc = {k: v for k, v in self.VALID_ALLOC.items() if k != 'general'}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
		assert 'general' in resp.json()['detail']

	def test_extra_slice_returns_422(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		alloc = {**self.VALID_ALLOC, 'unknown_slice': 0.1}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
		assert 'unknown_slice' in resp.json()['detail']

	def test_sum_exceeds_tolerance_returns_422(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		alloc = {**self.VALID_ALLOC, 'vle': 0.9}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
		assert 'sum' in resp.json()['detail'].lower()

	def test_sum_within_tolerance_accepted(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		alloc = {**self.VALID_ALLOC, 'vle': 0.4009}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 200

	def test_install_meters_not_called_on_validation_failure(self):
		mm = _make_meter_manager(SLICE_NAMES)
		registry.register(
			_make_stats_collector({}),
			mm,
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		alloc = {k: v for k, v in self.VALID_ALLOC.items() if k != 'general'}
		client.post('/allocate', json=alloc)
		mm.install_meters.assert_not_called()

	def test_all_zero_fractions_returns_422(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		alloc = {k: 0.0 for k in SLICE_NAMES}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422

	def test_valid_allocation_returns_rates_kbps(self):
		mm = _make_meter_manager(SLICE_NAMES)
		mm.install_meters.return_value = {'vle': 51988, 'student_portal': 26987}
		registry.register(
			_make_stats_collector({}),
			mm,
			_make_agent_manager(),
			_make_traffic_manager(),
		)
		resp = client.post('/allocate', json=self.VALID_ALLOC)
		assert resp.json() == {
			'status': 'ok',
			'rates_kbps': {'vle': 51988, 'student_portal': 26987},
		}


class TestRegistryDefaults:
	def test_fresh_registry_has_no_loop(self):
		r = _Registry()
		assert r.loop is None

	def test_fresh_registry_has_empty_ws_clients(self):
		r = _Registry()
		assert r.ws_clients == set()


class TestBroadcastMetrics:
	def test_sends_to_all_clients(self):
		ws1 = MagicMock()
		ws1.send_json = AsyncMock()
		ws2 = MagicMock()
		ws2.send_json = AsyncMock()
		registry.ws_clients = {ws1, ws2}
		registry._agent_manager = None

		payload = {'vle': {'tx_throughput_bps': 1.0}}
		asyncio.run(broadcast_metrics(payload))

		sent1 = ws1.send_json.await_args.args[0]
		sent2 = ws2.send_json.await_args.args[0]
		assert sent1 == sent2
		assert sent1['metrics'] == payload
		assert sent1['agent'] is None
		assert 'timestamp' in sent1

	def test_dead_client_removed_from_registry(self):
		good = MagicMock()
		good.send_json = AsyncMock()
		dead = MagicMock()
		dead.send_json = AsyncMock(side_effect=RuntimeError('client disconnected'))
		registry.ws_clients = {good, dead}

		asyncio.run(broadcast_metrics({}))

		assert dead not in registry.ws_clients
		assert good in registry.ws_clients

	def test_empty_clients_does_not_raise(self):
		registry.ws_clients = set()
		asyncio.run(broadcast_metrics({'vle': {}}))

	def test_multiple_dead_clients_pruned_without_affecting_survivors(self):
		survivors = [MagicMock() for _ in range(2)]
		for ws in survivors:
			ws.send_json = AsyncMock()
		failures = [MagicMock() for _ in range(3)]
		for ws in failures:
			ws.send_json = AsyncMock(side_effect=RuntimeError('client disconnected'))

		registry.ws_clients = set(survivors + failures)
		registry._agent_manager = None

		payload = {'vle': {'tx_throughput_bps': 1.0}}
		asyncio.run(broadcast_metrics(payload))

		assert registry.ws_clients == set(survivors)
		for ws in survivors:
			sent = ws.send_json.await_args.args[0]
			assert sent['metrics'] == payload
			assert sent['agent'] is None


class TestBroadcastMetricsAgentStatus:
	def test_agent_field_populated_when_running(self):
		am = MagicMock()
		am.status.return_value = {'running': True, 'last_result': {'step': 3}}
		registry._agent_manager = am

		ws = MagicMock()
		ws.send_json = AsyncMock()
		registry.ws_clients = {ws}

		asyncio.run(broadcast_metrics({'vle': {'tx_throughput_bps': 100}}))

		sent = ws.send_json.await_args.args[0]
		assert sent['agent'] == {'step': 3}
		assert sent['metrics'] == {'vle': {'tx_throughput_bps': 100}}

	def test_agent_field_none_when_not_running(self):
		am = MagicMock()
		am.status.return_value = {'running': False, 'last_result': {'step': 3}}
		registry._agent_manager = am

		ws = MagicMock()
		ws.send_json = AsyncMock()
		registry.ws_clients = {ws}

		asyncio.run(broadcast_metrics({'vle': {}}))

		sent = ws.send_json.await_args.args[0]
		assert sent['agent'] is None

	def test_agent_field_none_when_no_agent_manager(self):
		registry._agent_manager = None

		ws = MagicMock()
		ws.send_json = AsyncMock()
		registry.ws_clients = {ws}

		asyncio.run(broadcast_metrics({'vle': {}}))

		sent = ws.send_json.await_args.args[0]
		assert sent['agent'] is None


class TestBroadcastMetricsDoesNotBlockLoop:
	def test_status_call_does_not_block_other_coroutines(self):
		blocking_started = threading.Event()
		release = threading.Event()

		class SlowAgentManager:
			def status(self):
				blocking_started.set()
				release.wait(timeout=2.0)
				return {'running': True, 'last_result': {'step': 1}}

		registry._agent_manager = SlowAgentManager()
		registry.ws_clients = set()

		other_ran = []

		async def other_coro():
			await asyncio.sleep(0.01)
			other_ran.append(True)

		async def run_concurrently():
			broadcast_task = asyncio.create_task(broadcast_metrics({'vle': {}}))
			other_task = asyncio.create_task(other_coro())

			loop = asyncio.get_running_loop()
			await loop.run_in_executor(None, blocking_started.wait, 1.0)

			await asyncio.sleep(0.05)
			assert other_ran, 'other coroutine did not run -- status() blocked the loop'

			release.set()
			await broadcast_task
			await other_task

		asyncio.run(run_concurrently())


class TestTrafficState:
	def test_returns_503_when_no_traffic_manager(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			None,
		)
		resp = client.get('/traffic/state')
		assert resp.status_code == 503

	def test_returns_status_when_available(self):
		tm = _make_traffic_manager(running=True, last_loop={'loop': 2})
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.get('/traffic/state')
		assert resp.status_code == 200
		assert resp.json() == {'running': True, 'last_loop': {'loop': 2}}


class TestTrafficControl:
	def test_returns_503_when_no_traffic_manager(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			None,
		)
		resp = client.post('/traffic/control', json={'action': 'start'})
		assert resp.status_code == 503

	def test_start_calls_tm_start_with_body_fields(self):
		tm = _make_traffic_manager()
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post(
			'/traffic/control',
			json={
				'action': 'start',
				'slices': ['vle'],
				'loops': 3,
				'scenario': 'exam_week',
				'seed': 42,
			},
		)
		assert resp.status_code == 200
		tm.start.assert_called_once_with(
			slices=['vle'], loops=3, scenario='exam_week', seed=42
		)

	def test_start_defaults_when_fields_omitted(self):
		tm = _make_traffic_manager()
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/control', json={'action': 'start'})
		assert resp.status_code == 200
		tm.start.assert_called_once_with(slices=None, loops=0, scenario=None, seed=None)

	def test_start_conflict_returns_409(self):
		tm = _make_traffic_manager()
		tm.start.side_effect = RuntimeError('Traffic generator already running')
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/control', json={'action': 'start'})
		assert resp.status_code == 409
		assert 'already running' in resp.json()['detail']

	def test_stop_calls_tm_stop(self):
		tm = _make_traffic_manager()
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/control', json={'action': 'stop'})
		assert resp.status_code == 200
		tm.stop.assert_called_once()

	def test_unknown_action_returns_422(self):
		tm = _make_traffic_manager()
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/control', json={'action': 'pause'})
		assert resp.status_code == 422


class TestTrafficScenario:
	def test_returns_503_when_no_traffic_manager(self):
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			None,
		)
		resp = client.post('/traffic/scenario', json={'scenario': 'exam_week'})
		assert resp.status_code == 503

	def test_missing_scenario_field_returns_422(self):
		tm = _make_traffic_manager()
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/scenario', json={})
		assert resp.status_code == 422

	def test_valid_scenario_delegates_to_manager(self):
		tm = _make_traffic_manager()
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/scenario', json={'scenario': 'exam_week'})
		assert resp.status_code == 200
		tm.set_scenario.assert_called_once_with('exam_week')

	def test_unknown_scenario_value_error_returns_409(self):
		tm = _make_traffic_manager()
		tm.set_scenario.side_effect = ValueError('Unknown scenario')
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/scenario', json={'scenario': 'bogus'})
		assert resp.status_code == 409

	def test_not_running_runtime_error_returns_409(self):
		tm = _make_traffic_manager()
		tm.set_scenario.side_effect = RuntimeError('Traffic generator not running')
		registry.register(
			_make_stats_collector({}),
			_make_meter_manager(SLICE_NAMES),
			_make_agent_manager(),
			tm,
		)
		resp = client.post('/traffic/scenario', json={'scenario': 'exam_week'})
		assert resp.status_code == 409
