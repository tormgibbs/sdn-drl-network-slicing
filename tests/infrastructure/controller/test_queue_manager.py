# tests/infrastructure/controller/test_queue_manager.py
# Unit tests for queue_manager error paths, subprocess call structure, and config propagation.

import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

import infrastructure.controller.queue_manager as qm

SAMPLE_SLICES = {
	'network': {'total_bandwidth_bps': 100_000_000},
	'slices': {
		'vle': {'ap': 'ap1', 'min_throughput_bps': 10_000_000},
		'student_portal': {'ap': 'ap2', 'min_throughput_bps': 8_000_000},
		'admin': {'ap': 'ap3', 'min_throughput_bps': 5_000_000},
		'iot': {'ap': 'ap4', 'min_throughput_bps': 3_000_000},
		'general': {'ap': 'ap5', 'min_throughput_bps': 5_000_000},
	},
}


@pytest.fixture(autouse=True)
def patch_config(tmp_path, monkeypatch):
	slices_path = tmp_path / 'slices.yaml'
	slices_path.write_text(yaml.dump(SAMPLE_SLICES))
	monkeypatch.setattr(qm, '_SLICES_CONFIG', slices_path)


def _completed(returncode=0, stdout='', stderr=''):
	result = MagicMock()
	result.returncode = returncode
	result.stdout = stdout
	result.stderr = stderr
	return result


class TestUplinkPort:
	def test_returns_eth2_suffix(self):
		assert qm._uplink_port('ap1') == 'ap1-eth2'

	def test_arbitrary_ap_name(self):
		assert qm._uplink_port('ap99') == 'ap99-eth2'


class TestRun:
	def test_returns_stdout_on_success(self):
		with patch('subprocess.run', return_value=_completed(stdout='some-uuid\n')):
			result = qm._run(['ovs-vsctl', 'list', 'QoS'])
		assert result == 'some-uuid'

	def test_logs_error_on_nonzero_returncode(self, caplog):
		with caplog.at_level(
			logging.ERROR, logger='infrastructure.controller.queue_manager'
		):
			with patch(
				'subprocess.run', return_value=_completed(returncode=1, stderr='ovs error')
			):
				with pytest.raises(RuntimeError):
					qm._run(['ovs-vsctl', 'list', 'QoS'])
		assert 'ovs error' in caplog.text

	def test_raises_on_nonzero_by_default(self):
		with patch('subprocess.run', return_value=_completed(returncode=1, stderr='fail')):
			with pytest.raises(RuntimeError, match='ovs-vsctl failed'):
				qm._run(['ovs-vsctl', 'list', 'QoS'])

	def test_no_raise_when_raise_on_error_false(self):
		with patch('subprocess.run', return_value=_completed(returncode=1, stderr='fail')):
			# must not raise
			qm._run(['ovs-vsctl', 'list', 'QoS'], raise_on_error=False)

	def test_invoked_as_list_not_string(self):
		# Guards against shell=True regression: subprocess.run must receive a list.
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm._run(['ovs-vsctl', 'show'])
		args, _ = mock_run.call_args
		assert isinstance(args[0], list)


class TestCreateHtbQueue:
	def test_subprocess_called_as_list(self):
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm.create_htb_queue('ap1')
		args, _ = mock_run.call_args
		assert isinstance(args[0], list)

	def test_min_rate_matches_config(self):
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm.create_htb_queue('ap1')
		cmd = mock_run.call_args[0][0]
		assert any('min-rate=10000000' in arg for arg in cmd)

	def test_max_rate_matches_total_bandwidth(self):
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm.create_htb_queue('ap1')
		cmd = mock_run.call_args[0][0]
		matches = [arg for arg in cmd if 'max-rate=100000000' in arg]
		assert len(matches) == 2

	def test_port_name_derived_from_uplink_port(self):
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm.create_htb_queue('ap1')
		cmd = mock_run.call_args[0][0]
		assert any('ap1-eth2' in arg for arg in cmd)

	def test_missing_config_raises(self, monkeypatch, tmp_path):
		monkeypatch.setattr(qm, '_SLICES_CONFIG', tmp_path / 'nonexistent.yaml')
		with pytest.raises(FileNotFoundError):
			qm.create_htb_queue('ap1')

	def test_unknown_ap_uses_fallback_min_rate(self):
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm.create_htb_queue('ap99')
		cmd = mock_run.call_args[0][0]
		assert any('min-rate=5000000' in arg for arg in cmd)


class TestUpdateHtbQueue:
	def test_returns_early_and_logs_when_qos_uuid_empty(self, caplog):
		with caplog.at_level(
			logging.ERROR, logger='infrastructure.controller.queue_manager'
		):
			with patch('subprocess.run', return_value=_completed(stdout='')):
				qm.update_htb_queue('ap1', 20_000_000)
		assert 'No QoS record' in caplog.text

	def test_returns_early_and_logs_when_queue_uuid_empty(self, caplog):
		# First call (get qos uuid) succeeds, second call (get queue uuid) returns empty.
		responses = [
			_completed(stdout='qos-uuid-abc'),
			_completed(stdout=''),
		]
		with caplog.at_level(
			logging.ERROR, logger='infrastructure.controller.queue_manager'
		):
			with patch('subprocess.run', side_effect=responses):
				qm.update_htb_queue('ap1', 20_000_000)
		assert 'No queue found' in caplog.text

	def test_set_queue_not_called_when_qos_uuid_missing(self):
		with patch('subprocess.run', return_value=_completed(stdout='')) as mock_run:
			qm.update_htb_queue('ap1', 20_000_000)
		# Only one subprocess call: the get QoS uuid call. No set Queue call.
		assert mock_run.call_count == 1

	def test_set_queue_not_called_when_queue_uuid_missing(self):
		responses = [
			_completed(stdout='qos-uuid-abc'),
			_completed(stdout=''),
		]
		with patch('subprocess.run', side_effect=responses) as mock_run:
			qm.update_htb_queue('ap1', 20_000_000)
		assert mock_run.call_count == 2

	def test_set_queue_called_with_correct_max_rate(self):
		responses = [
			_completed(stdout='qos-uuid-abc'),
			_completed(stdout='queue-uuid-xyz'),
			_completed(stdout=''),
		]
		with patch('subprocess.run', side_effect=responses) as mock_run:
			qm.update_htb_queue('ap1', 20_000_000)
		final_cmd = mock_run.call_args[0][0]
		assert any('max-rate=20000000' in arg for arg in final_cmd)
		assert any('queue-uuid-xyz' in arg for arg in final_cmd)


class TestDestroyHtbQueues:
	def test_does_not_raise_on_ovs_error(self):
		with patch('subprocess.run', return_value=_completed(returncode=1, stderr='fail')):
			qm.destroy_htb_queues()

	def test_destroys_qos_and_queue(self):
		with patch('subprocess.run', return_value=_completed()) as mock_run:
			qm.destroy_htb_queues()
		cmds = [c[0][0] for c in mock_run.call_args_list]
		assert any('QoS' in cmd for cmd in cmds)
		assert any('Queue' in cmd for cmd in cmds)
