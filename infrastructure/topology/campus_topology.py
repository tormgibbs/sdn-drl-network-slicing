#!/usr/bin/env python3
# infrastructure/topology/campus_topology.py
# Three-tier campus network topology. Core (s1), aggregation (s2, s3), access (ap1-ap5).


import sys
from pathlib import Path

from mininet.log import info, setLogLevel
from mininet.node import OVSSwitch, RemoteController
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.topology.dpid_map import export_dpid_map


def create_topology():
	net = Mininet_wifi(switch=OVSSwitch, controller=None)

	info('*** Adding remote controller\n')
	c0 = net.addController(
		'c0',
		controller=RemoteController,
		ip='127.0.0.1',
		port=6633,
	)

	info('*** Adding core switch\n')
	s1 = net.addSwitch('s1', protocols='OpenFlow13')

	info('*** Adding aggregation switches\n')
	s2 = net.addSwitch('s2', protocols='OpenFlow13')
	s3 = net.addSwitch('s3', protocols='OpenFlow13')

	info('*** Adding access points (one per slice)\n')
	ap1 = net.addAccessPoint(
		'ap1',
		ssid='vle',
		mode='g',
		channel='1',
		protocols='OpenFlow13',
		failMode='secure',
	)
	ap2 = net.addAccessPoint(
		'ap2',
		ssid='student-portal',
		mode='g',
		channel='6',
		protocols='OpenFlow13',
		failMode='secure',
	)
	ap3 = net.addAccessPoint(
		'ap3',
		ssid='admin',
		mode='g',
		channel='11',
		protocols='OpenFlow13',
		failMode='secure',
	)
	ap4 = net.addAccessPoint(
		'ap4',
		ssid='iot',
		mode='g',
		channel='1',
		protocols='OpenFlow13',
		failMode='secure',
	)
	ap5 = net.addAccessPoint(
		'ap5',
		ssid='general',
		mode='g',
		channel='6',
		protocols='OpenFlow13',
		failMode='secure',
	)

	info('*** Adding stations (source + sink per slice)\n')
	# VLE slice stations
	sta1 = net.addStation('sta1', ip='10.0.1.1/24')
	sta2 = net.addStation('sta2', ip='10.0.1.2/24')

	# Student Portal slice stations
	sta3 = net.addStation('sta3', ip='10.0.2.1/24')
	sta4 = net.addStation('sta4', ip='10.0.2.2/24')

	# Admin slice stations
	sta5 = net.addStation('sta5', ip='10.0.3.1/24')
	sta6 = net.addStation('sta6', ip='10.0.3.2/24')

	# IoT slice stations
	sta7 = net.addStation('sta7', ip='10.0.4.1/24')
	sta8 = net.addStation('sta8', ip='10.0.4.2/24')

	# General Traffic slice stations
	sta9 = net.addStation('sta9', ip='10.0.5.1/24')
	sta10 = net.addStation('sta10', ip='10.0.5.2/24')

	info('*** Exporting DPID map\n')
	export_dpid_map([s1, s2, s3, ap1, ap2, ap3, ap4, ap5])

	info('*** Configuring nodes\n')
	net.configureNodes()

	info('*** Creating links\n')
	# core to aggregation
	net.addLink(s1, s2)
	net.addLink(s1, s3)

	# aggregation to access APs
	net.addLink(s2, ap1)
	net.addLink(s2, ap2)
	net.addLink(s2, ap3)
	net.addLink(s3, ap4)
	net.addLink(s3, ap5)

	# stations to APs
	net.addLink(sta1, ap1)
	net.addLink(sta2, ap1)
	net.addLink(sta3, ap2)
	net.addLink(sta4, ap2)
	net.addLink(sta5, ap3)
	net.addLink(sta6, ap3)
	net.addLink(sta7, ap4)
	net.addLink(sta8, ap4)
	net.addLink(sta9, ap5)
	net.addLink(sta10, ap5)

	info('*** Starting network\n')
	net.start()

	info('*** Associating stations\n')
	sta1.cmd('iw dev sta1-wlan0 connect vle')
	sta2.cmd('iw dev sta2-wlan0 connect vle')
	sta3.cmd('iw dev sta3-wlan0 connect student-portal')
	sta4.cmd('iw dev sta4-wlan0 connect student-portal')
	sta5.cmd('iw dev sta5-wlan0 connect admin')
	sta6.cmd('iw dev sta6-wlan0 connect admin')
	sta7.cmd('iw dev sta7-wlan0 connect iot')
	sta8.cmd('iw dev sta8-wlan0 connect iot')
	sta9.cmd('iw dev sta9-wlan0 connect general')
	sta10.cmd('iw dev sta10-wlan0 connect general')

	info('*** Verifying topology\n')
	for node in [s1, s2, s3, ap1, ap2, ap3, ap4, ap5]:
		info(f'    {node.name}: dpid={node.dpid}\n')

	info('*** Topology started successfully\n')
	CLI(net)

	info('*** Stopping network\n')
	net.stop()


if __name__ == '__main__':
	setLogLevel('info')
	create_topology()
