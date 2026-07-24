# tests/agent/test_env_ws_reconnect_integration.py
import socket
import threading
import time

import pytest

from agent.env import CampusSlicingEnv


def _free_port() -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind(('127.0.0.1', 0))
		return s.getsockname()[1]


def _make_env():
	slices_config = {
		'slice_order': ['vle'],
		'slices': {
			'vle': {'min_throughput_bps': 5_000_000, 'priority': 5, 'max_latency_ms': 100},
		},
		'network': {'total_bandwidth_bps': 100_000_000},
	}
	return CampusSlicingEnv(slices_config=slices_config)


def test_connect_ws_retries_until_listener_appears(monkeypatch, caplog):
	port = _free_port()
	monkeypatch.setattr('agent.env.WS_URL', f'ws://127.0.0.1:{port}')

	listener_ready = threading.Event()

	def delayed_listener():
		listener_ready.wait()
		srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		srv.bind(('127.0.0.1', port))
		srv.listen(1)
		conn, _ = srv.accept()
		conn.close()
		srv.close()

	threading.Thread(target=delayed_listener, daemon=True).start()

	env = _make_env()

	def release_listener_after_delay():
		time.sleep(2)
		listener_ready.set()

	threading.Thread(target=release_listener_after_delay, daemon=True).start()

	start = time.monotonic()
	with caplog.at_level('INFO', logger='agent.env'):
		with pytest.raises(Exception):
			env._connect_ws()
	elapsed = time.monotonic() - start

	assert elapsed >= 2.0, 'connect succeeded too fast -- retry loop likely not engaging'

	retry_log_lines = [r for r in caplog.records if 'WS connect attempt' in r.message]
	assert len(retry_log_lines) >= 2, (
		f'expected multiple retry attempts logged, got {len(retry_log_lines)}'
	)
