// frontend/src/components/primitives/agent-dashboard/trigger-timeline.tsx
import type { HeuristicHistoryPoint } from "#/stores/live-metrics-store";
import { PanelFrame } from "../panel-frame";

export function TriggerTimeline({
	history,
}: {
	history: HeuristicHistoryPoint[];
}) {
	const events = history
		.filter((p) => p.triggered.length > 0)
		.slice(-20)
		.reverse();

	return (
		<PanelFrame title="Trigger Events" motif={false} overflow="hidden">
			{events.length === 0 ? (
				<div className="px-3 py-4 text-xs font-mono text-muted-foreground">
					No thresholds crossed yet
				</div>
			) : (
				events.map((e) => (
					<div
						key={e.step}
						className="flex items-center justify-between px-3 py-1.5 border-b border-border last:border-b-0"
					>
						<span className="font-mono text-[10px] text-muted-foreground">
							STEP {e.step}
						</span>
						<span className="font-mono text-[11px] text-[#FF6900]">
							{e.triggered.join(", ")}
						</span>
					</div>
				))
			)}
		</PanelFrame>
	);
}
