# infrastructure/controller/agent_manager.py
# Runs AgentRunner in a background hub-spawned thread, controlled via REST.
# hub.spawn = real OS threads here (HUB_TYPE=native), matching StatsCollector.

import logging
import threading

import yaml
from os_ken.lib import hub

from agent.runner import AgentRunner

logger = logging.getLogger(__name__)

_SLICES_CONFIG_PATH = 'config/slices.yaml'


class AgentManager:
	def __init__(self):
		self._runner: AgentRunner | None = None
		self._running = False
		self._lock = threading.Lock()
		self._last_result: dict | None = None
		self._stopped_event = threading.Event()
		self._stopped_event.set()

	def status(self) -> dict:
		with self._lock:
			return {'running': self._running, 'last_result': self._last_result}

	def start(
		self, model_path: str, vecnorm_path: str | None = None, algo: str = 'ppo'
	) -> None:
		with self._lock:
			if self._running:
				raise RuntimeError('Agent already running')
			self._running = True
		self._stopped_event.clear()
		try:
			with open(_SLICES_CONFIG_PATH) as f:
				slices_config = yaml.safe_load(f)
			runner = AgentRunner(slices_config, model_path, vecnorm_path, algo=algo)
		except Exception:
			with self._lock:
				self._running = False
			self._stopped_event.set()
			raise

		with self._lock:
			self._runner = runner

		hub.spawn(self._run_loop)
		logger.info('AgentManager: started, model=%s algo=%s', model_path, algo)

	def stop(self) -> None:
		with self._lock:
			if not self._running or self._runner is None:
				logger.warning('AgentManager: stop() called but agent not running')
				return
			self._runner.request_stop()
		logger.info('AgentManager: stop requested')

	def stop_and_wait(self, timeout: float | None = None) -> bool:
		self.stop()
		return self._stopped_event.wait(timeout)

	def _on_step(self, result) -> None:
		with self._lock:
			self._last_result = result.to_dict()

	def _run_loop(self) -> None:
		try:
			self._runner.run(self._on_step, max_steps=0)
		except Exception:
			logger.exception('AgentManager: inference loop crashed')
		finally:
			with self._lock:
				self._running = False
				runner, self._runner = self._runner, None
			if runner is not None:
				runner.close()
			self._stopped_event.set()
			logger.info('AgentManager: stopped')
