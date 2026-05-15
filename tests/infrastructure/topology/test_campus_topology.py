# tests/infrastructure/topology/test_campus_topology.py
# Unit tests for topology helper functions.

import json
from unittest.mock import MagicMock

from infrastructure.topology.dpid_map import export_dpid_map


def _make_switch(name: str, dpid: str) -> MagicMock:
	sw = MagicMock()
	sw.name = name
	sw.dpid = dpid
	return sw


class TestExportDpidMap:
	def test_writes_correct_json(self, tmp_path):
		switches = [
			_make_switch('s1', '0000000000000001'),
			_make_switch('ap1', '1000000000000001'),
		]
		path = str(tmp_path / 'dpid_map.json')
		export_dpid_map(switches, path)
		result = json.loads(open(path).read())
		assert result['s1'] == 1
		assert result['ap1'] == 1152921504606846977

	def test_all_switches_written(self, tmp_path):
		switches = [
			_make_switch('s1', '0000000000000001'),
			_make_switch('s2', '0000000000000002'),
			_make_switch('s3', '0000000000000003'),
			_make_switch('ap1', '1000000000000001'),
			_make_switch('ap2', '1000000000000002'),
			_make_switch('ap3', '1000000000000003'),
			_make_switch('ap4', '1000000000000004'),
			_make_switch('ap5', '1000000000000005'),
		]
		path = str(tmp_path / 'dpid_map.json')
		export_dpid_map(switches, path)
		result = json.loads(open(path).read())
		assert len(result) == 8

	def test_creates_parent_directory(self, tmp_path):
		switches = [_make_switch('s1', '0000000000000001')]
		path = str(tmp_path / 'subdir' / 'dpid_map.json')
		export_dpid_map(switches, path)
		assert open(path).read() != ''

	def test_dpid_hex_conversion(self, tmp_path):
		switches = [_make_switch('ap5', '1000000000000005')]
		path = str(tmp_path / 'dpid_map.json')
		export_dpid_map(switches, path)
		result = json.loads(open(path).read())
		assert result['ap5'] == 1152921504606846981
