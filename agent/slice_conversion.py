# agent/slice_conversion.py


def slice_dict_to_action_array(
	d: dict[str, float], slice_order: list[str]
) -> list[float]:
	assert set(d.keys()) == set(slice_order), (
		f'dict keys do not match slice_order -- d.keys()={sorted(d.keys())}, '
		f'slice_order={slice_order}'
	)
	return [d[name] for name in slice_order]


def action_array_to_slice_dict(
	a: list[float], slice_order: list[str]
) -> dict[str, float]:
	assert len(a) == len(slice_order), (
		f'array length {len(a)} does not match slice_order length {len(slice_order)} '
		f'-- slice_order={slice_order}'
	)
	return dict(zip(slice_order, a))
