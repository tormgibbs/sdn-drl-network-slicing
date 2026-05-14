#!/usr/bin/env python3
"""
Campus network topology - three-tier wired backbone.
Core (s1) -> Aggregation (s2, s3) -> Access (s4-s8)
"""

from mininet.log import info, setLogLevel
from mininet.node import OVSSwitch, RemoteController
from mn_wifi.cli import CLI
from mn_wifi.link import WirelessLink
from mn_wifi.net import Mininet_wifi


def create_topology():
    net = Mininet_wifi(switch=OVSSwitch, link=WirelessLink, controller=None)

    info("*** Adding remote controller\n")
    c0 = net.addController(
        "c0",
        controller=RemoteController,
        ip="127.0.0.1",
        port=6633,
    )

    info("*** Adding core switch\n")
    s1 = net.addSwitch("s1", protocols="OpenFlow13")

    info("*** Adding aggregation switches\n")
    s2 = net.addSwitch("s2", protocols="OpenFlow13")
    s3 = net.addSwitch("s3", protocols="OpenFlow13")

    info("*** Adding access switches\n")
    s4 = net.addSwitch("s4", protocols="OpenFlow13")
    s5 = net.addSwitch("s5", protocols="OpenFlow13")
    s6 = net.addSwitch("s6", protocols="OpenFlow13")
    s7 = net.addSwitch("s7", protocols="OpenFlow13")
    s8 = net.addSwitch("s8", protocols="OpenFlow13")

    info("*** Creating links\n")
    net.addLink(s1, s2)
    net.addLink(s1, s3)
    net.addLink(s2, s4)
    net.addLink(s2, s5)
    net.addLink(s2, s6)
    net.addLink(s3, s7)
    net.addLink(s3, s8)

    info("*** Starting network\n")
    net.start()

    info("*** Verifying switch connections\n")
    for sw in [s1, s2, s3, s4, s5, s6, s7, s8]:
        info(f"    {sw.name}: dpid={sw.dpid}\n")

    info("*** Topology started successfully\n")
    info("*** Press Ctrl+C or type 'exit' to stop\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    create_topology()
