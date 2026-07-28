// frontend/src/components/primitives/side-panel/heuristic-performance.tsx
import { ChartNoAxesCombined } from "lucide-react";

type HeuristicPerformanceProps = {
	triggerCount: number;
	slaSatisfaction: string;
};

export function HeuristicPerformance({
	triggerCount,
	slaSatisfaction,
}: HeuristicPerformanceProps) {
	return (
		<div className="mt-8 mb-4">
			<div className="flex gap-2">
				<ChartNoAxesCombined size={20} />
				<p className="font-bold uppercase mb-4 text-sm">
					Heuristic Performance
				</p>
			</div>
			<div className="my-4">
				<p className="uppercase text-xs text-muted-foreground">
					Total Triggers
				</p>
				<p className="text-3xl font-bold">{triggerCount}</p>
			</div>
			<div className="my-4">
				<p className="uppercase text-xs text-muted-foreground">
					SLA Satisfaction
				</p>
				<p className="text-3xl font-bold">{slaSatisfaction}%</p>
			</div>
		</div>
	);
}
