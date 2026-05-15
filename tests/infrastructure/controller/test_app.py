# tests/infrastructure/controller/test_app.py
# Unit tests for app.py config loading functions.

import json

import pytest
import yaml

from infrastructure.controller.app import load_dpid_map, load_ap_vlan_map

SAMPLE_DPID_MAP_JSON = {
	's1': 1,
	's2': 2,
	's3': 3,
	'ap1': 1152921504606846977,
	'ap2': 1152921504606846978,
	'ap3': 1152921504606846979,
	'ap4': 1152921504606846980,
	'ap5': 1152921504606846981,
}

SAMPLE_SLICES_YAML = {
	'slices': {
		'vle': {'ap': 'ap1', 'vlan': 10},
		'student_portal': {'ap': 'ap2', 'vlan': 20},
		'admin': {'ap': 'ap3', 'vlan': 30},
		'iot': {'ap': 'ap4', 'vlan': 40},
		'general': {'ap': 'ap5', 'vlan': 50},
	}
}


@pytest.fixture
def dpid_map_file(tmp_path, monkeypatch):
	path = tmp_path / 'dpid_map.json'
	path.write_text(json.dumps(SAMPLE_DPID_MAP_JSON))
	monkeypatch.setattr('infrastructure.controller.app.DPID_MAP_PATH', str(path))
	return path


@pytest.fixture
def slices_config_file(tmp_path, monkeypatch):
	path = tmp_path / 'slices.yaml'
	path.write_text(yaml.dump(SAMPLE_SLICES_YAML))
	monkeypatch.setattr('infrastructure.controller.app.SLICES_CONFIG_PATH', str(path))
	return path


class TestLoadDpidMap:
	def test_returns_inverted_map(self, dpid_map_file):
		result = load_dpid_map()
		assert result[1] == 's1'
		assert result[1152921504606846977] == 'ap1'
		assert result[1152921504606846981] == 'ap5'

	def test_all_switches_present(self, dpid_map_file):
		result = load_dpid_map()
		assert len(result) == 8

	def test_raises_when_file_missing(self, monkeypatch):
		monkeypatch.setattr(
			'infrastructure.controller.app.DPID_MAP_PATH',
			'/nonexistent/path/dpid_map.json',
		)
		with pytest.raises(RuntimeError, match='DPID map not found'):
			load_dpid_map()

	def test_keys_are_integers(self, dpid_map_file):
		result = load_dpid_map()
		for key in result:
			assert isinstance(key, int)

	def test_values_are_strings(self, dpid_map_file):
		result = load_dpid_map()
		for value in result.values():
			assert isinstance(value, str)


class TestLoadApVlanMap:
	def test_returns_ap_to_vlan_mapping(self, slices_config_file):
		result = load_ap_vlan_map()
		assert result['ap1'] == 10
		assert result['ap5'] == 50

	def test_all_aps_present(self, slices_config_file):
		result = load_ap_vlan_map()
		assert len(result) == 5

	def test_keys_are_ap_names(self, slices_config_file):
		result = load_ap_vlan_map()
		for key in result:
			assert key.startswith('ap')

	def test_values_are_integers(self, slices_config_file):
		result = load_ap_vlan_map()
		for value in result.values():
			assert isinstance(value, int)

	def test_vlan_ids_are_correct(self, slices_config_file):
		result = load_ap_vlan_map()
		expected = {'ap1': 10, 'ap2': 20, 'ap3': 30, 'ap4': 40, 'ap5': 50}
		assert result == expected
