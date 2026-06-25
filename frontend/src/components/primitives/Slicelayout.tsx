// ── Shared layout shell for all network slice pages ───────────────────────────
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
  currentState:   MetricRowItem[];
  slaThresholds:  SLACellItem[];
  recentCycles:   RecentCycle[];
  recentCols?:    [string, string];
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
  // ── switcher ──
  /** All five tabs with live SLA status — drives the switcher */
  switcherTabs:     SliceTab[];
  activeSlice:      SliceKey;
  onSliceChange:    (key: SliceKey) => void;
  // ── slice content ──
  header:           SliceHeaderProps;
  right:            RightPanelProps;
  history:          HistoryTableProps;
  children:         React.ReactNode;
  telemetryLabel?:  string;
  timeRange:        "1M" | "5M" | "15M";
  onTimeRangeChange:(r: "1M" | "5M" | "15M") => void;
}

// ── sub-components ────────────────────────────────────────────────────────────

function SliceHeader({ name, priority, slaMet, metricChips, extraChips, slaTargets }: SliceHeaderProps) {
  return (
    <div className="vle-header">
      <span className="vle-name">{name}</span>
      <span className="badge badge-gray">{priority}</span>
      <span className={`badge ${slaMet ? "badge-green" : "badge-red"}`}>
        {slaMet ? "MET" : "VIOLATION"}
      </span>
      <div style={{ display: "flex", gap: 6, marginLeft: 12 }}>
        {metricChips.map((v) => (
          <span key={v} className="metric-chip">{v}</span>
        ))}
      </div>
      {extraChips && (
        <div style={{ display: "flex", gap: 6, marginLeft: 6 }}>
          {extraChips}
        </div>
      )}
      <span className="sla-targets">{slaTargets}</span>
    </div>
  );
}

function CurrentStatePanel({ rows }: { rows: MetricRowItem[] }) {
  return (
    <div className="panel">
      <div className="panel-hdr"><span className="panel-hdr-title">Current State</span></div>
      {rows.map(({ label, value, highlight }, idx) => (
        <div key={`${label}-${idx}`} className="metric-row" style={{ background: highlight ? "#111111" : undefined }}>
          <span className="metric-row-label">{label}</span>
          <span className="metric-row-value">{value}</span>
        </div>
      ))}
    </div>
  );
}

function SLAThresholdsPanel({ cells }: { cells: SLACellItem[] }) {
  return (
    <div className="panel">
      <div className="panel-hdr"><span className="panel-hdr-title">SLA Thresholds</span></div>
      <div className="sla-grid">
        {cells.map(({ label, value, highlight }) => (
          <div key={label} className="sla-cell" style={{ background: highlight ? "#111111" : undefined }}>
            <div className="sla-cell-label">{label}</div>
            <div className="sla-cell-value">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentCyclesPanel({ cycles, cols = ["THRPT", "LAT"] }: { cycles: RecentCycle[]; cols?: [string, string] }) {
  return (
    <div className="panel" style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div className="panel-hdr"><span className="panel-hdr-title">Recent Cycles</span></div>
      <div style={{ overflowY: "auto", flex: 1 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 20 }}>ST</th>
              <th>CYCLE ID</th>
              <th style={{ textAlign: "right" }}>{cols[0]}</th>
              <th style={{ textAlign: "right" }}>{cols[1]}</th>
            </tr>
          </thead>
          <tbody>
            {cycles.slice(0, 7).map((c) => (
              <tr key={c.id}>
                <td>
                  <span className="status-dot" style={{
                    background:  c.status === "VIOLATION" ? "#EAB308" : "transparent",
                    border:      `1px solid ${c.status === "VIOLATION" ? "#EAB308" : "#2A2A2A"}`,
                    display:     "inline-block",
                  }} />
                </td>
                <td className="td-pri">{c.id}</td>
                <td style={{ textAlign: "right" }} className={c.status === "VIOLATION" ? "td-warn" : ""}>{c.thrpt}</td>
                <td style={{ textAlign: "right" }} className={c.status === "VIOLATION" ? "td-warn" : ""}>{c.lat}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HistoryTable({ rows, title, thrptHeader = "THRPT (MBPS)", renderThrpt, renderAlloc }: HistoryTableProps) {
  return (
    <div style={{ borderTop: "1px solid var(--border)" }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 12px", height: 32, background: "var(--bg-elevated)",
        borderBottom: "1px solid var(--border)", position: "sticky", top: 0, zIndex: 10,
      }}>
        <span className="panel-hdr-title">{title}</span>
        <button style={{ background: "none", border: "none", color: "var(--text-ter)", cursor: "pointer", display: "flex", alignItems: "center" }}>
          <Download size={13} />
        </button>
      </div>
      <div style={{ maxHeight: 280, overflowY: "auto", overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>TIMESTAMP</th>
              <th>CYCLE ID</th>
              <th style={{ textAlign: "right" }}>{thrptHeader}</th>
              <th style={{ textAlign: "right" }}>LAT (MS)</th>
              <th style={{ textAlign: "right" }}>LOSS (%)</th>
              <th style={{ textAlign: "right" }}>ALLOC</th>
              <th style={{ textAlign: "right" }}>SLA STATUS</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={row.id + idx} style={{ background: idx % 2 === 0 ? "var(--bg-base)" : "var(--bg-surface)" }}>
                <td>{row.ts}</td>
                <td className="td-pri">{row.id}</td>
                <td style={{ textAlign: "right" }} className={row.sla === "VIOLATION" ? "td-violation" : ""}>
                  {renderThrpt ? renderThrpt(row) : row.thrpt}
                </td>
                <td style={{ textAlign: "right" }} className={row.sla === "VIOLATION" ? "td-violation" : ""}>{row.lat}</td>
                <td style={{ textAlign: "right" }}>{row.loss}</td>
                <td style={{ textAlign: "right" }}>{renderAlloc ? renderAlloc(row) : row.alloc}</td>
                <td style={{ textAlign: "right" }}>
                  <span className={`badge ${row.sla === "MET" ? "badge-green" : "badge-red"}`}>{row.sla}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main layout ───────────────────────────────────────────────────────────────
// NOTE: AppSidebar is NOT rendered here — it lives in the parent route (_app.tsx)
// so it stays mounted across slice switches without re-rendering.

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
}: SliceLayoutProps) {
  const recentCycles: RecentCycle[] = right.recentCycles.map((c) => ({
    id:     c.id,
    thrpt:  c.thrpt,
    lat:    c.lat,
    status: c.status,
  }));

  return (
    <div className="slice-main">
      {/* ── Slice switcher tab strip ── */}
      <SliceSwitcher
        tabs={switcherTabs}
        active={activeSlice}
        onChange={onSliceChange}
      />

      {/* ── Slice name / SLA status header ── */}
      <SliceHeader {...header} />

      {/* ── Body grid ── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 320px",
        gap: 1,
        backgroundColor: "var(--border)",
      }}>
        {/* Left — chart area */}
        <div style={{ background: "var(--bg-base)", display: "flex", flexDirection: "column", gap: 1 }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "0 12px", height: 32,
            background: "var(--bg-elevated)", borderBottom: "1px solid var(--border)",
          }}>
            <span className="panel-hdr-title">{telemetryLabel}</span>
            <div className="tab-strip">
              {(["1M", "5M", "15M"] as const).map((t) => (
                <button
                  key={t}
                  className={`tab-btn ${timeRange === t ? "tab-btn--active" : ""}`}
                  onClick={() => onTimeRangeChange(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr",
            gap: 1, backgroundColor: "var(--border)", flex: 1,
          }}>
            {children}
          </div>
        </div>

        {/* Right — panels */}
        <div style={{ background: "var(--bg-base)", display: "flex", flexDirection: "column", gap: 1 }}>
          <CurrentStatePanel rows={right.currentState} />
          <SLAThresholdsPanel cells={right.slaThresholds} />
          <RecentCyclesPanel cycles={recentCycles} cols={right.recentCols} />
        </div>
      </div>

      <HistoryTable {...history} />
    </div>
  );
}
