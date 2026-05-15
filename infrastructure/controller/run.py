#!/usr/bin/env python3
# infrastructure/controller/run.py
"""
Launches the OS-Ken app manager with the campus controller.
"""

import logging
import os
import sys

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(__file__))

from os_ken.base.app_manager import AppManager

if __name__ == '__main__':
	AppManager.run_apps(['app'])
