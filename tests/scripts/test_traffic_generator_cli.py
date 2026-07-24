# tests/scripts/test_traffic_generator_cli.py
import sys

import pytest

import scripts.traffic_generator as cli

FAKE_SCENARIOS = {'baseline': {}, 'exam_week': {}}


class FakeRunner:
	instances = []

	def __init__(self, **kwargs):
		self.init_kwargs = kwargs
		self.request_stop_calls = 0
		self.setup_called = False
		self.run_called_with = None
		self.on_loop_start_called_with = None
		FakeRunner.instances.append(self)

	def request_stop(self):
		self.request_stop_calls += 1

	def setup(self):
		self.setup_called = True

	def run(self, on_loop_complete, on_loop_start=None):
		self.run_called_with = on_loop_complete
		self.on_loop_start_called_with = on_loop_start


@pytest.fixture(autouse=True)
def patch_common(monkeypatch, tmp_path):
	FakeRunner.instances.clear()
	monkeypatch.setattr(cli, 'load_traffic_config', lambda path: ({}, {}, FAKE_SCENARIOS))
	monkeypatch.setattr(cli, 'TrafficRunner', FakeRunner)
	monkeypatch.setattr(cli, 'LOG_DIR', tmp_path)

	registered_handlers = {}
	monkeypatch.setattr(
		cli.signal,
		'signal',
		lambda sig, handler: registered_handlers.setdefault(sig, handler),
	)
	return registered_handlers


def test_runner_constructed_with_parsed_args(monkeypatch, patch_common):
	monkeypatch.setattr(
		sys,
		'argv',
		[
			'traffic_generator.py',
			'--slices',
			'vle',
			'general',
			'--loops',
			'3',
			'--scenario',
			'baseline',
			'--seed',
			'42',
		],
	)

	cli.main()

	runner = FakeRunner.instances[0]
	assert runner.init_kwargs == {
		'slices': ['vle', 'general'],
		'loops': 3,
		'scenario': 'baseline',
		'seed': 42,
	}


def test_defaults_when_no_args_given(monkeypatch, patch_common):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py'])

	cli.main()

	runner = FakeRunner.instances[0]
	assert runner.init_kwargs == {
		'slices': None,
		'loops': 0,
		'scenario': None,
		'seed': None,
	}


def test_invalid_scenario_rejected_by_argparse(monkeypatch, patch_common, capsys):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py', '--scenario', 'not_real'])

	with pytest.raises(SystemExit):
		cli.main()

	assert not FakeRunner.instances


def test_setup_called_before_run(monkeypatch, patch_common):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py'])

	cli.main()

	runner = FakeRunner.instances[0]
	assert runner.setup_called is True
	assert runner.run_called_with is not None


def test_sigint_and_sigterm_wired_to_request_stop(monkeypatch, patch_common):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py'])

	cli.main()

	runner = FakeRunner.instances[0]
	registered = patch_common

	assert cli.signal.SIGINT in registered
	assert cli.signal.SIGTERM in registered

	registered[cli.signal.SIGINT](cli.signal.SIGINT, None)
	assert runner.request_stop_calls == 1

	registered[cli.signal.SIGTERM](cli.signal.SIGTERM, None)
	assert runner.request_stop_calls == 2


def test_value_error_on_bad_slices_is_caught_cleanly(monkeypatch, patch_common, caplog):
	def raising_ctor(**kwargs):
		raise ValueError('No valid slices specified')

	monkeypatch.setattr(cli, 'TrafficRunner', raising_ctor)
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py', '--slices', 'nonexistent'])

	with caplog.at_level('ERROR'):
		cli.main()  # must not raise

	assert any('No valid slices specified' in rec.message for rec in caplog.records)


def test_on_loop_complete_saves_results_and_logs_failures(
	monkeypatch, patch_common, tmp_path, caplog
):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py'])

	cli.main()

	runner = FakeRunner.instances[0]
	callback = runner.run_called_with

	with caplog.at_level('WARNING'):
		callback(1, 'baseline', [{'slice': 'vle', 'component': 'continuous'}], ['general'])

	saved_files = list(tmp_path.glob('results_*.json'))
	assert len(saved_files) == 1
	assert any('general' in rec.message for rec in caplog.records)


def test_on_loop_complete_skips_save_when_no_results(
	monkeypatch, patch_common, tmp_path
):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py'])

	cli.main()

	runner = FakeRunner.instances[0]
	callback = runner.run_called_with
	callback(1, 'baseline', [], [])

	assert list(tmp_path.glob('results_*.json')) == []


def test_on_loop_start_logs_before_loop_complete(monkeypatch, patch_common, caplog):
	monkeypatch.setattr(sys, 'argv', ['traffic_generator.py'])

	cli.main()

	runner = FakeRunner.instances[0]
	assert runner.on_loop_start_called_with is not None

	on_loop_start = runner.on_loop_start_called_with
	on_loop_complete = runner.run_called_with

	with caplog.at_level('INFO'):
		caplog.clear()
		on_loop_start(1, 'baseline')
		on_loop_complete(1, 'baseline', [], [])

	messages = [r.message for r in caplog.records]
	start_idx = next(
		i for i, m in enumerate(messages) if 'Loop 1 | scenario=baseline' in m
	)
	complete_idx = next(i for i, m in enumerate(messages) if 'Loop 1 complete' in m)
	assert start_idx < complete_idx
