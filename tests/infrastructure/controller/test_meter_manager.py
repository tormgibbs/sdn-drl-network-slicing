# tests/infrastructure/controller/test_meter_manager.py
# Unit tests for MeterManager meter installation, reconnect handling, and allocation logic.

import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from infrastructure.controller.meter_manager import MeterManager

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
	'slice_order': ['vle', 'student_portal', 'admin', 'iot', 'general'],
	'network': {'total_bandwidth_bps': 100_000_000},
	'slices': {
		'vle': {'vlan': 10, 'min_throughput_bps': 5_000_000},
		'student_portal': {'vlan': 20, 'min_throughput_bps': 5_000_000},
		'admin': {'vlan': 30, 'min_throughput_bps': 5_000_000},
		'iot': {'vlan': 40, 'min_throughput_bps': 5_000_000},
		'general': {'vlan': 50, 'min_throughput_bps': 5_000_000},
	},
}

SKEWED_SLICES = {
	'slice_order': ['vle', 'student_portal', 'admin', 'iot', 'general'],
	'network': {'total_bandwidth_bps': 100_000_000},
	'slices': {
		'vle': {'vlan': 10, 'min_throughput_bps': 50_000_000},
		'student_portal': {'vlan': 20, 'min_throughput_bps': 25_000_000},
		'admin': {'vlan': 30, 'min_throughput_bps': 10_000_000},
		'iot': {'vlan': 40, 'min_throughput_bps': 64_000},
		'general': {'vlan': 50, 'min_throughput_bps': 5_000_000},
	},
}


@pytest.fixture
def manager_skewed_floors(tmp_path):
	topology_path = tmp_path / 'topology.yaml'
	slices_path = tmp_path / 'slices.yaml'
	topology_path.write_text(yaml.dump(SAMPLE_TOPOLOGY))
	slices_path.write_text(yaml.dump(SKEWED_SLICES))
	return MeterManager(topology_config=topology_path, slices_config=slices_path)


@pytest.fixture
def config_files(tmp_path):
	topology_path = tmp_path / 'topology.yaml'
	slices_path = tmp_path / 'slices.yaml'
	topology_path.write_text(yaml.dump(SAMPLE_TOPOLOGY))
	slices_path.write_text(yaml.dump(SAMPLE_SLICES))
	return topology_path, slices_path


@pytest.fixture
def manager(config_files):
	topology_path, slices_path = config_files
	return MeterManager(topology_config=topology_path, slices_config=slices_path)


def _make_datapath():
	dp = MagicMock()
	dp.ofproto.OFPMC_DELETE = 3
	dp.ofproto.OFPMC_ADD = 0
	dp.ofproto.OFPMF_KBPS = 1
	dp.ofproto.OFPMBT_DROP = 1
	dp.ofproto.OFPIT_APPLY_ACTIONS = 4
	dp.ofproto.OFPP_FLOOD = 0xFFFFFFFB
	return dp


class TestRegisterDatapath:
	def test_single_switch_does_not_trigger_install(self, manager):
		dp = _make_datapath()
		manager.register_datapath('s2', dp)
		dp.send_msg.assert_not_called()

	def test_both_switches_trigger_default_install(self, manager):
		dp_s2 = _make_datapath()
		dp_s3 = _make_datapath()
		manager.register_datapath('s2', dp_s2)
		manager.register_datapath('s3', dp_s3)
		assert dp_s2.send_msg.call_count > 0
		assert dp_s3.send_msg.call_count > 0

	def test_initialized_flag_set_after_first_connect(self, manager):
		manager.register_datapath('s2', _make_datapath())
		manager.register_datapath('s3', _make_datapath())
		assert manager._initialized is True

	def test_reconnect_does_not_call_install_default_meters(self, manager):
		manager.register_datapath('s2', _make_datapath())
		manager.register_datapath('s3', _make_datapath())

		with patch.object(manager, '_install_default_meters') as mock_default:
			manager.register_datapath('s3', _make_datapath())
			mock_default.assert_not_called()

	def test_reconnect_installs_meters_for_reconnected_switch_only(self, manager):
		manager.register_datapath('s2', _make_datapath())
		manager.register_datapath('s3', _make_datapath())

		with patch.object(manager, '_install_meters_for_switch') as mock_install:
			manager.register_datapath('s3', _make_datapath())
			call_args = mock_install.call_args[0]
			assert call_args[0] == 's3'
			expected_rates = manager._compute_rates_kbps(
				manager._current_allocations, manager._load_slices()
			)
			assert call_args[1] == expected_rates

	def test_reconnect_uses_current_allocations_not_defaults(self, manager):
		manager.register_datapath('s2', _make_datapath())
		manager.register_datapath('s3', _make_datapath())

		custom = {
			'vle': 0.4,
			'student_portal': 0.2,
			'admin': 0.2,
			'iot': 0.1,
			'general': 0.1,
		}
		manager.install_meters(custom)

		with patch.object(manager, '_install_meters_for_switch') as mock_install:
			manager.register_datapath('s3', _make_datapath())
			_, called_rates, *_ = mock_install.call_args[0]
			expected_rates = manager._compute_rates_kbps(custom, manager._load_slices())
			assert called_rates == expected_rates


class TestInstallMeters:
	def test_updates_current_allocations(self, manager):
		manager.register_datapath('s2', _make_datapath())
		manager.register_datapath('s3', _make_datapath())

		allocations = {
			'vle': 0.4,
			'student_portal': 0.2,
			'admin': 0.2,
			'iot': 0.1,
			'general': 0.1,
		}
		manager.install_meters(allocations)
		assert manager._current_allocations == allocations

	def test_updates_current_allocations_even_without_datapaths(self, manager):
		allocations = {
			'vle': 0.4,
			'student_portal': 0.2,
			'admin': 0.2,
			'iot': 0.1,
			'general': 0.1,
		}
		manager.install_meters(allocations)
		assert manager._current_allocations == allocations

	def test_no_registered_datapath_logs_error_does_not_raise(self, manager, caplog):
		with caplog.at_level(
			logging.ERROR, logger='infrastructure.controller.meter_manager'
		):
			manager.install_meters(
				{'vle': 0.2, 'student_portal': 0.2, 'admin': 0.2, 'iot': 0.2, 'general': 0.2}
			)
		assert 'No registered datapath' in caplog.text

	def test_rate_floored_at_min_throughput(self, manager_skewed_floors):
		dp2 = _make_datapath()
		manager_skewed_floors._datapaths['s2'] = dp2
		manager_skewed_floors._datapaths['s3'] = _make_datapath()
		manager_skewed_floors.install_meters(
			{'vle': 0.0, 'student_portal': 0.0, 'admin': 0.0, 'iot': 0.0, 'general': 0.0}
		)

		meter_mod_adds = [
			c
			for c in dp2.ofproto_parser.OFPMeterMod.call_args_list
			if c.kwargs.get('command') == dp2.ofproto.OFPMC_ADD
		]
		band_calls = dp2.ofproto_parser.OFPMeterBandDrop.call_args_list
		assert len(meter_mod_adds) == len(band_calls) == 3

		# meter_id -> slice on s2, per _METER_ID_BY_AP (ap1/ap2/ap3 -> 1/2/3).
		# OFPMeterBandDrop calls don't carry meter_id themselves, so each
		# band is matched to its ADD call by emission order -- a single
		# function's internal call order, not topology/AP iteration order.
		meter_id_to_slice = {1: 'vle', 2: 'student_portal', 3: 'admin'}
		expected_kbps = {'vle': 51988, 'student_portal': 26987, 'admin': 11987}
		expected_floor_kbps = {'vle': 50000, 'student_portal': 25000, 'admin': 10000}

		for mm_call, band_call in zip(meter_mod_adds, band_calls):
			slice_name = meter_id_to_slice[mm_call.kwargs['meter_id']]
			actual = band_call.kwargs['rate']
			assert actual == expected_kbps[slice_name], (
				f'{slice_name}: got {actual}, expected {expected_kbps[slice_name]}'
			)
			assert actual >= expected_floor_kbps[slice_name], (
				f'{slice_name}: got {actual} kbps, below its own floor of '
				f'{expected_floor_kbps[slice_name]} kbps'
			)


	def test_meter_ids_are_datapath_scoped(self, manager):
		dp_s2 = _make_datapath()
		dp_s3 = _make_datapath()
		manager.register_datapath('s2', dp_s2)
		manager.register_datapath('s3', dp_s3)

		s2_meter_ids = [
			c.kwargs['meter_id']
			for c in dp_s2.ofproto_parser.OFPMeterMod.call_args_list
			if c.kwargs.get('command') == dp_s2.ofproto.OFPMC_ADD
		]
		s3_meter_ids = [
			c.kwargs['meter_id']
			for c in dp_s3.ofproto_parser.OFPMeterMod.call_args_list
			if c.kwargs.get('command') == dp_s3.ofproto.OFPMC_ADD
		]

		# s2 covers ap1/ap2/ap3 -> meter IDs 1, 2, 3
		assert sorted(s2_meter_ids) == [1, 2, 3]
		# s3 covers ap4/ap5 -> meter IDs 1, 2 (datapath-local, not 4 and 5)
		assert sorted(s3_meter_ids) == [1, 2]


class TestReplaceMeter:
	def test_delete_sent_before_add(self, manager):
		dp = _make_datapath()
		manager._replace_meter(dp, meter_id=1, rate_kbps=10_000)

		delete_call = dp.ofproto_parser.OFPMeterMod.call_args_list[0]
		add_call = dp.ofproto_parser.OFPMeterMod.call_args_list[1]

		assert delete_call.kwargs['command'] == dp.ofproto.OFPMC_DELETE
		assert add_call.kwargs['command'] == dp.ofproto.OFPMC_ADD

	def test_rate_passed_through_unconverted(self, manager):
		dp = _make_datapath()
		manager._replace_meter(dp, meter_id=1, rate_kbps=50_000)

		band_call = dp.ofproto_parser.OFPMeterBandDrop.call_args_list[0]
		assert band_call.kwargs['rate'] == 50_000

	def test_rate_floored_at_one_kbps(self, manager):
		dp = _make_datapath()
		manager._replace_meter(dp, meter_id=1, rate_kbps=0)

		band_call = dp.ofproto_parser.OFPMeterBandDrop.call_args_list[0]
		assert band_call.kwargs['rate'] == 1
