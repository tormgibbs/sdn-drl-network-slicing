# infrastructure/controller/rest_api.py
# FastAPI REST API for the SDN controller northbound interface.
# Runs in a separate HubThread via hub.spawn, with its own asyncio event loop.
# Shares state with CampusController through the module-level registry populated
# at controller startup. Registry is frozen after init so reads are safe from
# any thread with no locking required.

import asyncio
import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


class _Registry:
	def __init__(self):
		self._stats_collector = None
		self._meter_manager = None
		self._agent_manager = None
		self._traffic_manager = None
		self._heuristic_manager = None
		self._frozen = False
		self.loop = None
		self.ws_clients = set()

	def register(
		self,
		stats_collector,
		meter_manager,
		agent_manager,
		traffic_manager,
		heuristic_manager,
	) -> None:
		if self._frozen:
			raise RuntimeError('Registry is already frozen')
		self._stats_collector = stats_collector
		self._meter_manager = meter_manager
		self._agent_manager = agent_manager
		self._traffic_manager = traffic_manager
		self._heuristic_manager = heuristic_manager
		self._frozen = True

	def reset(self) -> None:
		self._stats_collector = None
		self._meter_manager = None
		self._agent_manager = None
		self._traffic_manager = None
		self._heuristic_manager = None
		self._frozen = False

	@property
	def heuristic_manager(self):
		return self._heuristic_manager

	@property
	def stats_collector(self):
		return self._stats_collector

	@property
	def meter_manager(self):
		return self._meter_manager

	@property
	def agent_manager(self):
		return self._agent_manager

	@property
	def traffic_manager(self):
		return self._traffic_manager

	@property
	def frozen(self):
		return self._frozen


registry = _Registry()


def _get_stats_collector():
	sc = registry.stats_collector
	if sc is None:
		raise HTTPException(status_code=503, detail='Stats collector not available')
	return sc


def _get_meter_manager():
	mm = registry.meter_manager
	if mm is None:
		raise HTTPException(status_code=503, detail='Meter manager not available')
	return mm


@asynccontextmanager
async def _lifespan(app: FastAPI):
	registry.loop = asyncio.get_running_loop()
	yield
	registry.loop = None


app = FastAPI(
	title='SDN Slicing Controller API',
	description='Northbound REST API for slice metrics and bandwidth allocation',
	version='0.1.0',
	lifespan=_lifespan,
)


app.add_middleware(
	CORSMiddleware,
	allow_origins=['*'],
	allow_methods=['GET', 'POST'],
	allow_headers=['*'],
)


@app.get('/health')
def health():
	return {'status': 'ok', 'registry_frozen': registry.frozen}


@app.websocket('/ws/metrics')
async def ws_metrics(websocket: WebSocket):
	await websocket.accept()
	registry.ws_clients.add(websocket)
	try:
		while True:
			# Connection is push-only; block here until client disconnects.
			await websocket.receive_text()
	except WebSocketDisconnect:
		pass
	finally:
		registry.ws_clients.discard(websocket)


async def broadcast_metrics(data: dict) -> None:
	import datetime as _dt

	am = registry.agent_manager
	agent_status = await run_in_threadpool(am.status) if am is not None else None

	payload = {
		'timestamp': _dt.datetime.now(_dt.timezone.utc).isoformat(),
		'metrics': data,
		'agent': agent_status['last_result']
		if agent_status and agent_status['running']
		else None,
	}

	dead = set()
	for ws in registry.ws_clients:
		try:
			await ws.send_json(payload)
		except Exception:
			dead.add(ws)
	registry.ws_clients -= dead


@app.get('/metrics')
def get_metrics():
	"""
	Per-slice traffic statistics from the last completed polling interval.
	Empty if no switches have connected or no interval has completed yet.
	"""
	sc = _get_stats_collector()
	raw = sc.get_stats()
	return {
		slice_name: {k: v for k, v in metrics.items() if k != 'duration_sec'}
		for slice_name, metrics in raw.items()
	}


@app.post('/allocate')
def allocate(allocations: dict[str, float]):
	"""
	Set per-slice bandwidth fractions on aggregation switches.
	All configured slices must be present and values must sum to 1.0.
	"""
	mm = _get_meter_manager()

	missing = mm.slice_names - set(allocations.keys())
	if missing:
		raise HTTPException(
			status_code=422,
			detail=f'Missing slices: {sorted(missing)}',
		)

	extra = set(allocations.keys()) - mm.slice_names
	if extra:
		raise HTTPException(
			status_code=422,
			detail=f'Unknown slices: {sorted(extra)}',
		)

	total = sum(allocations.values())
	if abs(total - 1.0) > 0.01:
		raise HTTPException(
			status_code=422,
			detail=f'Allocations must sum to 1.0, got {total:.4f}',
		)

	rates_kbps = mm.install_meters(allocations)

	return {'status': 'ok', 'rates_kbps': rates_kbps}


@app.get('/agent/state')
def agent_state():
	am = registry.agent_manager
	if am is None:
		raise HTTPException(status_code=503, detail='Agent manager not available')
	return am.status()


@app.post('/agent/control')
def agent_control(body: dict):
	am = registry.agent_manager
	if am is None:
		raise HTTPException(status_code=503, detail='Agent manager not available')

	action = body.get('action')
	if action == 'start':
		model_path = body.get('model_path')
		if not model_path:
			raise HTTPException(status_code=422, detail='model_path required to start')
		try:
			am.start(model_path, body.get('vecnorm_path'))
		except RuntimeError as exc:
			raise HTTPException(status_code=409, detail=str(exc)) from exc
	elif action == 'stop':
		am.stop()
	else:
		raise HTTPException(status_code=422, detail=f'Unknown action: {action!r}')

	return am.status()


@app.get('/heuristic/state')
def heuristic_state():
	hm = registry.heuristic_manager
	if hm is None:
		raise HTTPException(status_code=503, detail='Heuristic manager not available')
	return hm.status()


@app.post('/heuristic/control')
def heuristic_control(body: dict):
	hm = registry.heuristic_manager
	if hm is None:
		raise HTTPException(status_code=503, detail='Heuristic manager not available')

	action = body.get('action')
	if action == 'start':
		try:
			hm.start()
		except RuntimeError as exc:
			raise HTTPException(status_code=409, detail=str(exc)) from exc
	elif action == 'stop':
		hm.stop()
	else:
		raise HTTPException(status_code=422, detail=f'Unknown action: {action!r}')

	return hm.status()


@app.get('/traffic/state')
def traffic_state():
	tm = registry.traffic_manager
	if tm is None:
		raise HTTPException(status_code=503, detail='Traffic manager not available')
	return tm.status()


@app.post('/traffic/control')
def traffic_control(body: dict):
	tm = registry.traffic_manager
	if tm is None:
		raise HTTPException(status_code=503, detail='Traffic manager not available')

	action = body.get('action')
	if action == 'start':
		try:
			tm.start(
				slices=body.get('slices'),
				loops=body.get('loops', 0),
				scenario=body.get('scenario'),
				seed=body.get('seed'),
			)
		except RuntimeError as exc:
			raise HTTPException(status_code=409, detail=str(exc)) from exc
	elif action == 'stop':
		tm.stop()
	else:
		raise HTTPException(status_code=422, detail=f'Unknown action: {action!r}')

	return tm.status()


@app.post('/traffic/scenario')
def traffic_scenario(body: dict):
	tm = registry.traffic_manager
	if tm is None:
		raise HTTPException(status_code=503, detail='Traffic manager not available')

	scenario_name = body.get('scenario')
	if not scenario_name:
		raise HTTPException(status_code=422, detail='scenario required')

	try:
		tm.set_scenario(scenario_name)
	except (RuntimeError, ValueError) as exc:
		raise HTTPException(status_code=409, detail=str(exc)) from exc

	return tm.status()


def start_api_server(host: str = '0.0.0.0', port: int = 8080) -> None:
	"""Start uvicorn in a daemon thread with its own asyncio event loop."""

	def _run():
		uvicorn.run(
			app,
			host=host,
			port=port,
			loop='asyncio',
			log_level='info',
			log_config=None,
			access_log=False,
		)

	t = threading.Thread(target=_run, daemon=True, name='uvicorn-api')
	t.start()
	logger.info('REST API server starting on http://%s:%d', host, port)
