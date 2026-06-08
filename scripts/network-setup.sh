#!/bin/bash
set -e

echo "[1/7] Configuring bridge netfilter..."
sudo modprobe br_netfilter
sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null

echo "Waiting for OVS bridge s1..."
until sudo ovs-vsctl br-exists s1 2>/dev/null; do sleep 1; done
echo "    s1 ready"

echo "[2/7] Waiting for UPF PFCP listener..."
for i in $(seq 1 30); do
  if docker exec upf ss -lnup 2>/dev/null | grep -q ':8805'; then
    echo "    UPF PFCP listener up"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: UPF PFCP listener did not come up after 60s"
    exit 1
  fi
  sleep 2
done

UPF_MAC=$(docker exec upf ip link show eth0 | awk '/ether/ {print $2}')
if [ -z "$UPF_MAC" ]; then
  echo "ERROR: Could not get UPF MAC from eth0"
  exit 1
fi
echo "    UPF MAC: $UPF_MAC"

echo "[3/7] Adding s1-upf to OVS s1..."
sudo ip link add s1-upf type veth peer name upf-s1 2>/dev/null || true
sudo ip link set s1-upf up
sudo ip link set upf-s1 up
sudo ovs-vsctl --may-exist add-port s1 s1-upf

echo "[4/7] Adding upf-s1 to br-free5gc..."
sudo ip link set upf-s1 master br-free5gc

echo "[5/7] Adding upf-gw internal port..."
sudo ovs-vsctl --may-exist add-port s1 upf-gw \
  -- set Interface upf-gw type=internal \
  -- set Interface upf-gw mac=\"02:00:00:00:0c:00\"
sudo ip addr add 10.100.200.200/24 dev upf-gw 2>&1 || \
  echo "    WARN: upf-gw addr add failed or already exists"
sudo ip link set upf-gw up
sudo ip route add 10.0.0.0/8 dev upf-gw 2>&1 || \
  echo "    WARN: host route add failed or already exists"

echo "[6/7] Configuring UPF container routes..."
docker exec upf ip route add 10.0.0.0/8 via 10.100.200.200 dev eth0 2>&1 || \
  echo "    WARN: UPF route add failed or already exists"

echo "[7/7] Configuring UPF iptables..."
docker exec upf iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || true
docker exec upf iptables -t nat -A POSTROUTING -s 10.60.0.0/16 -o eth0 ! -d 10.0.0.0/8 -j MASQUERADE


echo ""
echo "Network setup complete."
echo "Next: make ue-attach && make ue-setup"
