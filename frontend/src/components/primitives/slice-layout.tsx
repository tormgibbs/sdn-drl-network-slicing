// frontend/src/components/primitives/Slicelayout.tsx
import type {
	MetricRowItem,
	RecentCycle,
	SLACellItem,
} from "../../types/slice1";
import { CurrentStatePanel } from "./slice-dashboard/current-state-panel";
import {
	HistoryTable,
	type HistoryTableProps,
} from "./slice-dashboard/history-table";
import { SLAThresholdsPanel } from "./slice-dashboard/slathresholds-panel";
import type { SliceHeaderProps } from "./slice-dashboard/sliceheader";
import type { SliceKey, SliceTab } from "./slice-switcher";
import { SliceSwitcher } from "./slice-switcher";
export type { SliceKey, SliceTab };
interface RightPanelProps {
	currentState: MetricRowItem[];
	slaThresholds: SLACellItem[];
	recentCycles: RecentCycle[];
	recentCols?: [string, string];
	recentSecondKey?: "thrpt" | "lat";
}
export interface SliceLayoutProps {
	switcherTabs: SliceTab[];
	activeSlice: SliceKey;
	onSliceChange: (key: SliceKey) => void;
	header: SliceHeaderProps;
	right: RightPanelProps;
	history: HistoryTableProps;
	children: React.ReactNode;
	telemetryLabel?: string;
	sidebarChildren?: React.ReactNode;
}
export function SliceLayout({
	switcherTabs,
	activeSlice,
	onSliceChange,
	right,
	history,
	children,
	telemetryLabel = "Telemetry Timeline",
	sidebarChildren,
}: SliceLayoutProps) {
	return (
		<div className="flex flex-col bg-background min-h-0">
			<SliceSwitcher
				tabs={switcherTabs}
				active={activeSlice}
				onChange={onSliceChange}
			/>
			<div className="flex flex-1 min-h-0">
				{sidebarChildren && (
					<div className="w-48 shrink-0 border-r border-border flex flex-col overflow-y-auto bg-card">
						{sidebarChildren}
					</div>
				)}
				<div className="flex flex-1 min-w-0">
					<div className="flex flex-col flex-1 min-w-0">
						<div className="flex items-center justify-between px-4 h-8 bg-card shrink-0">
							<span className="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
								{telemetryLabel}
							</span>
						</div>
						<div className="grid grid-cols-2 auto-rows-fr gap-4 bg-background flex-1">
							{children}
						</div>
					</div>
					<div className="w-72 shrink-0 border-l border-border flex flex-col bg-background">
						<CurrentStatePanel rows={right.currentState} />
						<SLAThresholdsPanel cells={right.slaThresholds} />
					</div>
				</div>
			</div>

			<HistoryTable {...history} />
		</div>
	);
}
