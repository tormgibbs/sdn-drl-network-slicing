#!/usr/bin/env python3
# infrastructure/controller/run.py
"""
Launches the OS-Ken app manager with the campus controller.
"""

import logging
import sys
from pathlib import Path

log_path = Path(__file__).resolve().parents[2] / 'logs' / 'controller.log'
log_path.parent.mkdir(exist_ok=True)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

file_handler = logging.FileHandler(log_path, mode='w')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(file_handler)
root.addHandler(stream_handler)

# Route all Uvicorn output through root logger so file handler captures it.
# log_config=None in start_api_server prevents Uvicorn from overwriting this.
for uvicorn_logger in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
	logging.getLogger(uvicorn_logger).propagate = True

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from os_ken.base.app_manager import AppManager

if __name__ == '__main__':
	AppManager.run_apps(['infrastructure.controller.app', 'scripts.diagnostics.barrier_timing_test'])
