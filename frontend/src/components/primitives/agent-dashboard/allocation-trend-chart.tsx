// frontend/src/components/primitives/agent-dashboard/allocation-trend-chart.tsx
import {
	CartesianGrid,
	Line,
	LineChart,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import type { SliceKey } from "#/types/slice";
import { ChartPanel } from "../slice-dashboard/chartpanel";

const SLICE_COLORS: Record<SliceKey, string> = {
	vle: "var(--chart-1)",
	student_portal: "var(--chart-2)",
	admin: "var(--chart-3)",
	iot: "var(--chart-4)",
	general: "var(--chart-5)",
};

export function AllocationTrendChart({
	history,
	sliceKeys,
}: {
	history: Array<{ i: number; allocation_kbps: Record<string, number> }>;
	sliceKeys: SliceKey[];
}) {
	const data = history.map((p) => ({
		i: p.i,
		...Object.fromEntries(
			sliceKeys.map((key) => [key, (p.allocation_kbps[key] ?? 0) / 1000]),
		),
	}));

	return (
		<ChartPanel title="Allocation Trend (Mbps)">
			<LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
				<CartesianGrid stroke="var(--motif-line)" vertical={false} />
				<XAxis dataKey="i" hide />
				<YAxis
					tick={{
						fontFamily: "var(--font-mono)",
						fontSize: 10,
						fill: "var(--muted-foreground)",
					}}
					tickLine={false}
					axisLine={false}
					width={32}
				/>
				<Tooltip
					contentStyle={{
						background: "var(--card)",
						border: "1px solid var(--border)",
						fontFamily: "var(--font-mono)",
						fontSize: 11,
					}}
				/>
				{sliceKeys.map((key) => (
					<Line
						key={key}
						type="monotone"
						dataKey={key}
						stroke={SLICE_COLORS[key]}
						strokeWidth={1.5}
						dot={false}
						isAnimationActive={false}
					/>
				))}
			</LineChart>
		</ChartPanel>
	);
}
