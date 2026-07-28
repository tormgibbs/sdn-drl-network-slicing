import type { SliceSLA } from "#/hooks/use-live-slice-data";

export function computeCycleStatus(
  point: { latency_ms: number; tx_throughput_bps: number; loss_pct: number },
  sla: SliceSLA,
): "MET" | "VIOLATION" {
  const met =
    point.latency_ms <= sla.maxLat &&
    point.tx_throughput_bps >= sla.minThrpt &&
    point.loss_pct <= sla.maxLoss;
  return met ? "MET" : "VIOLATION";
}
