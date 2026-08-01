# agent/heuristic_runner.py

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

import httpx2 as httpx
from websockets.sync.client import connect as ws_connect

logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:8080'
WS_URL = 'ws://localhost:8080/ws/metrics'

_WS_CONNECT_MAX_RETRIES = 10
_WS_CONNECT_RETRY_DELAY_SEC = 1

EQUAL_SPLIT_FRACTION = 0.2

_UTIL_THRESHOLD = 0.80
_STEP_SIZE = 0.005
_MIN_FRACTION = 0.05


class HeuristicStepResult:
	__slots__ = ('timestamp', 'step', 'allocation_kbps', 'triggered', 'done')

	def __init__(self, timestamp, step, allocation_kbps, triggered, done):
		self.timestamp = timestamp
		self.step = step
		self.allocation_kbps = allocation_kbps
		self.triggered = triggered
		self.done = done

	def to_dict(self) -> dict:
		return {
			'timestamp': self.timestamp,
			'step': self.step,
			'allocation_kbps': self.allocation_kbps,
			'triggered': self.triggered,
			'done': self.done,
		}


class HeuristicRunner:
	def __init__(self, slice_order: list[str]):
		self.slice_order = slice_order
		self._fractions = {name: EQUAL_SPLIT_FRACTION for name in slice_order}
		self._http = httpx.Client(base_url=API_BASE_URL)
		self._ws = None
		self._current_rates_kbps: dict[str, int] = {}
		self._stop_requested = False
		self._step_count = 0

	def get_current_allocation(self) -> dict[str, int]:
		return dict(self._current_rates_kbps)

	def request_stop(self) -> None:
		self._stop_requested = True

	def _connect_ws(self) -> None:
		if self._ws is not None:
			self._ws.close()
		last_exc = None
		for attempt in range(_WS_CONNECT_MAX_RETRIES):
			try:
				self._ws = ws_connect(WS_URL)
				return
			except OSError as exc:
				last_exc = exc
				logger.info(
					'HeuristicRunner: WS connect attempt %d/%d failed: %s',
					attempt + 1,
					_WS_CONNECT_MAX_RETRIES,
					exc,
				)
				time.sleep(_WS_CONNECT_RETRY_DELAY_SEC)
		raise RuntimeError(
			f'could not connect to {WS_URL} after {_WS_CONNECT_MAX_RETRIES} attempts'
		) from last_exc

	def _wait_for_stats(self) -> dict:
		raw = self._ws.recv()
		return json.loads(raw)['metrics']

	def _apply_allocation(self) -> dict[str, int]:
		resp = self._http.post('/allocate', json=self._fractions)
		resp.raise_for_status()
		return resp.json()['rates_kbps']

	def _utilisation(self, name: str, metrics: dict) -> float:
		rate_bps = self._current_rates_kbps.get(name, 0) * 1000
		if rate_bps <= 0:
			return 0.0
		return min(metrics[name]['tx_throughput_bps'] / rate_bps, 1.0)

	def _apply_rule(self, metrics: dict) -> list[str]:
		triggered = [
			name
			for name in self.slice_order
			if self._utilisation(name, metrics) > _UTIL_THRESHOLD
		]
		if not triggered:
			return []

		new_fractions = dict(self._fractions)
		untriggered = [n for n in self.slice_order if n not in triggered]

		for name in triggered:
			bump = min(_STEP_SIZE, sum(new_fractions[n] - _MIN_FRACTION for n in untriggered))
			if bump <= 0:
				continue
			new_fractions[name] += bump
			take_pool = sum(new_fractions[n] - _MIN_FRACTION for n in untriggered)
			if take_pool > 0:
				for n in untriggered:
					share = (new_fractions[n] - _MIN_FRACTION) / take_pool
					new_fractions[n] -= bump * share

		total = sum(new_fractions.values())
		self._fractions = {n: v / total for n, v in new_fractions.items()}
		return triggered

	def run(
		self, on_step: Callable[[HeuristicStepResult], None], max_steps: int = 0
	) -> None:
		self._stop_requested = False
		self._connect_ws()
		self._current_rates_kbps = self._apply_allocation()

		while not self._stop_requested:
			metrics = self._wait_for_stats()
			triggered = self._apply_rule(metrics)
			if triggered:
				self._current_rates_kbps = self._apply_allocation()

			self._step_count += 1
			on_step(
				HeuristicStepResult(
					timestamp=datetime.now(timezone.utc).isoformat(),
					step=self._step_count,
					allocation_kbps=dict(self._current_rates_kbps),
					triggered=triggered,
					done=False,
				)
			)
			if max_steps > 0 and self._step_count >= max_steps:
				break

	def close(self) -> None:
		if self._ws is not None:
			self._ws.close()
			self._ws = None
		self._http.close()
