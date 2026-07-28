// frontend/src/components/primitives/slice-dashboard/current-state-panel.tsx
import type { MetricRowItem } from "../../../types/slice1";
import { PanelFrame } from "../panel-frame";

export function CurrentStatePanel({ rows }: { rows: MetricRowItem[] }) {
	return (
		<PanelFrame title="Current State" motif={false}>
			{rows.map(({ label, value, highlight }, idx) => (
				<div
					key={`${label}-${idx}`}
					className={[
						"flex items-center justify-between px-3 py-1.5 border-b border-border last:border-b-0",
						highlight ? "bg-accent" : "hover:bg-accent/50",
					].join(" ")}
				>
					<span className="font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
						{label}
					</span>
					<span
						className={[
							"font-mono text-[11px]",
							highlight ? "text-[#2B7FFF]" : "text-foreground",
						].join(" ")}
					>
						{value}
					</span>
				</div>
			))}
		</PanelFrame>
	);
}
