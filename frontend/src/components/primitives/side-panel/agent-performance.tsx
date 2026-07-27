// frontend/src/components/primitives/side-panel/agent-performance.tsx
// 
import { ChartNoAxesCombined, TrendingDown, TrendingUp } from "lucide-react";

type AgentPerformanceProps = {
	reward: number;
	slaSatisfaction: string;
};

export function AgentPerformance({
	reward,
	slaSatisfaction,
}: AgentPerformanceProps) {
	const isPositive = reward >= 0;

	return (
		<div className="mt-8 mb-4">
			<div className="flex gap-2">
				<ChartNoAxesCombined size={20} />
				<p className="font-bold uppercase mb-4">Agent Performance</p>
			</div>
			<div className="my-4">
				<p className="uppercase">Reward Signal</p>
				<p
					className={`text-3xl font-bold flex items-center gap-2 ${
						isPositive ? "text-green-500" : "text-red-500"
					}`}
				>
					<span>
						{isPositive ? "+" : ""}
						{reward.toFixed(2)}
					</span>
					{isPositive ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
				</p>
			</div>
			<div className="my-4">
				<p className="uppercase">SLA Satisfaction</p>
				<p className="text-3xl font-bold">{slaSatisfaction}%</p>
			</div>
		</div>
	);
}
