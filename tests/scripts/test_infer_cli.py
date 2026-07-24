# tests/scripts/test_infer_cli.py
import sys

import pytest

import scripts.infer as cli


class FakeRunner:
	def __init__(self, *args, **kwargs):
		self.request_stop_calls = 0
		self.run_called_with = None
		self.closed = False

	def request_stop(self):
		self.request_stop_calls += 1

	def run(self, on_step, max_steps=0):
		self.run_called_with = (on_step, max_steps)

	def close(self):
		self.closed = True


@pytest.fixture
def patch_common(monkeypatch, tmp_path):
	monkeypatch.setattr(cli, 'AgentRunner', FakeRunner)
	monkeypatch.setattr(cli, 'SLICES_CONFIG_PATH', str(tmp_path / 'slices.yaml'))
	(tmp_path / 'slices.yaml').write_text('slices: {}\n')

	registered_handlers = {}
	monkeypatch.setattr(
		cli.signal,
		'signal',
		lambda sig, handler: registered_handlers.setdefault(sig, handler),
	)
	return registered_handlers


def test_sigint_and_sigterm_wired_to_request_stop(monkeypatch, patch_common):
	monkeypatch.setattr(sys, 'argv', ['infer.py', '--model', 'fake_model'])

	cli.main()

	registered = patch_common
	assert cli.signal.SIGINT in registered
	assert cli.signal.SIGTERM in registered


def test_signal_handler_calls_request_stop_not_raises(monkeypatch, patch_common):
	monkeypatch.setattr(sys, 'argv', ['infer.py', '--model', 'fake_model'])

	created = {}
	orig_ctor = FakeRunner.__init__

	def capturing_ctor(self, *args, **kwargs):
		orig_ctor(self, *args, **kwargs)
		created['runner'] = self

	monkeypatch.setattr(FakeRunner, '__init__', capturing_ctor)

	cli.main()

	runner = created['runner']
	registered = patch_common

	registered[cli.signal.SIGINT](cli.signal.SIGINT, None)
	assert runner.request_stop_calls == 1

	registered[cli.signal.SIGTERM](cli.signal.SIGTERM, None)
	assert runner.request_stop_calls == 2


def test_no_bare_except_keyboardinterrupt_remains(monkeypatch, patch_common):
	# Regression guard: KeyboardInterrupt handling was removed in favor of
	# signal.signal()-based cooperative stop. If a real, unrelated exception
	# occurs inside run(), it must propagate, not be silently swallowed.
	class RaisingRunner(FakeRunner):
		def run(self, on_step, max_steps=0):
			raise ValueError('unexpected failure')

	monkeypatch.setattr(cli, 'AgentRunner', RaisingRunner)
	monkeypatch.setattr(sys, 'argv', ['infer.py', '--model', 'fake_model'])

	with pytest.raises(ValueError, match='unexpected failure'):
		cli.main()


def test_close_called_even_on_exception(monkeypatch, patch_common):
	created = {}

	class RaisingRunner(FakeRunner):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			created['runner'] = self

		def run(self, on_step, max_steps=0):
			raise ValueError('boom')

	monkeypatch.setattr(cli, 'AgentRunner', RaisingRunner)
	monkeypatch.setattr(sys, 'argv', ['infer.py', '--model', 'fake_model'])

	with pytest.raises(ValueError):
		cli.main()

	assert created['runner'].closed is True
