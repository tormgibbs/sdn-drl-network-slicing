#!/usr/bin/env python3
"""
Live smoke test for CampusSlicingEnv against the real controller/OVS stack.
Not a training run -- proves the env<->controller<->OVS<->WS pipeline works
with real numbers. Verifies constraints (floors, capacity, OVS agreement),
not hardcoded rate predictions, since project_allocation()'s exact output
for a given input is an implementation detail this script should not assume.

Requires: live controller + topology + UE tunnels already up (confirmed
earlier this session). Requires passwordless/cached sudo for ovs-ofctl calls.
"""

import re
import subprocess
import sys
import time

import numpy as np
import yaml

from agent.env import CampusSlicingEnv

SLICES_CONFIG_PATH = 'config/slices.yaml'

# Validated this session via live ovs-ofctl output -- not re-derived here.
SLICE_TO_METER = {
	'vle': ('s2', 1),
	'student_portal': ('s2', 2),
	'admin': ('s2', 3),
	'iot': ('s3', 1),
	'general': ('s3', 2),
}


def dump_meter_rates(switch: str) -> dict[int, int]:
	"""Return {meter_id: rate_kbps} from live OVS state on `switch`."""
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


def verify_rates_against_ovs(
	rates_kbps: dict[str, int], floors_kbps: dict[str, int], total_kbps: int
) -> None:
	total = sum(rates_kbps.values())
	assert total <= total_kbps, (
		f'installed rates sum to {total} kbps, exceeds link capacity {total_kbps} kbps'
	)
	for name, rate in rates_kbps.items():
		floor = floors_kbps[name]
		assert rate >= floor, (
			f'slice {name!r} installed at {rate} kbps, below floor {floor} kbps'
		)

	ovs_cache: dict[str, dict[int, int]] = {}
	for name, (switch, meter_id) in SLICE_TO_METER.items():
		if switch not in ovs_cache:
			ovs_cache[switch] = dump_meter_rates(switch)
		ovs_rate = ovs_cache[switch].get(meter_id)
		assert ovs_rate is not None, (
			f'no meter_id={meter_id} found in live OVS state on {switch}'
		)
		expected = rates_kbps[name]
		assert ovs_rate == expected, (
			f'DRIFT: slice {name!r} -- controller reported {expected} kbps, '
			f'OVS actually has {ovs_rate} kbps on {switch} meter={meter_id}'
		)
	print('  OVS cross-check: all installed rates match controller response.')


def run_step(
	env: CampusSlicingEnv,
	label: str,
	action: np.ndarray,
	floors_kbps: dict[str, int],
	total_kbps: int,
) -> None:
	print(f'\n--- step: {label} ---')
	print(f'  raw logits: {action.tolist()}')
	t0 = time.monotonic()
	obs, reward, terminated, truncated, info = env.step(action)
	dt = time.monotonic() - t0
	print(f'  step() completed in {dt:.3f}s')

	if truncated and info.get('failure'):
		raise RuntimeError(f'step() reported infra failure: {info["failure"]}')

	assert obs.shape == (env.n_slices * 3,), f'unexpected obs shape: {obs.shape}'
	assert not np.isnan(obs).any(), f'NaN in observation: {obs}'
	assert not np.isinf(obs).any(), f'Inf in observation: {obs}'

	print(f'  reward={reward:.4f} terminated={terminated} truncated={truncated}')
	print(f'  installed rates_kbps: {env._current_rates_kbps}')
	verify_rates_against_ovs(env._current_rates_kbps, floors_kbps, total_kbps)


def main() -> int:
	with open(SLICES_CONFIG_PATH) as f:
		slices_config = yaml.safe_load(f)

	slice_order = slices_config['slice_order']
	floors_kbps = {
		name: slices_config['slices'][name]['min_throughput_bps'] // 1000
		for name in slice_order
	}
	total_kbps = slices_config['network']['total_bandwidth_bps'] // 1000

	env = CampusSlicingEnv(
		slices_config=slices_config, ue_profiles=None, episode_length=100
	)

	try:
		print('=== reset() ===')
		t0 = time.monotonic()
		obs, info = env.reset()
		dt = time.monotonic() - t0
		print(f'reset() completed in {dt:.3f}s')
		assert obs.shape == (env.n_slices * 3,), f'unexpected obs shape: {obs.shape}'
		assert not np.isnan(obs).any(), f'NaN in observation after reset: {obs}'
		print(f'initial obs: {obs}')
		print(f'initial rates_kbps: {env._current_rates_kbps}')
		verify_rates_against_ovs(env._current_rates_kbps, floors_kbps, total_kbps)

		n = env.n_slices
		idx = {name: i for i, name in enumerate(slice_order)}

		# Fixed, hand-chosen actions -- not random. Each tests a distinct case.
		equal = np.zeros(n)

		skew_general = np.full(n, -2.0)
		skew_general[idx['general']] = 6.0

		skew_vle = np.full(n, -2.0)
		skew_vle[idx['vle']] = 6.0

		run_step(env, 'equal (baseline)', equal, floors_kbps, total_kbps)
		run_step(
			env,
			'skew toward general (tests floor holds for others)',
			skew_general,
			floors_kbps,
			total_kbps,
		)
		run_step(
			env,
			'skew toward vle (tests floor holds for others)',
			skew_vle,
			floors_kbps,
			total_kbps,
		)

		print('\n=== SMOKE TEST PASSED ===')
		return 0

	except Exception as exc:
		print(f'\n=== SMOKE TEST FAILED: {exc} ===', file=sys.stderr)
		raise

	finally:
		print('\nRestoring equal-split allocation before exit...')
		try:
			env._apply_allocation([0.2, 0.2, 0.2, 0.2, 0.2])
		except Exception as restore_exc:
			print(f'WARNING: failed to restore equal split: {restore_exc}', file=sys.stderr)
		env.close()


if __name__ == '__main__':
	sys.exit(main())
