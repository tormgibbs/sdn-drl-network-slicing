import type { SLAStatus, SliceMetrics, SliceSLA } from "@/types/slice";

export function computeSlaStatus(
	metrics: SliceMetrics,
	sla: SliceSLA,
): SLAStatus {
	const { tx_throughput_bps, latency_ms, loss_pct } = metrics;
	const { min_throughput_bps, max_latency_ms, max_loss_pct } = sla;

	// Any threshold breached
	if (tx_throughput_bps < min_throughput_bps) return "VIOLATION";
	if (latency_ms !== null && latency_ms > max_latency_ms) return "VIOLATION";
	if (loss_pct !== null && loss_pct > max_loss_pct) return "VIOLATION";

	// Any metric within 20% of its threshold
	const throughputWarning = min_throughput_bps * 1.2;
	const latencyWarning = max_latency_ms * 0.8;
	const lossWarning = max_loss_pct * 0.8;

	if (tx_throughput_bps < throughputWarning) return "WARNING";
	if (latency_ms !== null && latency_ms > latencyWarning) return "WARNING";
	if (loss_pct !== null && loss_pct > lossWarning) return "WARNING";

	return "NOMINAL";
}
