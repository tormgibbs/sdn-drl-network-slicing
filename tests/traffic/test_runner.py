import threading
import time

import pytest

from traffic.runner import TrafficRunner

FAKE_PROFILES = {
	'vle': {
		'pattern': 'mixed',
		'protocol': 'udp',
		'continuous_bps': 1000,
		'on_off_bps': 2000,
		'downlink_bps': 3000,
		'duration_sec': 1,
	},
	'general': {
		'pattern': 'continuous',
		'protocol': 'udp',
		'target_bps': 500,
		'duration_sec': 1,
	},
}
FAKE_DEFAULTS = {'duration_sec': 1, 'inter_loop_gap_sec': 0}
FAKE_SCENARIOS = {'baseline': {}, 'exam_week': {}}
FAKE_NETWORK = {
	'vle': {
		'tunnel': 'ue1tun0',
		'bind_ip': '10.0.1.1',
		'server_ip': '10.0.1.2',
		'ue_ip': '10.0.1.1',
		'dl_port': 5202,
		'sta': 'sta1',
	},
	'general': {
		'tunnel': 'ue5tun0',
		'bind_ip': '10.0.5.1',
		'server_ip': '10.0.5.2',
		'ue_ip': '10.0.5.1',
		'dl_port': 5210,
		'sta': 'sta9',
	},
}


def _ok_result(name, scen):
	return [{'slice': name, 'component': 'continuous', 'scenario': scen}]


def _failed_result(name, scen):
	return [{'slice': name, 'component': 'continuous', 'scenario': scen, 'error': 'boom'}]


@pytest.fixture
def patch_loaders(monkeypatch):
	monkeypatch.setattr(
		'traffic.runner.load_traffic_config',
		lambda path: (FAKE_PROFILES, FAKE_DEFAULTS, FAKE_SCENARIOS),
	)
	monkeypatch.setattr('traffic.runner.load_slice_network', lambda path: FAKE_NETWORK)


@pytest.fixture
def make_runner(patch_loaders):
	def _make(**kwargs):
		r = TrafficRunner(slices=['vle', 'general'], **kwargs)
		r._slice_pids = {'vle': 101, 'general': 102}
		return r

	return _make


def test_constructor_rejects_unknown_scenario(make_runner):
	with pytest.raises(ValueError):
		make_runner(scenario='nonexistent')


def test_constructor_rejects_no_valid_slices(patch_loaders):
	with pytest.raises(ValueError):
		TrafficRunner(slices=['not_a_real_slice'])


def test_set_scenario_rejects_unknown_scenario(make_runner):
	r = make_runner()
	with pytest.raises(ValueError):
		r.set_scenario('nonexistent')


@pytest.mark.timeout(5)
def test_run_respects_loops_limit(make_runner, monkeypatch):
	calls = []

	def fake_run_slice(name, prof, net, dur, pid, scen, rng):
		return _ok_result(name, scen)

	monkeypatch.setattr('traffic.runner.run_slice', fake_run_slice)

	r = make_runner(loops=3, scenario='baseline')
	completed = []
	r.run(lambda loop, scen, results, failed: completed.append(loop))

	assert completed == [1, 2, 3]


@pytest.mark.timeout(5)
def test_stop_between_loops_prevents_next_loop(make_runner, monkeypatch):
	monkeypatch.setattr(
		'traffic.runner.run_slice',
		lambda name, prof, net, dur, pid, scen, rng: _ok_result(name, scen),
	)

	r = make_runner(loops=0, scenario='baseline')
	completed = []

	def on_complete(loop, scen, results, failed):
		completed.append(loop)
		r.request_stop()

	r.run(on_complete)

	assert completed == [1]


@pytest.mark.timeout(5)
def test_stop_during_inter_loop_gap_returns_promptly(patch_loaders, monkeypatch):
	monkeypatch.setattr(
		'traffic.runner.load_traffic_config',
		lambda path: (
			FAKE_PROFILES,
			{'duration_sec': 1, 'inter_loop_gap_sec': 10},
			FAKE_SCENARIOS,
		),
	)
	monkeypatch.setattr(
		'traffic.runner.run_slice',
		lambda name, prof, net, dur, pid, scen, rng: _ok_result(name, scen),
	)

	r = TrafficRunner(slices=['vle', 'general'], loops=0, scenario='baseline')
	r._slice_pids = {'vle': 101, 'general': 102}

	first_loop_done = threading.Event()

	def on_complete(loop, scen, results, failed):
		first_loop_done.set()

	thread = threading.Thread(target=r.run, args=(on_complete,))
	thread.start()

	assert first_loop_done.wait(timeout=2.0)
	time.sleep(0.05)  # let run() enter the gap wait

	stop_issued = time.monotonic()
	r.request_stop()
	thread.join(timeout=2.0)
	elapsed = time.monotonic() - stop_issued

	assert not thread.is_alive()
	assert elapsed < 1.0  # should return almost immediately, not wait out the 10s gap


@pytest.mark.timeout(5)
def test_set_scenario_takes_effect_next_loop_not_current(make_runner, monkeypatch):
	seen_scenarios = []

	def fake_run_slice(name, prof, net, dur, pid, scen, rng):
		return _ok_result(name, scen)

	monkeypatch.setattr('traffic.runner.run_slice', fake_run_slice)

	r = make_runner(loops=2, scenario='baseline')

	def on_complete(loop, scen, results, failed):
		seen_scenarios.append(scen)
		if loop == 1:
			r.set_scenario('exam_week')

	r.run(on_complete)

	assert seen_scenarios == ['baseline', 'exam_week']


@pytest.mark.timeout(5)
def test_missing_slice_pid_marks_failed_and_skipped(make_runner, monkeypatch):
	calls = []

	def fake_run_slice(name, prof, net, dur, pid, scen, rng):
		calls.append(name)
		return _ok_result(name, scen)

	monkeypatch.setattr('traffic.runner.run_slice', fake_run_slice)

	r = make_runner(loops=1, scenario='baseline')
	r._slice_pids = {'vle': 101}  # 'general' missing

	results_captured = {}

	def on_complete(loop, scen, results, failed):
		results_captured['failed'] = failed

	r.run(on_complete)

	assert calls == ['vle']
	assert results_captured['failed'] == ['general']


@pytest.mark.timeout(5)
def test_on_loop_complete_receives_failed_slices_when_all_fail(
	make_runner, monkeypatch
):
	monkeypatch.setattr(
		'traffic.runner.run_slice',
		lambda name, prof, net, dur, pid, scen, rng: _failed_result(name, scen),
	)

	r = make_runner(loops=1, scenario='baseline')
	captured = {}

	def on_complete(loop, scen, results, failed):
		captured['failed'] = set(failed)
		captured['results'] = results

	r.run(on_complete)

	assert captured['failed'] == {'vle', 'general'}
	assert all('error' in res for res in captured['results'])


def test_setup_lock_blocks_second_instance(patch_loaders, tmp_path):
	lock_path = tmp_path / 'traffic.lock'
	r1 = TrafficRunner(slices=['vle', 'general'], lock_path=lock_path)
	r1._slice_pids = {'vle': 101, 'general': 102}

	orig_setup = TrafficRunner.setup

	def fake_setup(self):
		self._acquire_lock()

	TrafficRunner.setup = fake_setup
	try:
		r1.setup()

		r2 = TrafficRunner(slices=['vle', 'general'], lock_path=lock_path)
		r2._slice_pids = {'vle': 101, 'general': 102}

		with pytest.raises(RuntimeError, match='already running'):
			r2.setup()
	finally:
		TrafficRunner.setup = orig_setup
		r1._release_lock()


def test_lock_released_after_run_completes(patch_loaders, monkeypatch, tmp_path):
	lock_path = tmp_path / 'traffic.lock'
	monkeypatch.setattr(
		'traffic.runner.run_slice',
		lambda name, prof, net, dur, pid, scen, rng: _ok_result(name, scen),
	)

	r1 = TrafficRunner(
		slices=['vle', 'general'], loops=1, scenario='baseline', lock_path=lock_path
	)
	r1._slice_pids = {'vle': 101, 'general': 102}
	r1._acquire_lock()
	r1.run(lambda *a: None)

	r2 = TrafficRunner(slices=['vle', 'general'], lock_path=lock_path)
	r2._acquire_lock()
	r2._release_lock()


def test_lock_released_on_setup_failure(patch_loaders, monkeypatch, tmp_path):
	lock_path = tmp_path / 'traffic.lock'

	def failing_load_slice_pids(path):
		raise RuntimeError('tunnel verification failed')

	monkeypatch.setattr('traffic.runner.load_slice_pids', failing_load_slice_pids)

	r1 = TrafficRunner(slices=['vle', 'general'], lock_path=lock_path)
	with pytest.raises(RuntimeError, match='tunnel verification failed'):
		r1.setup()

	r2 = TrafficRunner(slices=['vle', 'general'], lock_path=lock_path)
	r2._acquire_lock()
	r2._release_lock()
