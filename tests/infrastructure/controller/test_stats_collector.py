# tests/infrastructure/controller/test_stats_collector.py

import threading
from unittest.mock import MagicMock, patch

import pytest
import yaml
from os_ken.lib import hub

from infrastructure.controller.stats_collector import StatsCollector

SAMPLE_TOPOLOGY = {
	'topology': {
		'ap_slice_map': {
			'ap1': 'vle',
			'ap2': 'student_portal',
			'ap3': 'admin',
			'ap4': 'iot',
			'ap5': 'general',
		},
		'aggregation_ports': {
			's2': {
				'core_port': 1,
				'ap_ports': {'ap1': 2, 'ap2': 3, 'ap3': 4},
			},
			's3': {
				'core_port': 1,
				'ap_ports': {'ap4': 2, 'ap5': 3},
			},
		},
	}
}

SAMPLE_SLICES = {
	'slices': {
		'vle': {'sink_ip': '10.0.1.1', 'probe_interface': 'ue1tun0'},
		'student_portal': {'sink_ip': '10.0.2.1', 'probe_interface': 'ue2tun0'},
		'admin': {'sink_ip': '10.0.3.1', 'probe_interface': 'ue3tun0'},
		'iot': {'sink_ip': '10.0.4.1', 'probe_interface': 'ue4tun0'},
		'general': {'sink_ip': '10.0.5.1', 'probe_interface': 'ue5tun0'},
	}
}

MULTI_AP_SLICE_TOPOLOGY = {
	'topology': {
		'ap_slice_map': {
			'ap1': 'vle',
			'ap2': 'vle',
		},
		'aggregation_ports': {
			's2': {
				'core_port': 1,
				'ap_ports': {'ap1': 2, 'ap2': 3},
			},
		},
	}
}

MULTI_AP_SLICES = {
	'slices': {
		'vle': {'sink_ip': '10.0.1.1', 'probe_interface': 'ue1tun0'},
	}
}


@pytest.fixture
def config_files(tmp_path):
	topology_path = tmp_path / 'topology.yaml'
	slices_path = tmp_path / 'slices.yaml'
	topology_path.write_text(yaml.dump(SAMPLE_TOPOLOGY))
	slices_path.write_text(yaml.dump(SAMPLE_SLICES))
	return topology_path, slices_path


@pytest.fixture
def multi_ap_config(tmp_path):
	topology_path = tmp_path / 'topology.yaml'
	slices_path = tmp_path / 'slices.yaml'
	topology_path.write_text(yaml.dump(MULTI_AP_SLICE_TOPOLOGY))
	slices_path.write_text(yaml.dump(MULTI_AP_SLICES))
	return topology_path, slices_path


@pytest.fixture
def collector(config_files):
	topology_path, slices_path = config_files
	return StatsCollector(
		topology_config=topology_path,
		slices_config=slices_path,
		interval_sec=5,
	)


@pytest.fixture
def multi_ap_collector(multi_ap_config):
	topology_path, slices_path = multi_ap_config
	return StatsCollector(
		topology_config=topology_path,
		slices_config=slices_path,
		interval_sec=5,
	)


def _make_stat(
	port_no,
	tx_bytes,
	rx_bytes,
	tx_packets=0,
	rx_packets=0,
	tx_errors=0,
	rx_errors=0,
	duration_sec=10,
):
	stat = MagicMock()
	stat.port_no = port_no
	stat.tx_bytes = tx_bytes
	stat.rx_bytes = rx_bytes
	stat.tx_packets = tx_packets
	stat.rx_packets = rx_packets
	stat.tx_errors = tx_errors
	stat.rx_errors = rx_errors
	stat.duration_sec = duration_sec
	return stat


def _fake_probe(results, slice_name, sink_ip, probe_interface):
	results[slice_name] = {
		'latency_ms': 1.0,
		'loss_pct': 0.0,
		'error': None,
	}


def _run_probe_cycle_with_mock(collector):
	def fake_spawn(fn, *args):
		fn(*args)
		gt = MagicMock()
		gt.wait = lambda: None
		return gt

	with patch.object(collector, '_probe_slice', side_effect=_fake_probe):
		with patch(
			'infrastructure.controller.stats_collector.hub.spawn', side_effect=fake_spawn
		):
			collector._run_probe_cycle()


class TestRegisterDatapath:
	def test_stores_datapath(self, collector):
		dp = MagicMock()
		collector.register_datapath('s2', dp)
		assert collector._datapaths['s2'] is dp

	def test_overwrites_on_reconnect(self, collector):
		dp1 = MagicMock()
		dp2 = MagicMock()
		collector.register_datapath('s2', dp1)
		collector.register_datapath('s2', dp2)
		assert collector._datapaths['s2'] is dp2


class TestStart:
	def test_double_start_spawns_only_one_loop(self, collector):
		with patch('infrastructure.controller.stats_collector.hub') as mock_hub:
			collector.start()
			collector.start()
			assert mock_hub.spawn.call_count == 1

	def test_running_flag_set_after_start(self, collector):
		with patch('infrastructure.controller.stats_collector.hub'):
			collector.start()
			assert collector._running is True

	def test_stop_clears_running_flag(self, collector):
		with patch('infrastructure.controller.stats_collector.hub'):
			collector.start()
			collector.stop()
			assert collector._running is False

	def test_stop_without_start_does_not_raise(self, collector):
		collector.stop()
		assert collector._running is False


class TestGetStats:
	def test_returns_empty_dict_before_any_cycle(self, collector):
		assert collector.get_stats() == {}

	def test_returns_copy_not_reference(self, collector):
		collector._stats_cache['vle'] = {'tx_throughput_bps': 1000.0}
		result = collector.get_stats()
		result['vle']['tx_throughput_bps'] = 9999.0
		assert collector._stats_cache['vle']['tx_throughput_bps'] == 1000.0


class TestHandlePortStatsReply:
	def test_unknown_switch_returns_without_error(self, collector):
		collector.handle_port_stats_reply('s99', [_make_stat(2, 1000, 500)])

	def test_port_with_no_slice_mapping_is_ignored(self, collector):
		collector.handle_port_stats_reply('s2', [_make_stat(99, 1000, 500)])
		assert collector._pending_throughput == {}

	def test_throughput_accumulated_in_pending(self, collector):
		with patch('time.time', return_value=100.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 0, 0)])
		with patch('time.time', return_value=101.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 8_000_000, 0)])
		assert abs(collector._pending_throughput['vle'] - 64_000_000.0) < 1.0

	def test_counter_reset_skips_interval(self, collector):
		with patch('time.time', return_value=100.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 8_000_000, 0)])
		with patch('time.time', return_value=101.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 100, 0)])
		assert collector._pending_throughput.get('vle', 0.0) == 0.0

	def test_counter_reset_next_interval_is_clean(self, collector):
		with patch('time.time', return_value=100.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 8_000_000, 0)])
		with patch('time.time', return_value=101.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 100, 0)])

		collector._pending_throughput.clear()
		collector._reply_count = 0
		collector._reply_event = hub.Event()

		with patch('time.time', return_value=102.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 1000, 0)])
		assert abs(collector._pending_throughput['vle'] - 7200.0) < 1.0

	def test_reply_count_increments_per_switch(self, collector):
		collector.handle_port_stats_reply('s2', [_make_stat(2, 0, 0)])
		assert collector._reply_count == 1
		collector.handle_port_stats_reply('s3', [_make_stat(2, 0, 0)])
		assert collector._reply_count == 2

	def test_event_set_when_all_replies_received(self, collector):
		collector._reply_event = threading.Event()
		collector.handle_port_stats_reply('s2', [_make_stat(2, 0, 0)])
		assert not collector._reply_event.is_set()
		collector.handle_port_stats_reply('s3', [_make_stat(2, 0, 0)])
		assert collector._reply_event.is_set()


class TestProbeCycle:
	def test_cache_populated_after_probe_cycle(self, collector):
		with patch('time.time', return_value=100.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 0, 0)])
		with patch('time.time', return_value=101.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 8_000_000, 0)])

		_run_probe_cycle_with_mock(collector)

		stats = collector.get_stats()
		assert 'vle' in stats
		assert abs(stats['vle']['tx_throughput_bps'] - 64_000_000.0) < 1.0
		assert stats['vle']['latency_ms'] == 1.0
		assert stats['vle']['loss_pct'] == 0.0

	def test_all_slices_populated_after_probe_cycle(self, collector):
		_run_probe_cycle_with_mock(collector)
		stats = collector.get_stats()
		for slice_name in ('vle', 'student_portal', 'admin', 'iot', 'general'):
			assert slice_name in stats

	def test_probe_failure_sets_none_values(self, collector):
		def failing_probe(results, slice_name, sink_ip, probe_interface):
			results[slice_name] = {
				'latency_ms': None,
				'loss_pct': None,
				'error': 'timeout',
			}

		def fake_spawn(fn, *args):
			fn(*args)
			gt = MagicMock()
			gt.wait = lambda: None
			return gt

		with patch.object(collector, '_probe_slice', side_effect=failing_probe):
			with patch(
				'infrastructure.controller.stats_collector.hub.spawn', side_effect=fake_spawn
			):
				collector._run_probe_cycle()

		stats = collector.get_stats()
		assert stats['vle']['latency_ms'] is None
		assert stats['vle']['loss_pct'] is None

	def test_throughput_zero_when_no_port_stats_received(self, collector):
		_run_probe_cycle_with_mock(collector)
		stats = collector.get_stats()
		assert stats['vle']['tx_throughput_bps'] == 0.0

	def test_slice_missing_probe_config_is_skipped(self, tmp_path):
		topology_path = tmp_path / 'topology.yaml'
		slices_path = tmp_path / 'slices.yaml'
		topology_path.write_text(yaml.dump(SAMPLE_TOPOLOGY))
		slices_path.write_text(yaml.dump({'slices': {'vle': {}}}))
		c = StatsCollector(topology_config=topology_path, slices_config=slices_path)
		_run_probe_cycle_with_mock(c)
		assert c.get_stats() == {}

	def test_throughput_accumulated_across_ports_same_slice(self, multi_ap_collector):
		with patch('time.time', return_value=100.0):
			multi_ap_collector.handle_port_stats_reply(
				's2', [_make_stat(2, 0, 0), _make_stat(3, 0, 0)]
			)
		with patch('time.time', return_value=101.0):
			multi_ap_collector.handle_port_stats_reply(
				's2', [_make_stat(2, 8_000_000, 0), _make_stat(3, 8_000_000, 0)]
			)

		_run_probe_cycle_with_mock(multi_ap_collector)

		stats = multi_ap_collector.get_stats()
		assert abs(stats['vle']['tx_throughput_bps'] - 128_000_000.0) < 1.0

	def test_two_switches_populate_independent_slices(self, collector):
		with patch('time.time', return_value=100.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 0, 0)])
			collector.handle_port_stats_reply('s3', [_make_stat(2, 0, 0)])
		with patch('time.time', return_value=101.0):
			collector.handle_port_stats_reply('s2', [_make_stat(2, 8_000_000, 0)])
			collector.handle_port_stats_reply('s3', [_make_stat(2, 4_000_000, 0)])

		_run_probe_cycle_with_mock(collector)

		stats = collector.get_stats()
		assert abs(stats['vle']['tx_throughput_bps'] - 64_000_000.0) < 1.0
		assert abs(stats['iot']['tx_throughput_bps'] - 32_000_000.0) < 1.0


class TestRequestStats:
	def test_no_datapaths_does_not_raise(self, collector):
		collector._request_stats()


class TestBroadcast:
	def test_no_broadcast_when_loop_is_none(self, collector):
		with (
			patch(
				'infrastructure.controller.stats_collector.rest_api.registry'
			) as mock_registry,
			patch(
				'infrastructure.controller.stats_collector.rest_api.broadcast_metrics'
			) as mock_broadcast,
			patch(
				'infrastructure.controller.stats_collector.asyncio.run_coroutine_threadsafe'
			) as mock_run,
		):
			mock_registry.loop = None
			_run_probe_cycle_with_mock(collector)

		mock_broadcast.assert_not_called()
		mock_run.assert_not_called()

	def test_broadcast_called_when_loop_set(self, collector):
		# Unit-level only: verifies the call signature (snapshot + loop passed
		# to run_coroutine_threadsafe), not that cross-thread dispatch actually
		# delivers to a real asyncio loop/websocket. That path was manually
		# verified end-to-end via a live websocket client during development;
		# see PENDING for automating it as an integration test.
		mock_loop = MagicMock()
		sentinel_coro = object()
		with (
			patch(
				'infrastructure.controller.stats_collector.rest_api.registry'
			) as mock_registry,
			patch(
				'infrastructure.controller.stats_collector.rest_api.broadcast_metrics',
				new_callable=MagicMock,
				return_value=sentinel_coro,
			) as mock_broadcast,
			patch(
				'infrastructure.controller.stats_collector.asyncio.run_coroutine_threadsafe'
			) as mock_run,
		):
			mock_registry.loop = mock_loop
			_run_probe_cycle_with_mock(collector)

		expected_snapshot = collector.get_stats()
		mock_broadcast.assert_called_once_with(expected_snapshot)
		mock_run.assert_called_once_with(sentinel_coro, mock_loop)
