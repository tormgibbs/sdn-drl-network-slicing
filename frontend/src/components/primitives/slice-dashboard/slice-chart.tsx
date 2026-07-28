// frontend/src/components/primitives/slice-dashboard/slice-chart.tsx
import {
	Area,
	AreaChart,
	CartesianGrid,
	Line,
	LineChart,
	ReferenceLine,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import type { ChartSpec } from "#/types/slice-view-config";
import { SliceTooltip } from "../slice-tooltip";
import { ChartPanel } from "./chartpanel";

export function SliceChart({
	spec,
	data,
}: {
	spec: ChartSpec;
	data: Record<string, number>[];
}) {
	const renderLiveDot = (props: any) => {
		const { cx, cy, index } = props;
		if (index !== data.length - 1) return null;
		return (
			<circle
				cx={cx}
				cy={cy}
				r={2.5}
				fill={spec.color}
				stroke="var(--card)"
				strokeWidth={1}
			/>
		);
	};

	const commonAxis = (
		<>
			<CartesianGrid stroke="var(--motif-line)" vertical={false} />
			<XAxis dataKey="i" hide />
			<YAxis
				tickCount={spec.yTickCount ?? 4}
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
				content={<SliceTooltip />}
				cursor={{ stroke: "var(--motif-line)", strokeWidth: 1 }}
			/>
			{spec.slaLine && (
				<ReferenceLine
					y={spec.slaLine.value}
					stroke={spec.slaLine.color}
					strokeDasharray="3 3"
					strokeWidth={1}
					label={{
						value: spec.slaLine.label,
						position: "insideTopLeft",
						fill: spec.slaLine.color,
						fontSize: 9,
						fontFamily: "var(--font-mono)",
					}}
				/>
			)}
		</>
	);

	return (
		<ChartPanel title={spec.title}>
			{spec.type === "area" ? (
				<AreaChart
					data={data}
					margin={{ top: 4, right: 8, bottom: 0, left: -8 }}
				>
					{commonAxis}
					<Area
						type="monotone"
						dataKey={spec.dataKey}
						stroke={spec.color}
						strokeWidth={1.5}
						fill={spec.color}
						fillOpacity={0.08}
						dot={renderLiveDot}
						isAnimationActive={false}
					/>
				</AreaChart>
			) : (
				<LineChart
					data={data}
					margin={{ top: 4, right: 8, bottom: 0, left: -8 }}
				>
					{commonAxis}
					<Line
						type="monotone"
						dataKey={spec.dataKey}
						stroke={spec.color}
						strokeWidth={1.5}
						dot={renderLiveDot}
						isAnimationActive={false}
					/>
				</LineChart>
			)}
		</ChartPanel>
	);
}
