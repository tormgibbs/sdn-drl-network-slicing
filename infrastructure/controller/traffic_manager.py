import logging
import threading
from datetime import datetime, timezone

from os_ken.lib import hub

from traffic.runner import TrafficRunner

logger = logging.getLogger(__name__)


class TrafficManager:
	def __init__(self):
		self._runner: TrafficRunner | None = None
		self._running = False
		self._lock = threading.Lock()
		self._last_loop_result: dict | None = None

	def status(self) -> dict:
		with self._lock:
			return {'running': self._running, 'last_loop': self._last_loop_result}

	def start(
		self,
		slices: list[str] | None = None,
		loops: int = 0,
		scenario: str | None = None,
		seed: int | None = None,
	) -> None:
		with self._lock:
			if self._running:
				raise RuntimeError('Traffic generator already running')
			self._running = True

		try:
			runner = TrafficRunner(slices=slices, loops=loops, scenario=scenario, seed=seed)
			runner.setup()
		except Exception:
			with self._lock:
				self._running = False
			raise

		with self._lock:
			self._runner = runner

		hub.spawn(self._run_loop)
		logger.info('TrafficManager: started, slices=%s scenario=%s', slices, scenario)

	def stop(self) -> None:
		with self._lock:
			if not self._running or self._runner is None:
				logger.warning(
					'TrafficManager: stop() called but traffic generator not running'
				)
				return
			self._runner.request_stop()
		logger.info('TrafficManager: stop requested')

	def set_scenario(self, scenario_name: str) -> None:
		with self._lock:
			runner = self._runner
			running = self._running
		if not running or runner is None:
			raise RuntimeError('Traffic generator not running')
		runner.set_scenario(scenario_name)

	def _on_loop_complete(self, loop, scenario_name, results, failed_slices) -> None:
		with self._lock:
			self._last_loop_result = {
				'loop': loop,
				'scenario': scenario_name,
				'results': results,
				'failed_slices': failed_slices,
				'timestamp': datetime.now(timezone.utc).isoformat(),
			}

	def _run_loop(self) -> None:
		try:
			self._runner.run(self._on_loop_complete)
		except Exception:
			logger.exception('TrafficManager: traffic loop crashed')
		finally:
			with self._lock:
				self._running = False
				self._runner = None
			logger.info('TrafficManager: stopped')
