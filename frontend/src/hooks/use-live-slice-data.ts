// frontend/src/hooks/use-live-slice-data.ts
import { useShallow } from "zustand/react/shallow";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import type { SliceKey } from "#/types/slice";

export interface SliceSLA {
	minThrpt: number; // bps — matches backend units directly, no Mbps conversion here
	maxLat: number; // ms
	maxLoss: number; // percent
}

export function useLiveSliceData(sliceKey: SliceKey, sla: SliceSLA) {
	const current = useLiveMetricsStore(
		useShallow((s) => s.metrics?.[sliceKey] ?? null),
	);
	const history = useLiveMetricsStore((s) => s.metricsHistory[sliceKey]);
	const agent = useLiveMetricsStore((s) => s.agent);

	const slaMet =
		current !== null
			? current.latency_ms <= sla.maxLat &&
				current.tx_throughput_bps >= sla.minThrpt &&
				current.loss_pct <= sla.maxLoss
			: null; // no data received yet — genuinely unknown, not "met"

	const allocationBps =
		agent?.allocation_kbps[sliceKey] != null
			? agent.allocation_kbps[sliceKey] * 1000
			: null;

	return { current, history, slaMet, allocationBps };
}
