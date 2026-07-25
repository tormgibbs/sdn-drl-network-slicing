# infrastructure/controller/heuristic_manager.py

import logging
import threading

import yaml
from os_ken.lib import hub

from agent.heuristic_runner import HeuristicRunner

logger = logging.getLogger(__name__)

_SLICES_CONFIG_PATH = 'config/slices.yaml'


class HeuristicManager:
	def __init__(self):
		self._runner: HeuristicRunner | None = None
		self._running = False
		self._lock = threading.Lock()
		self._last_result: dict | None = None

	def status(self) -> dict:
		with self._lock:
			return {'running': self._running, 'last_result': self._last_result}

	def start(self) -> None:
		with self._lock:
			if self._running:
				raise RuntimeError('Heuristic already running')
			self._running = True
		try:
			with open(_SLICES_CONFIG_PATH) as f:
				slices_config = yaml.safe_load(f)
			runner = HeuristicRunner(slices_config['slice_order'])
		except Exception:
			with self._lock:
				self._running = False
			raise
		with self._lock:
			self._runner = runner
		hub.spawn(self._run_loop)
		logger.info('HeuristicManager: started')

	def stop(self) -> None:
		with self._lock:
			if not self._running or self._runner is None:
				logger.warning('HeuristicManager: stop() called but heuristic not running')
				return
			self._runner.request_stop()
		logger.info('HeuristicManager: stop requested')

	def _on_step(self, result) -> None:
		with self._lock:
			self._last_result = result.to_dict()

	def _run_loop(self) -> None:
		try:
			self._runner.run(self._on_step, max_steps=0)
		except Exception:
			logger.exception('HeuristicManager: loop crashed')
		finally:
			with self._lock:
				self._running = False
				runner, self._runner = self._runner, None
			if runner is not None:
				runner.close()
			logger.info('HeuristicManager: stopped')
