# tests/infrastructure/controller/test_flow_manager.py
# Unit tests for flow_manager DPID classification, map lookups, and flow rule construction.

from unittest.mock import MagicMock

import pytest

import infrastructure.controller.flow_manager as fm

SAMPLE_DPID_MAP = {
	1: 's1',
	2: 's2',
	3: 's3',
	1152921504606846977: 'ap1',
	1152921504606846978: 'ap2',
	1152921504606846979: 'ap3',
	1152921504606846980: 'ap4',
	1152921504606846981: 'ap5',
}

SAMPLE_VLAN_MAP = {
	'ap1': 10,
	'ap2': 20,
	'ap3': 30,
	'ap4': 40,
	'ap5': 50,
}


@pytest.fixture(autouse=True)
def reset_state():
	fm.reset_state()
	yield
	fm.reset_state()


@pytest.fixture
def loaded_maps(reset_state):
	fm.set_dpid_map(SAMPLE_DPID_MAP)
	fm.set_ap_vlan_map(SAMPLE_VLAN_MAP)


class TestDpidClassification:
	def test_set_dpid_map_classifies_core(self, loaded_maps):
		assert fm.is_core(1) is True

	def test_set_dpid_map_classifies_aggregation(self, loaded_maps):
		assert fm.is_aggregation(2) is True
		assert fm.is_aggregation(3) is True

	def test_set_dpid_map_classifies_aps(self, loaded_maps):
		for dpid in [
			1152921504606846977,
			1152921504606846978,
			1152921504606846979,
			1152921504606846980,
			1152921504606846981,
		]:
			assert fm.is_ap(dpid) is True

	def test_unknown_dpid_is_not_core(self, loaded_maps):
		assert fm.is_core(999) is False

	def test_unknown_dpid_is_not_aggregation(self, loaded_maps):
		assert fm.is_aggregation(999) is False

	def test_unknown_dpid_is_not_ap(self, loaded_maps):
		assert fm.is_ap(999) is False

	def test_core_is_not_aggregation(self, loaded_maps):
		assert fm.is_aggregation(1) is False

	def test_aggregation_is_not_core(self, loaded_maps):
		assert fm.is_core(2) is False


class TestApNameLookup:
	def test_get_ap_name_returns_correct_name(self, loaded_maps):
		assert fm.get_ap_name(1152921504606846977) == 'ap1'
		assert fm.get_ap_name(1152921504606846981) == 'ap5'

	def test_get_ap_name_returns_none_for_unknown(self, loaded_maps):
		assert fm.get_ap_name(999) is None

	def test_get_ap_name_returns_none_for_core(self, loaded_maps):
		assert fm.get_ap_name(1) is None


class TestVlanLookup:
	def test_get_ap_vlan_returns_correct_vlan(self, loaded_maps):
		assert fm.get_ap_vlan('ap1') == 10
		assert fm.get_ap_vlan('ap5') == 50

	def test_get_ap_vlan_returns_none_for_unknown(self, loaded_maps):
		assert fm.get_ap_vlan('ap99') is None

	def test_get_ap_vlan_returns_none_before_map_loaded(self):
		assert fm.get_ap_vlan('ap1') is None


class TestFlowInstallation:
	def _make_datapath(self, dpid=1152921504606846977):
		dp = MagicMock()
		dp.id = dpid
		dp.ofproto.OFPVID_PRESENT = 0x1000
		dp.ofproto.OFPIT_APPLY_ACTIONS = 4
		dp.ofproto.OFPP_FLOOD = 0xFFFFFFFB
		return dp

	def test_install_ap_rules_sends_two_flows(self, loaded_maps):
		dp = self._make_datapath()
		fm.install_ap_rules(dp, 'ap1', 10)
		assert dp.send_msg.call_count == 2

	def test_install_aggregation_rules_sends_one_flow(self, loaded_maps):
		dp = self._make_datapath(dpid=2)
		fm.install_aggregation_rules(dp)
		assert dp.send_msg.call_count == 1

	def test_install_core_rules_sends_one_flow(self, loaded_maps):
		dp = self._make_datapath(dpid=1)
		fm.install_core_rules(dp)
		assert dp.send_msg.call_count == 1

	def test_install_table_miss_sends_one_flow(self, loaded_maps):
		dp = self._make_datapath()
		fm.install_table_miss(dp)
		assert dp.send_msg.call_count == 1
