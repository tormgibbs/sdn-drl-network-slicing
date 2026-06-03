# tests/infrastructure/controller/test_rest_api.py
# Unit tests for the REST API endpoints covering health, metrics, and allocation
# validation. Uses FastAPI TestClient for in-process route testing without a
# running server.

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from infrastructure.controller.rest_api import app, registry


@pytest.fixture(autouse=True)
def reset_registry():
	registry.reset()
	yield
	registry.reset()


def _make_stats_collector(stats: dict):
	sc = MagicMock()
	sc.get_stats.return_value = stats
	return sc


def _make_meter_manager(slice_names: frozenset):
	mm = MagicMock()
	mm.slice_names = slice_names
	return mm


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
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		registry.reset()
		resp = client.get('/metrics')
		assert resp.status_code == 503

	def test_frozen_false_after_reset(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
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
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		resp = client.get('/health')
		assert resp.json()['registry_frozen'] is True


class TestMetrics:
	def test_returns_503_when_registry_empty(self):
		resp = client.get('/metrics')
		assert resp.status_code == 503

	def test_returns_empty_dict_when_no_stats(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		resp = client.get('/metrics')
		assert resp.status_code == 200
		assert resp.json() == {}

	def test_duration_sec_stripped_from_response(self):
		registry.register(
			_make_stats_collector(SAMPLE_STATS), _make_meter_manager(SLICE_NAMES)
		)
		resp = client.get('/metrics')
		assert resp.status_code == 200
		assert 'duration_sec' not in resp.json()['vle']

	def test_throughput_fields_present(self):
		registry.register(
			_make_stats_collector(SAMPLE_STATS), _make_meter_manager(SLICE_NAMES)
		)
		resp = client.get('/metrics')
		vle = resp.json()['vle']
		assert 'tx_throughput_bps' in vle
		assert 'rx_throughput_bps' in vle

	def test_all_slice_fields_preserved_except_duration(self):
		registry.register(
			_make_stats_collector(SAMPLE_STATS), _make_meter_manager(SLICE_NAMES)
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
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		resp = client.post('/allocate', json=self.VALID_ALLOC)
		assert resp.status_code == 200
		assert resp.json()['status'] == 'ok'

	def test_valid_allocation_calls_install_meters(self):
		mm = _make_meter_manager(SLICE_NAMES)
		registry.register(_make_stats_collector({}), mm)
		client.post('/allocate', json=self.VALID_ALLOC)
		mm.install_meters.assert_called_once_with(self.VALID_ALLOC)

	def test_missing_slice_returns_422(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		alloc = {k: v for k, v in self.VALID_ALLOC.items() if k != 'general'}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
		assert 'general' in resp.json()['detail']

	def test_extra_slice_returns_422(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		alloc = {**self.VALID_ALLOC, 'unknown_slice': 0.1}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
		assert 'unknown_slice' in resp.json()['detail']

	def test_sum_exceeds_tolerance_returns_422(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		alloc = {**self.VALID_ALLOC, 'vle': 0.9}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
		assert 'sum' in resp.json()['detail'].lower()

	def test_sum_within_tolerance_accepted(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		alloc = {**self.VALID_ALLOC, 'vle': 0.4009}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 200

	def test_install_meters_not_called_on_validation_failure(self):
		mm = _make_meter_manager(SLICE_NAMES)
		registry.register(_make_stats_collector({}), mm)
		alloc = {k: v for k, v in self.VALID_ALLOC.items() if k != 'general'}
		client.post('/allocate', json=alloc)
		mm.install_meters.assert_not_called()

	def test_all_zero_fractions_returns_422(self):
		registry.register(_make_stats_collector({}), _make_meter_manager(SLICE_NAMES))
		alloc = {k: 0.0 for k in SLICE_NAMES}
		resp = client.post('/allocate', json=alloc)
		assert resp.status_code == 422
