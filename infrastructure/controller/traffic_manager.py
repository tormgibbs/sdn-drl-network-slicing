# infrastructure/controller/traffic_manager.py
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from os_ken.lib import hub

from traffic.runner import TrafficRunner

logger = logging.getLogger(__name__)
_traffic_runner_logger = logging.getLogger('traffic_runner')
_LOG_DIR = Path('logs/traffic')


class TrafficManager:
	def __init__(self):
		self._runner: TrafficRunner | None = None
		self._running = False
		self._lock = threading.Lock()
		self._last_loop_result: dict | None = None
		self._log_handler: logging.Handler | None = None

	def status(self) -> dict:
		with self._lock:
			current_scenario = self._runner.get_current_scenario() if self._runner else None
			return {
				'running': self._running,
				'current_scenario': current_scenario,
				'last_loop': self._last_loop_result,
			}

	def _attach_log_file(self) -> Path:
		_LOG_DIR.mkdir(parents=True, exist_ok=True)
		ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
		log_path = _LOG_DIR / f'traffic_{ts}.log'
		handler = logging.FileHandler(log_path)
		handler.setFormatter(
			logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
		)
		_traffic_runner_logger.addHandler(handler)
		logger.addHandler(handler)
		self._log_handler = handler
		return log_path

	def _detach_log_file(self) -> None:
		if self._log_handler is not None:
			_traffic_runner_logger.removeHandler(self._log_handler)
			logger.removeHandler(self._log_handler)
			self._log_handler.close()
			self._log_handler = None

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
		log_path = self._attach_log_file()
		hub.spawn(self._run_loop)
		logger.info(
			'TrafficManager: started, slices=%s scenario=%s, logging to %s',
			slices,
			scenario,
			log_path,
		)

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
			self._detach_log_file()
