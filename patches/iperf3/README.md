# iperf3 OWD Patch

Patches iperf3 3.20 to expose `mean_transit_ms` (mean one-way delay) per interval in JSON output on the receiver side.

## What it does
Adds `mean_transit_ms` to each `event:interval` stream object when running in UDP server mode with `--json-stream`. The value is mean one-way delay in milliseconds computed from iperf3's internal per-packet transit time calculation.

## Apply patch
```bash
git clone https://github.com/esnet/iperf.git
cd iperf
git checkout 3.20
patch -p1 < owd-mean-transit.patch
./configure && make -j$(nproc)
```

## Install on VM host
```bash
sudo cp iperf3-owd /usr/bin/iperf3
sudo cp libiperf.so.0 /usr/lib/x86_64-linux-gnu/libiperf.so.0
sudo ldconfig
```
