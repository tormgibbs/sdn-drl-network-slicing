// frontend/src/hooks/use-slice-view-model.ts

import { formatBps } from "#/lib/format";
import { computeCycleStatus } from "#/lib/slice-cycle-status";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import type { SliceViewConfig } from "#/types/slice-view-config";
import { useLiveSliceData } from "./use-live-slice-data";

export function useSliceViewModel(config: SliceViewConfig) {
	const { key, name, priority, priorityLabel, sla, unitDivisor, unitLabel } =
		config;
	const throughputLabel = config.throughputLabel ?? "THROUGHPUT";
	const latencyLabel = config.latencyLabel ?? "LATENCY";
	const { current, history, slaMet, allocationBps } = useLiveSliceData(
		key,
		sla,
	);
	const trafficStatus = useLiveMetricsStore((s) => s.trafficStatus);

	const continuousResult = trafficStatus?.last_loop?.results.find(
		(r) => r.slice === key && r.component === "continuous",
	);
	const jitterMs =
		continuousResult?.protocol === "udp"
			? (continuousResult.jitter_ms ?? null)
			: null;

	const thrptDisplay = current ? current.tx_throughput_bps / unitDivisor : null;
	const allocDisplay =
		allocationBps !== null ? allocationBps / unitDivisor : null;
	const chartData = history.map((p, i) => ({
		i,
		thrpt: p.tx_throughput_bps / unitDivisor,
		lat: p.latency_ms,
		loss: p.loss_pct,
	}));
	const recentCycles = history
		.slice(-7)
		.reverse()
		.map((p, i) => ({
			id: `${key}-${history.length - i}`,
			thrpt: +(p.tx_throughput_bps / unitDivisor).toFixed(2),
			lat: p.latency_ms,
			status: computeCycleStatus(p, sla),
		}));
	const historyRows = history.slice(-20).map((p, i) => ({
		ts: new Date(p.timestamp).toISOString(),
		id: `${key}-${i}`,
		thrpt: p.tx_throughput_bps / unitDivisor,
		lat: p.latency_ms,
		loss: p.loss_pct,
		alloc: allocDisplay ?? 0,
		sla: computeCycleStatus(p, sla),
	}));

	return {
		chartData,
		historyRows,
		header: {
			name,
			priority,
			slaMet,
			metricChips: current
				? [
						`${thrptDisplay!.toFixed(2)} ${unitLabel}`,
						`${current.latency_ms.toFixed(1)}ms`,
						`${current.loss_pct.toFixed(2)}%`,
					]
				: [`— ${unitLabel}`, "—ms", "—%"],
			slaTargets: `${formatBps(sla.minThrpt)} min\u00a0·\u00a0${sla.maxLat}ms max\u00a0·\u00a0${sla.maxLoss}% max`,
		},
		right: {
			currentState: [
				{
					label: throughputLabel,
					value: current ? `${thrptDisplay!.toFixed(2)} ${unitLabel}` : "—",
				},
				{
					label: latencyLabel,
					value: current ? `${current.latency_ms.toFixed(1)}ms` : "—",
				},
				{
					label: "PACKET LOSS",
					value: current ? `${current.loss_pct.toFixed(2)}%` : "—",
				},
				...(jitterMs !== null
					? [{ label: "JITTER", value: `${jitterMs.toFixed(2)}ms` }]
					: []),
			],
			slaThresholds: [
				{ label: "MIN THRPT", value: formatBps(sla.minThrpt) },
				{ label: "MAX LAT", value: `${sla.maxLat}ms` },
				{ label: "MAX LOSS", value: `${sla.maxLoss}%` },
				{ label: "PRIORITY", value: priorityLabel, highlight: true },
			],
			recentCycles,
			recentCols: config.recentCols,
		},
		allocDisplay,
	};
}
