# infrastructure/controller/queue_manager.py
# Creates and updates HTB QoS queues on AP uplink ports via ovs-vsctl.
import logging
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_SLICES_CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'slices.yaml'


def _load_config() -> tuple[int, dict[str, int]]:
	with open(_SLICES_CONFIG) as f:
		config = yaml.safe_load(f)
	total_bw = config['network']['total_bandwidth_bps']
	min_rates = {
		slice_cfg['ap']: slice_cfg['min_throughput_bps']
		for slice_cfg in config['slices'].values()
	}
	return total_bw, min_rates


def _uplink_port(ap_name: str) -> str:
	return f'{ap_name}-eth2'


def _run(cmd: str) -> str:
	result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
	if result.returncode != 0:
		logger.error('ovs-vsctl error: %s', result.stderr.strip())
	return result.stdout.strip()


def create_htb_queue(ap_name: str) -> None:
	total_bw, min_rates = _load_config()
	port = _uplink_port(ap_name)
	min_bps = min_rates.get(ap_name, 5_000_000)
	_run(
		f'ovs-vsctl -- --id=@qos create QoS type=linux-htb '
		f'other-config:max-rate={total_bw} '
		f'queues:1=@q1 '
		f'-- --id=@q1 create Queue '
		f'other-config:min-rate={min_bps} '
		f'other-config:max-rate={total_bw} '
		f'-- set Port {port} qos=@qos'
	)
	logger.info('HTB queue created: ap=%s port=%s min=%s bps', ap_name, port, min_bps)


def update_htb_queue(ap_name: str, max_rate_bps: int) -> None:
	port = _uplink_port(ap_name)
	qos_uuid = _run(f'ovs-vsctl get Port {port} qos').strip('[]"\n ')
	if not qos_uuid:
		logger.error('No QoS record found for port %s', port)
		return
	queue_uuid = _run(f'ovs-vsctl get QoS {qos_uuid} queues:1').strip('[]"\n ')
	if not queue_uuid:
		logger.error('No queue found in QoS record for port %s', port)
		return
	_run(f'ovs-vsctl set Queue {queue_uuid} other-config:max-rate={max_rate_bps}')
	logger.info('HTB queue updated: ap=%s max=%s bps', ap_name, max_rate_bps)


def destroy_htb_queues() -> None:
	_run('ovs-vsctl --all destroy QoS')
	_run('ovs-vsctl --all destroy Queue')
	logger.info('All HTB queues destroyed')
