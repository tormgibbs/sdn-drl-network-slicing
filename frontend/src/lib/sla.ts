import type { SlaStatus, SliceMetrics, SliceSLA } from "@/types/slice";

export function computeSlaStatus(
	metrics: SliceMetrics,
	sla: SliceSLA,
): SlaStatus {
	const { tx_throughput_bps, latency_ms, loss_pct } = metrics;
	const { min_throughput_bps, max_latency_ms, max_loss_pct } = sla;

	// Any threshold breached
	if (tx_throughput_bps < min_throughput_bps) return "violated";
	if (latency_ms !== null && latency_ms > max_latency_ms) return "violated";
	if (loss_pct !== null && loss_pct > max_loss_pct) return "violated";

	// Any metric within 20% of its threshold
	const throughputWarning = min_throughput_bps * 1.2;
	const latencyWarning = max_latency_ms * 0.8;
	const lossWarning = max_loss_pct * 0.8;

	if (tx_throughput_bps < throughputWarning) return "warning";
	if (latency_ms !== null && latency_ms > latencyWarning) return "warning";
	if (loss_pct !== null && loss_pct > lossWarning) return "warning";

	return "met";
}
