import pytest

from agent.project_allocation import project_allocation, validate_floors

FLOORS = [50000, 25000, 10000, 64, 5000]
C = 100_000
REMAINDER = C - sum(FLOORS)


class TestInvariants:
	POLICIES = [
		[0.2, 0.2, 0.2, 0.2, 0.2],
		[0.96, 0.01, 0.01, 0.01, 0.01],
		[0.01, 0.01, 0.01, 0.01, 0.96],
		[0.55, 0.28, 0.10, 0.02, 0.05],
		[0.30, 0.25, 0.20, 0.15, 0.10],
		[0.501, 0.249, 0.100, 0.050, 0.100],
	]

	@pytest.mark.parametrize('p', POLICIES)
	def test_sum_equals_capacity(self, p):
		assert sum(project_allocation(p, FLOORS, C)) == C

	@pytest.mark.parametrize('p', POLICIES)
	def test_all_floors_respected(self, p):
		a = project_allocation(p, FLOORS, C)
		for i, (alloc, floor) in enumerate(zip(a, FLOORS)):
			assert alloc >= floor, f'slice {i}: got {alloc} kbps, floor is {floor} kbps'


class TestBehaviour:
	def test_equal_split_clamps_vle_and_portal(self):
		a = project_allocation([0.2, 0.2, 0.2, 0.2, 0.2], FLOORS, C)
		for i, (alloc, floor) in enumerate(zip(a, FLOORS)):
			assert alloc >= floor, f'slice {i}: got {alloc} kbps, floor is {floor} kbps'

	def test_dominant_slice_receives_most_remainder(self):
		a = project_allocation([0.96, 0.01, 0.01, 0.01, 0.01], FLOORS, C)
		assert a[0] > FLOORS[0] + int(REMAINDER * 0.8)

	def test_feasible_input_is_near_identity(self):
		p = [0.55, 0.28, 0.10, 0.02, 0.05]
		raw = [pi * C for pi in p]

		a = project_allocation(p, FLOORS, C)

		for i, (got, expected) in enumerate(zip(a, raw)):
			assert abs(got - expected) <= 5, f'slice {i}: got {got}, expected ~{expected}'

	def test_rounding_correction_never_violates_floor(self):
		# Construct an allocation where one slice sits only slightly above
		# its floor, minimizing its available correction margin.
		p0 = FLOORS[0] / C + 0.001
		leftover = 1.0 - p0

		p = [
			p0,
			leftover * 0.4,
			leftover * 0.3,
			leftover * 0.1,
			leftover * 0.2,
		]

		a = project_allocation(p, FLOORS, C)

		assert sum(a) == C

		for i, (alloc, floor) in enumerate(zip(a, FLOORS)):
			assert alloc >= floor, f'slice {i}: got {alloc}, floor {floor}'


class TestValidation:
	def test_valid_config_passes(self):
		validate_floors(FLOORS, C)

	def test_floors_exceed_capacity(self):
		with pytest.raises(AssertionError, match='floors'):
			validate_floors([50000, 25000, 10000, 10000, 5001], C)

	def test_floors_equal_capacity(self):
		with pytest.raises(AssertionError, match='floors'):
			validate_floors([50000, 25000, 10000, 9936, 5064], C)

	def test_zero_floor_rejected(self):
		with pytest.raises(AssertionError, match='zero floor'):
			validate_floors([50000, 25000, 10000, 0, 5000], C)

	def test_remainder_too_small(self):
		with pytest.raises(AssertionError, match='remainder'):
			validate_floors([50000, 25000, 14990, 64, 9935], C)


class TestEdgeCases:
	def test_all_slices_at_or_below_floor_no_crash(self):
		# Regression: p proportional to floors, with C close to floor_sum,
		# makes every raw allocation <= floor, so total_residual == 0.
		# Previously caused ZeroDivisionError.
		floor_sum = sum(FLOORS)
		tight_c = floor_sum + 100
		p = [f / floor_sum for f in FLOORS]
		a = project_allocation(p, FLOORS, tight_c)
		assert sum(a) == tight_c
		for i, (alloc, floor) in enumerate(zip(a, FLOORS)):
			assert alloc >= floor, f'slice {i}: got {alloc} kbps, floor is {floor} kbps'


	def test_correction_negative_avoids_zero_slack_slice(self):
		# Regression: negative rounding correction must only target a slice
		# with slack > 0, never one already sitting exactly at its floor.
		floors = [10, 10, 10]
		c = 31  # floor_sum=30, remainder=1
		p = [0.0, 0.5, 0.5]

		a = project_allocation(p, floors, c)

		assert sum(a) == c
		for i, (alloc, floor) in enumerate(zip(a, floors)):
			assert alloc >= floor, f'slice {i}: got {alloc}, floor {floor}'
