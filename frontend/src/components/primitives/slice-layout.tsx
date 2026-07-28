import { SliceSwitcher } from "./SliceSwitcher";
import type { SliceTab, SliceKey } from "./SliceSwitcher";
import type { RecentCycle } from "../../types/slice1";
import { SliceHeader, type SliceHeaderProps } from "./slice-dashboard/sliceheader";
import { CurrentStatePanel } from "./slice-dashboard/current-state-panel";
import { SLAThresholdsPanel } from "./slice-dashboard/slathresholds-panel";
import { RecentCyclesPanel } from "./slice-dashboard/recent-cycles-panel";
import { HistoryTable, type HistoryTableProps } from "./slice-dashboard/history-table";
import type { MetricRowItem, SLACellItem } from "../../types/slice1";

export type { SliceTab, SliceKey };

interface RightPanelProps {
  currentState:     MetricRowItem[];
  slaThresholds:    SLACellItem[];
  recentCycles:     RecentCycle[];
  recentCols?:      [string, string];
  recentSecondKey?: "thrpt" | "lat";
}

export interface SliceLayoutProps {
  switcherTabs:      SliceTab[];
  activeSlice:       SliceKey;
  onSliceChange:     (key: SliceKey) => void;
  header:            SliceHeaderProps;
  right:             RightPanelProps;
  history:           HistoryTableProps;
  children:          React.ReactNode;
  telemetryLabel?:   string;
  timeRange:         "1M" | "5M" | "15M";
  onTimeRangeChange: (r: "1M" | "5M" | "15M") => void;
  sidebarChildren?:  React.ReactNode;
}

export function SliceLayout({
  switcherTabs,
  activeSlice,
  onSliceChange,
  header,
  right,
  history,
  children,
  telemetryLabel = "Telemetry Timeline",
  timeRange,
  onTimeRangeChange,
  sidebarChildren,
}: SliceLayoutProps) {
  const recentCycles: RecentCycle[] = right.recentCycles.map((c) => ({
    id:     c.id,
    thrpt:  c.thrpt,
    lat:    c.lat,
    status: c.status,
  }));

  return (
    <div className="flex flex-col bg-black min-h-0">
      <SliceSwitcher tabs={switcherTabs} active={activeSlice} onChange={onSliceChange} />

      <SliceHeader {...header} />

      <div className="flex flex-1 min-h-0">
        {sidebarChildren && (
          <div className="w-48 shrink-0 border-r border-white/10 flex flex-col overflow-y-auto bg-zinc-950">
            {sidebarChildren}
          </div>
        )}

        <div className="flex flex-1 min-w-0">
          <div className="flex flex-col flex-1 min-w-0">
            <div className="flex items-center justify-between px-4 h-8 border-b border-white/10 bg-zinc-950 shrink-0">
              <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">{telemetryLabel}</span>
              <div className="flex gap-px">
                {(["1M", "5M", "15M"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => onTimeRangeChange(t)}
                    className={[
                      "font-mono text-[10px] px-2.5 py-1 cursor-pointer border-none transition-colors",
                      timeRange === t
                        ? "bg-white/10 text-white"
                        : "bg-transparent text-white/35 hover:text-white/60",
                    ].join(" ")}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-px bg-white/10 flex-1">
              {children}
            </div>
          </div>

          <div className="w-72 shrink-0 border-l border-white/10 flex flex-col bg-black">
            <CurrentStatePanel rows={right.currentState} />
            <SLAThresholdsPanel cells={right.slaThresholds} />
            <RecentCyclesPanel cycles={recentCycles} cols={right.recentCols} />
          </div>
        </div>
      </div>

      <HistoryTable {...history} />
    </div>
  );
}