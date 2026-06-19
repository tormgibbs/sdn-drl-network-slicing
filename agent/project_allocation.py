# agent/project_allocation.py

# Action-space floor projection. Operates in integer kbps to match
# the OFPMeterMod enforcement boundary.


def validate_floors(floors_kbps: list[int], C_kbps: int) -> None:
	"""Validate floor configuration at startup."""
	n = len(floors_kbps)

	assert all(f > 0 for f in floors_kbps), (
		'every floor must be positive — a zero floor is likely a bps-to-kbps '
		'truncation error (e.g. int(64_000 / 1_000_000) == 0 for IoT)'
	)

	floor_sum = sum(floors_kbps)

	assert floor_sum < C_kbps, (
		f'sum(floors)={floor_sum} kbps >= C={C_kbps} kbps: '
		'floors leave no room for agent decisions'
	)

	remainder = C_kbps - floor_sum

	assert remainder >= 2 * n + 2, (
		f'remainder={remainder} kbps too small (need >= {2 * n + 2}): '
		'cannot guarantee rounding correction never violates a floor'
	)


def project_allocation(
	p: list[float],
	floors_kbps: list[int],
	C_kbps: int,
) -> list[int]:
	"""Project a softmax allocation onto the feasible floor-constrained simplex.
	Returns integer kbps allocations that sum exactly to C_kbps and respect
	all configured floors.
	"""
	n = len(p)
	floor_sum = sum(floors_kbps)
	remainder = C_kbps - floor_sum
	raw = [pi * C_kbps for pi in p]
	residual = [max(0.0, r - f) for r, f in zip(raw, floors_kbps)]
	total_residual = sum(residual)

	if total_residual == 0.0:
		# Every slice's raw allocation fell at or below its own floor --
		# p carries no usable signal for distributing the remainder.
		# Split evenly rather than picking an implicit priority order.
		a = [round(floors_kbps[i] + remainder / n) for i in range(n)]
	else:
		a = [
			round(floors_kbps[i] + remainder * (residual[i] / total_residual))
			for i in range(n)
		]

	# Per-element rounding may cause the total to differ from C_kbps.
	# Apply the correction to the slice with the largest margin above its
	# floor; validate_floors() guarantees this cannot violate a floor.
	correction = C_kbps - sum(a)
	if correction != 0:
		slack = [a[i] - floors_kbps[i] for i in range(n)]
		if correction > 0:
			target = max(range(n), key=lambda i: slack[i])
		else:
			eligible = [i for i in range(n) if slack[i] > 0]
			assert eligible, (
				f'rounding correction={correction} but no slice has slack above its '
				f'floor (a={a}, floors={floors_kbps}): this means floor_sum >= C_kbps '
				'and validate_floors() should have rejected this configuration — '
				'do not silently breach a floor to balance the sum'
			)
			target = max(eligible, key=lambda i: slack[i])
		a[target] += correction
	return a
