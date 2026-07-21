#!/usr/bin/env python3
"""
Extended soak-style test for CampusSlicingEnv -- runs a full episode with
randomized actions under real traffic load, then verifies reset() recovers
cleanly across an episode boundary. Complements scripts/smoke_test_env.py,
which only proves the pipeline works for a handful of hand-picked steps.
This proves it keeps working under conditions closer to actual PPO training:
sustained operation, an episode-length run, and the terminated->reset boundary.

Requires: live controller + topology + UE tunnels + traffic generator all
already running. Requires passwordless/cached sudo for ovs-ofctl calls.
"""

import re
import subprocess
import sys
import time

import numpy as np
import yaml

from agent.env import CampusSlicingEnv

SLICES_CONFIG_PATH = 'config/slices.yaml'
SEED = 42

SLICE_TO_METER = {
	'vle': ('s2', 1),
	'student_portal': ('s2', 2),
	'admin': ('s2', 3),
	'iot': ('s3', 1),
	'general': ('s3', 2),
}


def dump_meter_rates(switch: str) -> dict[int, int]:
	out = subprocess.run(
		['sudo', 'ovs-ofctl', '-O', 'OpenFlow13', 'dump-meters', switch],
		capture_output=True,
		text=True,
		timeout=10,
		check=True,
	).stdout
	rates = {}
	current_meter = None
	for line in out.splitlines():
		m = re.search(r'meter=(\d+)', line)
		if m:
			current_meter = int(m.group(1))
			continue
		r = re.search(r'rate=(\d+)', line)
		if r and current_meter is not None:
			rates[current_meter] = int(r.group(1))
			current_meter = None
	return rates


def verify_rates_against_ovs(rates_kbps: dict[str, int]) -> list[str]:
	problems = []
	ovs_cache: dict[str, dict[int, int]] = {}
	for name, (switch, meter_id) in SLICE_TO_METER.items():
		if switch not in ovs_cache:
			ovs_cache[switch] = dump_meter_rates(switch)
		ovs_rate = ovs_cache[switch].get(meter_id)
		expected = rates_kbps.get(name)
		if ovs_rate != expected:
			problems.append(
				f'{name}: controller says {expected} kbps, OVS has {ovs_rate} kbps'
			)
	return problems


def run_episode(env: CampusSlicingEnv, rng: np.random.Generator, label: str) -> dict:
	print(f'\n=== {label}: reset() ===')
	t0 = time.monotonic()
	obs, info = env.reset()
	reset_dt = time.monotonic() - t0
	print(f'reset() completed in {reset_dt:.3f}s')

	assert not np.isnan(obs).any(), f'NaN in observation after reset: {obs}'

	step_times = []
	rewards = []
	failures = 0
	drift_events = []

	step_count = 0
	terminated = False
	truncated = False

	while not terminated and not truncated:
		action = rng.normal(loc=0.0, scale=2.0, size=env.n_slices)

		t0 = time.monotonic()
		obs, reward, terminated, truncated, info = env.step(action)
		dt = time.monotonic() - t0
		step_times.append(dt)
		step_count += 1

		if truncated and info.get('failure'):
			failures += 1
			print(f'  [step {step_count}] INFRA FAILURE: {info["failure"]}')
			continue

		rewards.append(reward)

		if np.isnan(obs).any() or np.isinf(obs).any():
			print(f'  [step {step_count}] WARNING: NaN/Inf in observation: {obs}')

		problems = verify_rates_against_ovs(env._current_rates_kbps)
		if problems:
			drift_events.append((step_count, problems))
			print(f'  [step {step_count}] OVS DRIFT: {problems}')

		if step_count % 10 == 0:
			print(
				f'  [step {step_count}] reward={reward:.3f} dt={dt:.2f}s '
				f'terminated={terminated} truncated={truncated}'
			)

	return {
		'label': label,
		'reset_dt': reset_dt,
		'step_count': step_count,
		'step_times': step_times,
		'rewards': rewards,
		'failures': failures,
		'drift_events': drift_events,
		'terminated': terminated,
		'truncated': truncated,
	}


def print_summary(result: dict) -> None:
	st = result['step_times']
	rw = result['rewards']
	print(f'\n--- {result["label"]} summary ---')
	print(f'  steps completed: {result["step_count"]}')
	print(f'  ended via: {"terminated" if result["terminated"] else "truncated"}')
	print(f'  infra failures: {result["failures"]}')
	print(f'  OVS drift events: {len(result["drift_events"])}')
	if st:
		print(
			f'  step time: min={min(st):.2f}s max={max(st):.2f}s mean={sum(st) / len(st):.2f}s'
		)
	if rw:
		print(f'  reward: min={min(rw):.2f} max={max(rw):.2f} mean={sum(rw) / len(rw):.2f}')


def main() -> int:
	with open(SLICES_CONFIG_PATH) as f:
		slices_config = yaml.safe_load(f)

	rng = np.random.default_rng(SEED)
	env = CampusSlicingEnv(
		slices_config=slices_config, ue_profiles=None, episode_length=100
	)

	try:
		result_1 = run_episode(env, rng, 'Episode 1 (full length)')
		print_summary(result_1)

		print('\n=== Verifying reset() recovers cleanly after episode boundary ===')
		result_2 = run_episode_partial(
			env, rng, 'Episode 2 (post-boundary, 10 steps)', n_steps=10
		)
		print_summary(result_2)

		total_failures = result_1['failures'] + result_2['failures']
		total_drift = len(result_1['drift_events']) + len(result_2['drift_events'])

		print('\n=== SOAK TEST RESULT ===')
		if total_failures > 0:
			print(
				f'  {total_failures} infra failure(s) occurred -- review before trusting for training.'
			)
		if total_drift > 0:
			print(
				f'  {total_drift} OVS drift event(s) occurred -- review before trusting for training.'
			)
		if total_failures == 0 and total_drift == 0:
			print(
				'  Clean run: no infra failures, no OVS drift, reset() recovered correctly.'
			)

		return 0

	finally:
		print('\nRestoring equal-split allocation before exit...')
		try:
			env._apply_allocation([0.2, 0.2, 0.2, 0.2, 0.2])
		except Exception as restore_exc:
			print(f'WARNING: failed to restore equal split: {restore_exc}', file=sys.stderr)
		env.close()


def run_episode_partial(
	env: CampusSlicingEnv, rng: np.random.Generator, label: str, n_steps: int
) -> dict:
	print(f'\n=== {label}: reset() ===')
	t0 = time.monotonic()
	obs, info = env.reset()
	reset_dt = time.monotonic() - t0
	print(f'reset() completed in {reset_dt:.3f}s')

	step_times = []
	rewards = []
	failures = 0
	drift_events = []
	terminated = False
	truncated = False

	for step_count in range(1, n_steps + 1):
		action = rng.normal(loc=0.0, scale=2.0, size=env.n_slices)
		t0 = time.monotonic()
		obs, reward, terminated, truncated, info = env.step(action)
		dt = time.monotonic() - t0
		step_times.append(dt)

		if truncated and info.get('failure'):
			failures += 1
			print(f'  [step {step_count}] INFRA FAILURE: {info["failure"]}')
			continue

		rewards.append(reward)
		problems = verify_rates_against_ovs(env._current_rates_kbps)
		if problems:
			drift_events.append((step_count, problems))
			print(f'  [step {step_count}] OVS DRIFT: {problems}')

		print(f'  [step {step_count}] reward={reward:.3f} dt={dt:.2f}s')

		if terminated or truncated:
			break

	return {
		'label': label,
		'reset_dt': reset_dt,
		'step_count': len(step_times),
		'step_times': step_times,
		'rewards': rewards,
		'failures': failures,
		'drift_events': drift_events,
		'terminated': terminated,
		'truncated': truncated,
	}


if __name__ == '__main__':
	sys.exit(main())
