#!/usr/bin/env python3
# infrastructure/controller/run.py
"""
Launches the OS-Ken app manager with the campus controller.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from os_ken.base.app_manager import AppManager

if __name__ == '__main__':
	AppManager.run_apps(['infrastructure.controller.app'])
