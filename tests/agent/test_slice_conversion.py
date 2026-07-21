# tests/agent/test_slice_conversion.py

import pytest

from agent.slice_conversion import (
	action_array_to_slice_dict,
	slice_dict_to_action_array,
)

SLICE_ORDER = ['iot', 'vle', 'general', 'admin', 'student_portal']


class TestSliceDictToActionArray:
	def test_array_reflects_slice_order_not_insertion_order(self):
		d = {
			'vle': 1.0,
			'student_portal': 2.0,
			'admin': 3.0,
			'iot': 4.0,
			'general': 5.0,
		}
		result = slice_dict_to_action_array(d, SLICE_ORDER)
		assert result == [4.0, 1.0, 5.0, 3.0, 2.0]

	def test_mismatched_keys_raises(self):
		d = {
			'vle': 1.0,
			'student_portal': 2.0,
			'admin': 3.0,
			'iot': 4.0,
		}
		with pytest.raises(AssertionError):
			slice_dict_to_action_array(d, SLICE_ORDER)

	def test_extra_key_raises(self):
		d = {
			'vle': 1.0,
			'student_portal': 2.0,
			'admin': 3.0,
			'iot': 4.0,
			'general': 5.0,
			'extra': 6.0,
		}
		with pytest.raises(AssertionError):
			slice_dict_to_action_array(d, SLICE_ORDER)


class TestActionArrayToSliceDict:
	def test_dict_reflects_slice_order_not_array_position_assumption(self):
		a = [4.0, 1.0, 5.0, 3.0, 2.0]
		result = action_array_to_slice_dict(a, SLICE_ORDER)
		assert result == {
			'iot': 4.0,
			'vle': 1.0,
			'general': 5.0,
			'admin': 3.0,
			'student_portal': 2.0,
		}

	def test_wrong_length_raises(self):
		a = [1.0, 2.0, 3.0]
		with pytest.raises(AssertionError):
			action_array_to_slice_dict(a, SLICE_ORDER)


class TestRoundTrip:
	def test_dict_array_dict_is_identity(self):
		original = {
			'vle': 0.5,
			'student_portal': 0.2,
			'admin': 0.15,
			'iot': 0.05,
			'general': 0.1,
		}
		arr = slice_dict_to_action_array(original, SLICE_ORDER)
		back = action_array_to_slice_dict(arr, SLICE_ORDER)
		assert back == original
