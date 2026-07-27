import { useState } from "react";
import { initialData } from "#/data/dashboard";
import type { SliceMetricPoint } from "#/stores/live-metrics-store";
import type { SliceKey } from "#/types/slice";
import { MetricChart } from "./metric-chart";
import { TimeRangeToggle } from "./time-range-toggle";
import {
	buildChartWindow,
	buildWindow,
	TIME_RANGE_POINTS,
	type TimeRange,
} from "./use-chart-window";

type PerformanceChartsProps = {
	metricsHistory: Record<SliceKey, SliceMetricPoint[]>;
	totalAggregate: number;
	breachedSlice: SliceKey | undefined;
};

export function PerformanceCharts({
	metricsHistory,
	totalAggregate,
	breachedSlice,
}: PerformanceChartsProps) {
	const [timeRange, setTimeRange] = useState<TimeRange>("1M");
	const pointCount = TIME_RANGE_POINTS[timeRange];

	const throughputData = buildChartWindow(
		metricsHistory,
		pointCount,
		(p) => p.tx_throughput_bps / 1_000_000,
	);
	const latencyData = buildWindow(
		metricsHistory,
		pointCount,
		(p) => p.latency_ms,
	);

	return (
		<div className="flex flex-col gap-4">
			<div className="flex justify-between items-center">
				<p className="text-xl tracking-tight font-medium">
					Performance Metrics
				</p>
				<TimeRangeToggle value={timeRange} onChange={setTimeRange} />
			</div>

			<div className="grid grid-cols-2 gap-4">
				<MetricChart
					title="Throughput Aggregate"
					data={throughputData}
					headerRight={
						<p className="text-sm font-mono font-bold">
							{totalAggregate.toFixed(1)} Mbps
						</p>
					}
				/>
				<MetricChart
					title="Latency Per Slice"
					data={latencyData}
					headerRight={
						breachedSlice && (
							<p className="text-xs font-mono text-[#FB2C36]">
								Alert: {initialData.slices[breachedSlice].name} Breached
							</p>
						)
					}
				/>
			</div>
		</div>
	);
}
