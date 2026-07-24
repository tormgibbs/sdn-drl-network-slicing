# tests/infrastructure/controller/test_agent_manager.py
import threading
import time

import pytest

from infrastructure.controller.agent_manager import AgentManager


class FakeStepResult:
	def __init__(self, step):
		self.step = step

	def to_dict(self):
		return {'step': self.step, 'reward': 1.0}


class FakeRunner:
	def __init__(self):
		self._stop = threading.Event()
		self.first_step_done = threading.Event()
		self.closed = threading.Event()
		self.close_calls = 0
		self.on_step_calls = 0

	def request_stop(self):
		self._stop.set()

	def run(self, on_step, max_steps):
		step = 0
		while not self._stop.is_set():
			step += 1
			self.on_step_calls += 1
			on_step(FakeStepResult(step))
			self.first_step_done.set()
			time.sleep(0.01)

	def close(self):
		self.close_calls += 1
		self.closed.set()


@pytest.fixture
def manager(monkeypatch):
	mgr = AgentManager()
	created = {}

	def fake_ctor(*args, **kwargs):
		r = FakeRunner()
		created['runner'] = r
		return r

	monkeypatch.setattr('infrastructure.controller.agent_manager.AgentRunner', fake_ctor)
	mgr._created = created
	yield mgr
	if mgr._runner is not None:
		mgr.stop()
		mgr._created['runner'].closed.wait(timeout=1.0)


@pytest.mark.timeout(5)
def test_start_while_running_raises_and_does_not_spawn_second_loop(manager):
	manager.start(model_path='fake', vecnorm_path='fake')
	runner = manager._created['runner']

	with pytest.raises(RuntimeError):
		manager.start(model_path='fake', vecnorm_path='fake')

	manager.stop()
	assert runner.closed.wait(timeout=1.0)
	assert manager._created['runner'] is runner


@pytest.mark.timeout(5)
def test_stop_running_agent_resets_state(manager):
	manager.start(model_path='fake', vecnorm_path='fake')
	runner = manager._created['runner']
	assert runner.first_step_done.wait(timeout=1.0)

	manager.stop()
	assert runner.closed.wait(timeout=1.0)

	status = manager.status()
	assert status['running'] is False
	assert manager._runner is None
	assert runner.close_calls == 1


@pytest.mark.timeout(5)
def test_stop_when_not_running_logs_warning_and_does_not_raise(manager, caplog):
	with caplog.at_level('WARNING'):
		manager.stop()
	assert any('not running' in rec.message.lower() for rec in caplog.records)


@pytest.mark.timeout(5)
def test_status_reflects_last_result_after_on_step(manager):
	manager.start(model_path='fake', vecnorm_path='fake')
	runner = manager._created['runner']
	assert runner.first_step_done.wait(timeout=1.0)

	status = manager.status()
	assert status['last_result'] is not None
	assert status['last_result']['step'] >= 1

	manager.stop()
	assert runner.closed.wait(timeout=1.0)


@pytest.mark.timeout(5)
def test_start_failure_resets_running_state(manager, monkeypatch):
	def failing_ctor(*args, **kwargs):
		raise RuntimeError('model load failed')
	monkeypatch.setattr(
		'infrastructure.controller.agent_manager.AgentRunner', failing_ctor
	)
	with pytest.raises(RuntimeError, match='model load failed'):
		manager.start(model_path='bad', vecnorm_path=None)
	status = manager.status()
	assert status['running'] is False
	assert manager._runner is None


@pytest.mark.timeout(5)
def test_status_returns_immediately_during_slow_construction(manager, monkeypatch):
	construction_started = threading.Event()
	release_construction = threading.Event()

	def slow_ctor(*args, **kwargs):
		construction_started.set()
		release_construction.wait(timeout=2.0)
		r = FakeRunner()
		manager._created['runner'] = r
		return r

	monkeypatch.setattr('infrastructure.controller.agent_manager.AgentRunner', slow_ctor)

	t = threading.Thread(
		target=manager.start, kwargs={'model_path': 'fake', 'vecnorm_path': 'fake'}
	)
	t.start()
	assert construction_started.wait(timeout=1.0)

	status = manager.status()
	assert status['running'] is True

	release_construction.set()
	t.join(timeout=2.0)

	manager.stop()
	manager._created['runner'].closed.wait(timeout=1.0)
