// frontend/src/components/primitives/agent-dashboard/reward-trend-chart.tsx
import {
	CartesianGrid,
	Line,
	LineChart,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { ChartPanel } from "../slice-dashboard/chartpanel";

export function RewardTrendChart({
	history,
}: {
	history: Array<{ step: number; reward: number }>;
}) {
	return (
		<ChartPanel title="Reward Over Time">
			<LineChart
				data={history}
				margin={{ top: 4, right: 8, bottom: 0, left: -8 }}
			>
				<CartesianGrid stroke="var(--motif-line)" vertical={false} />
				<XAxis dataKey="step" hide />
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
				<Line
					type="monotone"
					dataKey="reward"
					stroke="#2B7FFF"
					strokeWidth={1.5}
					dot={false}
					isAnimationActive={false}
				/>
			</LineChart>
		</ChartPanel>
	);
}
