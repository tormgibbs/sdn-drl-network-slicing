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

logger = logging.getLogger(__name__)


class _Registry:
	def __init__(self):
		self._stats_collector = None
		self._meter_manager = None
		self._frozen = False
		self.loop = None
		self.ws_clients = set()

	def register(self, stats_collector, meter_manager) -> None:
		if self._frozen:
			raise RuntimeError('Registry is already frozen')
		self._stats_collector = stats_collector
		self._meter_manager = meter_manager
		self._frozen = True

	def reset(self) -> None:
		self._stats_collector = None
		self._meter_manager = None
		self._frozen = False

	@property
	def stats_collector(self):
		return self._stats_collector

	@property
	def meter_manager(self):
		return self._meter_manager

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
	dead = set()
	for ws in registry.ws_clients:
		try:
			await ws.send_json(data)
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
