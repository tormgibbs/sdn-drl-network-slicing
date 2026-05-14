#!/usr/bin/env python3
"""
Campus network topology - three-tier with wireless access points and stations.
Core (s1) -> Aggregation (s2, s3) -> Access APs (ap1-ap5)
Two stations per AP: src (traffic source) and sink (traffic sink)
"""

from mininet.log import info, setLogLevel
from mininet.node import OVSSwitch, RemoteController
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


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
		failMode='managed',
	)
	ap2 = net.addAccessPoint(
		'ap2',
		ssid='student-portal',
		mode='g',
		channel='6',
		protocols='OpenFlow13',
		failMode='managed',
	)
	ap3 = net.addAccessPoint(
		'ap3',
		ssid='admin',
		mode='g',
		channel='11',
		protocols='OpenFlow13',
		failMode='managed',
	)
	ap4 = net.addAccessPoint(
		'ap4',
		ssid='iot',
		mode='g',
		channel='1',
		protocols='OpenFlow13',
		failMode='managed',
	)
	ap5 = net.addAccessPoint(
		'ap5',
		ssid='general',
		mode='g',
		channel='6',
		protocols='OpenFlow13',
		failMode='managed',
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
	net.build()
	c0.start()
	s1.start([c0])
	s2.start([c0])
	s3.start([c0])
	ap1.start([c0])
	ap2.start([c0])
	ap3.start([c0])
	ap4.start([c0])
	ap5.start([c0])

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
