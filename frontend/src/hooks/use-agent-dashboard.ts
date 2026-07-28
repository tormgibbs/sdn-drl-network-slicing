// frontend/src/hooks/use-agent-dashboard.ts
import { initialData } from "#/data/dashboard";
import { computeSlaStatus } from "#/lib/sla";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import type { SliceKey } from "#/types/slice";

const SLICE_KEYS = Object.keys(initialData.slices) as SliceKey[];

export function useAgentDashboard() {
	const activeController = useLiveMetricsStore((s) => s.activeController);
	const metrics = useLiveMetricsStore((s) => s.metrics);
	const agent = useLiveMetricsStore((s) => s.agent);
	const agentHistory = useLiveMetricsStore((s) => s.agentHistory);
	const heuristic = useLiveMetricsStore((s) => s.heuristic);
	const heuristicHistory = useLiveMetricsStore((s) => s.heuristicHistory);

	const nominalCount = metrics
		? SLICE_KEYS.filter(
				(key) =>
					computeSlaStatus(metrics[key], initialData.slices[key]) === "NOMINAL",
			).length
		: 0;

	const slaSatisfactionPct = metrics
		? (nominalCount / SLICE_KEYS.length) * 100
		: null;

	return {
		activeController,
		sliceKeys: SLICE_KEYS,
		slaSatisfactionPct,
		agent,
		agentHistory,
		heuristic,
		heuristicHistory,
	};
}
