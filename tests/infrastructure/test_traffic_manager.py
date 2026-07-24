# tests/infrastructure/test_traffic_manager.py
import threading
import time

import pytest

from infrastructure.controller.traffic_manager import TrafficManager


class FakeTrafficRunner:
	def __init__(self, **kwargs):
		self.init_kwargs = kwargs
		self._stop = threading.Event()
		self.first_loop_done = threading.Event()
		self.setup_called = threading.Event()
		self.set_scenario_calls = []
		self.loop_count = 0

	def setup(self):
		self.setup_called.set()

	def request_stop(self):
		self._stop.set()

	def set_scenario(self, scenario_name):
		self.set_scenario_calls.append(scenario_name)

	def run(self, on_loop_complete):
		while not self._stop.is_set():
			self.loop_count += 1
			on_loop_complete(self.loop_count, 'baseline', [{'slice': 'vle'}], [])
			self.first_loop_done.set()
			time.sleep(0.01)


@pytest.fixture
def manager(monkeypatch):
	mgr = TrafficManager()
	created = {}

	def fake_ctor(**kwargs):
		r = FakeTrafficRunner(**kwargs)
		created['runner'] = r
		return r

	monkeypatch.setattr(
		'infrastructure.controller.traffic_manager.TrafficRunner', fake_ctor
	)
	mgr._created = created
	yield mgr
	if mgr._runner is not None:
		mgr.stop()
		# graceful drain: give _run_loop a moment to observe the stop
		# and clear state via its finally block.
		deadline = time.monotonic() + 1.0
		while mgr._runner is not None and time.monotonic() < deadline:
			time.sleep(0.01)


@pytest.mark.timeout(5)
def test_start_while_running_raises_and_does_not_spawn_second_loop(manager):
	manager.start(slices=['vle'], scenario='baseline')
	runner = manager._created['runner']
	assert runner.setup_called.wait(timeout=1.0)

	with pytest.raises(RuntimeError):
		manager.start(slices=['vle'], scenario='baseline')

	manager.stop()
	assert manager._created['runner'] is runner


@pytest.mark.timeout(5)
def test_stop_running_resets_state(manager):
	manager.start(slices=['vle'], scenario='baseline')
	runner = manager._created['runner']
	assert runner.first_loop_done.wait(timeout=1.0)

	manager.stop()

	deadline = time.monotonic() + 1.0
	while manager._runner is not None and time.monotonic() < deadline:
		time.sleep(0.01)

	status = manager.status()
	assert status['running'] is False
	assert manager._runner is None


@pytest.mark.timeout(5)
def test_stop_when_not_running_logs_warning_and_does_not_raise(manager, caplog):
	with caplog.at_level('WARNING'):
		manager.stop()
	assert any('not running' in rec.message.lower() for rec in caplog.records)


@pytest.mark.timeout(5)
def test_status_reflects_last_loop_result(manager):
	manager.start(slices=['vle'], scenario='baseline')
	runner = manager._created['runner']
	assert runner.first_loop_done.wait(timeout=1.0)

	status = manager.status()
	assert status['last_loop'] is not None
	assert status['last_loop']['scenario'] == 'baseline'
	assert status['last_loop']['loop'] >= 1

	manager.stop()


@pytest.mark.timeout(5)
def test_start_failure_in_setup_resets_running_state(manager, monkeypatch):
	def failing_ctor(**kwargs):
		class Failing:
			def setup(self):
				raise RuntimeError('tunnel verification failed')

		return Failing()

	monkeypatch.setattr(
		'infrastructure.controller.traffic_manager.TrafficRunner', failing_ctor
	)

	with pytest.raises(RuntimeError, match='tunnel verification failed'):
		manager.start(slices=['vle'], scenario='baseline')

	status = manager.status()
	assert status['running'] is False
	assert manager._runner is None


@pytest.mark.timeout(5)
def test_status_returns_immediately_during_slow_setup(manager, monkeypatch):
	setup_started = threading.Event()
	release_setup = threading.Event()

	def slow_ctor(**kwargs):
		r = FakeTrafficRunner(**kwargs)

		def slow_setup():
			setup_started.set()
			release_setup.wait(timeout=2.0)

		r.setup = slow_setup
		manager._created['runner'] = r
		return r

	monkeypatch.setattr(
		'infrastructure.controller.traffic_manager.TrafficRunner', slow_ctor
	)

	t = threading.Thread(
		target=manager.start, kwargs={'slices': ['vle'], 'scenario': 'baseline'}
	)
	t.start()
	assert setup_started.wait(timeout=1.0)

	status = manager.status()
	assert status['running'] is True

	release_setup.set()
	t.join(timeout=2.0)

	manager.stop()


@pytest.mark.timeout(5)
def test_set_scenario_raises_when_not_running(manager):
	with pytest.raises(RuntimeError, match='not running'):
		manager.set_scenario('exam_week')


@pytest.mark.timeout(5)
def test_set_scenario_delegates_to_runner_when_running(manager):
	manager.start(slices=['vle'], scenario='baseline')
	runner = manager._created['runner']
	assert runner.first_loop_done.wait(timeout=1.0)

	manager.set_scenario('exam_week')

	assert runner.set_scenario_calls == ['exam_week']

	manager.stop()
