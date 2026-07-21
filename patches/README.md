# Patches

## gtp5g-kernel7-gcp.patch
Fixes gtp5g build against GCP's kernel 7.0.0-1007-gcp (kernel API changes
not yet reflected in upstream gtp5g as of this session):
- struct flowi4: flowi4_tos renamed to flowi4_dscp (requires
  inet_dsfield_to_dscp() conversion), two occurrences in src/gtpu/pktinfo.c
- proto_ops connect callback: sockaddr* parameter type changed to
  sockaddr_unsized*; switched to the kernel_connect() helper instead of
  calling ->ops->connect() directly, in src/pfcp/pdr.c

Apply against a fresh gtp5g clone with:
  cd gtp5g && patch -p1 < ../sdn-drl-network-slicing/patches/gtp5g-kernel7-gcp.patch
