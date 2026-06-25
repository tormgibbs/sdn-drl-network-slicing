import { Download } from "lucide-react";
import { SliceSwitcher } from "./SliceSwitcher";
import type { SliceTab, SliceKey } from "./SliceSwitcher";
import type { MetricRowItem, SLACellItem, HistoryRow, RecentCycle } from "../../types/slice1";

export type { SliceTab, SliceKey };

// ── types ─────────────────────────────────────────────────────────────────────

interface SliceHeaderProps {
  name:        string;
  priority:    string;
  slaMet:      boolean;
  metricChips: string[];
  extraChips?: React.ReactNode;
  slaTargets:  string;
}

interface RightPanelProps {
  currentState:     MetricRowItem[];
  slaThresholds:    SLACellItem[];
  recentCycles:     RecentCycle[];
  recentCols?:      [string, string];
  recentSecondKey?: "thrpt" | "lat";
}

interface HistoryTableProps {
  rows:          HistoryRow[];
  title:         string;
  thrptHeader?:  string;
  renderThrpt?:  (row: HistoryRow) => React.ReactNode;
  renderAlloc?:  (row: HistoryRow) => React.ReactNode;
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

// ── sub-components ────────────────────────────────────────────────────────────

function SliceHeader({ name, priority, slaMet, metricChips, extraChips, slaTargets }: SliceHeaderProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 px-4 h-11 border-b border-white/10 bg-zinc-950">
      <span className="font-mono text-[13px] font-semibold text-white tracking-wide">{name}</span>

      {/* Priority badge */}
      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded border border-white/15 text-white/50 bg-white/5">
        {priority}
      </span>

      {/* SLA status */}
      <span className={[
        "font-mono text-[9px] px-1.5 py-0.5 rounded border font-medium tracking-widest uppercase",
        slaMet
          ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
          : "text-red-400 border-red-500/30 bg-red-500/10",
      ].join(" ")}>
        {slaMet ? "MET" : "VIOLATION"}
      </span>

      {/* Metric chips */}
      <div className="flex gap-1.5 ml-2">
        {metricChips.map((v) => (
          <span key={v} className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/70 bg-white/5">
            {v}
          </span>
        ))}
      </div>

      {extraChips && <div className="flex gap-1.5">{extraChips}</div>}

      <span className="font-mono text-[10px] text-white/30 ml-auto">{slaTargets}</span>
    </div>
  );
}

function CurrentStatePanel({ rows }: { rows: MetricRowItem[] }) {
  return (
    <div className="border-b border-white/10">
      <div className="px-4 h-8 flex items-center border-b border-white/10 bg-white/[0.03]">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Current State</span>
      </div>
      {rows.map(({ label, value, highlight }, idx) => (
        <div
          key={`${label}-${idx}`}
          className={[
            "flex items-center justify-between px-4 py-1.5",
            highlight ? "bg-white/[0.04]" : "hover:bg-white/[0.02]",
          ].join(" ")}
        >
          <span className="font-mono text-[10px] text-white/35 uppercase tracking-wider">{label}</span>
          <span className={[
            "font-mono text-[11px]",
            highlight ? "text-blue-400" : "text-white/80",
          ].join(" ")}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function SLAThresholdsPanel({ cells }: { cells: SLACellItem[] }) {
  return (
    <div className="border-b border-white/10">
      <div className="px-4 h-8 flex items-center border-b border-white/10 bg-white/[0.03]">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">SLA Thresholds</span>
      </div>
      <div className="grid grid-cols-2 gap-px bg-white/10 m-2 rounded overflow-hidden">
        {cells.map(({ label, value, highlight }) => (
          <div
            key={label}
            className={[
              "flex flex-col px-3 py-2",
              highlight ? "bg-white/[0.06]" : "bg-zinc-950",
            ].join(" ")}
          >
            <span className="font-mono text-[9px] text-white/30 uppercase tracking-widest mb-0.5">{label}</span>
            <span className={[
              "font-mono text-[12px] font-semibold",
              highlight ? "text-blue-400" : "text-white/75",
            ].join(" ")}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentCyclesPanel({ cycles, cols = ["THRPT", "LAT"] }: { cycles: RecentCycle[]; cols?: [string, string] }) {
  return (
    <div className="flex flex-col flex-1 overflow-hidden border-b border-white/10">
      <div className="px-4 h-8 flex items-center border-b border-white/10 bg-white/[0.03] shrink-0">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Recent Cycles</span>
      </div>
      <div className="overflow-y-auto flex-1">
        <table className="w-full text-[10px] font-mono">
          <thead>
            <tr className="border-b border-white/10">
              <th className="w-6 px-3 py-1.5 text-left text-white/30 font-normal">ST</th>
              <th className="px-3 py-1.5 text-left text-white/30 font-normal">CYCLE ID</th>
              <th className="px-3 py-1.5 text-right text-white/30 font-normal">{cols[0]}</th>
              <th className="px-3 py-1.5 text-right text-white/30 font-normal">{cols[1]}</th>
            </tr>
          </thead>
          <tbody>
            {cycles.slice(0, 7).map((c) => {
              const isViolation = c.status === "VIOLATION";
              return (
                <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-3 py-1.5">
                    <span className={[
                      "inline-block w-1.5 h-1.5 rounded-full",
                      isViolation ? "bg-amber-400" : "bg-transparent border border-white/15",
                    ].join(" ")} />
                  </td>
                  <td className={["px-3 py-1.5", isViolation ? "text-amber-400" : "text-white/60"].join(" ")}>{c.id}</td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-amber-400" : "text-white/60"].join(" ")}>{c.thrpt}</td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-amber-400" : "text-white/60"].join(" ")}>{c.lat}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HistoryTable({ rows, title, thrptHeader = "THRPT (MBPS)", renderThrpt, renderAlloc }: HistoryTableProps) {
  return (
    <div className="border-t border-white/10">
      {/* Sticky header */}
      <div className="flex items-center justify-between px-4 h-8 bg-zinc-950 border-b border-white/10 sticky top-0 z-10">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">{title}</span>
        <button className="text-white/30 hover:text-white/60 transition-colors cursor-pointer bg-transparent border-none p-0">
          <Download size={12} />
        </button>
      </div>
      <div className="max-h-72 overflow-y-auto overflow-x-auto">
        <table className="w-full text-[10px] font-mono min-w-[600px]">
          <thead className="sticky top-0 bg-zinc-950 z-10">
            <tr className="border-b border-white/10">
              <th className="px-3 py-2 text-left text-white/30 font-normal">TIMESTAMP</th>
              <th className="px-3 py-2 text-left text-white/30 font-normal">CYCLE ID</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">{thrptHeader}</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">LAT (MS)</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">LOSS (%)</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">ALLOC</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">SLA STATUS</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const isViolation = row.sla === "VIOLATION";
              return (
                <tr
                  key={row.id + idx}
                  className={["border-b border-white/5", idx % 2 === 0 ? "bg-transparent" : "bg-white/[0.02]"].join(" ")}
                >
                  <td className="px-3 py-1.5 text-white/40">{row.ts}</td>
                  <td className="px-3 py-1.5 text-white/60">{row.id}</td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-red-400" : "text-white/60"].join(" ")}>
                    {renderThrpt ? renderThrpt(row) : row.thrpt}
                  </td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-red-400" : "text-white/60"].join(" ")}>{row.lat}</td>
                  <td className="px-3 py-1.5 text-right text-white/50">{row.loss}</td>
                  <td className="px-3 py-1.5 text-right text-white/50">{renderAlloc ? renderAlloc(row) : row.alloc}</td>
                  <td className="px-3 py-1.5 text-right">
                    <span className={[
                      "font-mono text-[9px] px-1.5 py-0.5 rounded border uppercase tracking-widest",
                      row.sla === "MET"
                        ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                        : "text-red-400 border-red-500/30 bg-red-500/10",
                    ].join(" ")}>
                      {row.sla}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main layout ───────────────────────────────────────────────────────────────

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
      {/* Slice switcher */}
      <SliceSwitcher tabs={switcherTabs} active={activeSlice} onChange={onSliceChange} />

      {/* Slice header */}
      <SliceHeader {...header} />

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Optional IoT sidebar */}
        {sidebarChildren && (
          <div className="w-48 shrink-0 border-r border-white/10 flex flex-col overflow-y-auto bg-zinc-950">
            {sidebarChildren}
          </div>
        )}

        {/* Main grid: charts + right panel */}
        <div className="flex flex-1 min-w-0">
          {/* Chart area */}
          <div className="flex flex-col flex-1 min-w-0">
            {/* Telemetry bar */}
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

            {/* 2×2 chart grid */}
            <div className="grid grid-cols-2 gap-px bg-white/10 flex-1">
              {children}
            </div>
          </div>

          {/* Right panel */}
          <div className="w-72 shrink-0 border-l border-white/10 flex flex-col bg-black">
            <CurrentStatePanel rows={right.currentState} />
            <SLAThresholdsPanel cells={right.slaThresholds} />
            <RecentCyclesPanel cycles={recentCycles} cols={right.recentCols} />
          </div>
        </div>
      </div>

      {/* History table */}
      <HistoryTable {...history} />
    </div>
  );
}
