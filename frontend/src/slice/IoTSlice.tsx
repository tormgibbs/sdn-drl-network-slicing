import { useState, useEffect, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { SliceLayout }  from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import {
  IOT_SLA,
  genIoTTelemetry,
  buildIoTHistory,
  INIT_SOURCES,
  STATUS_COLOR,
  fmtArrival,
} from "../data/slices";
import type { TrafficSource } from "../types/slice1";

import type { SliceSharedProps } from "../types/sliceShared";

export function IoTSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const [range,   setRange]   = useState<"1M" | "5M" | "15M">("1M");
  const [data,    setData]    = useState(() => genIoTTelemetry(60));
  const [history]             = useState(() => buildIoTHistory(50));
  const [sources, setSources] = useState<TrafficSource[]>(INIT_SOURCES);
  const [selSrc,  setSelSrc]  = useState("SRC-001");

  const pts  = range === "1M" ? 60 : range === "5M" ? 300 : 900;
  const tick = useCallback(() => setData(genIoTTelemetry(pts)), [pts]);
  useEffect(() => { tick(); const id = setInterval(tick, 2500); return () => clearInterval(id); }, [tick]);

  // Heartbeat jitter simulation
  useEffect(() => {
    const id = setInterval(() => {
      setSources((prev) =>
        prev.map((s) =>
          s.status !== "missed"
            ? { ...s, lastArrival: Math.floor(500 + Math.random() * 4000), latency: +(30 + Math.random() * 160).toFixed(0) }
            : s,
        ),
      );
    }, 2500);
    return () => clearInterval(id);
  }, []);

  const last        = data[data.length - 1] ?? { thrpt: 0.064, lat: 95, loss: 1.2, pktRate: 18, sources: 6 };
  const slaMet      = last.lat! <= IOT_SLA.maxLat && last.loss <= IOT_SLA.maxLoss;

  // Report SLA status up to slices.tsx
  useEffect(() => { onSlaChange(slaMet); }, [slaMet, onSlaChange]);
  const selectedSrc = sources.find((s) => s.id === selSrc)!;

  const onSchedule  = sources.filter((s) => s.status === "on-schedule").length;
  const delayed     = sources.filter((s) => s.status === "delayed").length;
  const missed      = sources.filter((s) => s.status === "missed").length;

  const recentCycles = history.slice(0, 7).map((r) => ({
    id:     r.id,
    thrpt:  r.thrpt,
    lat:    r.lat,
    status: r.sla,
  }));

  // IoT sidebar: source list
  const sidebarChildren = (
    <>
      <div style={{ padding: "8px 16px 6px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: "0.1em", color: "var(--text-ter)", textTransform: "uppercase", marginBottom: 6 }}>
          Traffic Sources
        </div>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <span className="badge badge-green">{onSchedule} ON-TIME</span>
          {delayed > 0 && <span className="badge badge-amber">{delayed} DELAYED</span>}
          {missed  > 0 && <span className="badge badge-red">{missed} MISSED</span>}
        </div>
      </div>
      {sources.map((s) => (
        <button
          key={s.id}
          onClick={() => setSelSrc(s.id)}
          style={{
            display: "flex", flexDirection: "column", gap: 2,
            width: "100%", padding: "6px 16px",
            background:   selSrc === s.id ? "var(--bg-elevated)" : "transparent",
            border:       "none",
            borderLeft:   `2px solid ${selSrc === s.id ? STATUS_COLOR[s.status] : "transparent"}`,
            borderBottom: "1px solid var(--border)",
            cursor: "pointer", textAlign: "left",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span className="status-dot" style={{ background: STATUS_COLOR[s.status], flexShrink: 0 }} />
            <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-pri)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {s.name}
            </span>
          </div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "var(--text-ter)", paddingLeft: 14 }}>
            {s.id} · {fmtArrival(s.lastArrival)} ago
          </div>
        </button>
      ))}
    </>
  );

  // IoT right column has an extra "Source Detail" panel — injected via currentState grouping
  // We render a custom right column below and pass it; however SliceLayout's right column
  // doesn't support arbitrary extra panels, so we extend currentState with a divider row
  // and use a separate sidePanel slot. For IoT specifically, we override via a wrapper.

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      // ── time range ──
      timeRange={range}
      onTimeRangeChange={setRange}
      sidebarChildren={sidebarChildren}
      telemetryLabel="Telemetry Timeline — Heartbeat / Control Traffic (mMTC)"
      header={{
        name:     "IoT",
        priority: "P2",
        slaMet,
        metricChips: [
          `${(last.thrpt * 1000).toFixed(2)} Kbps`,
          `${last.lat!.toFixed(1)}ms`,
          `${last.loss.toFixed(2)}%`,
        ],
        extraChips: (
          <>
            <span className="metric-chip" style={{ color: "var(--text-sec)", borderColor: "var(--border)" }}>
              {last.pktRate?.toFixed(0)} pkts/min
            </span>
            <span className="metric-chip" style={{ color: "var(--text-sec)", borderColor: "var(--border)" }}>
              {last.sources} active
            </span>
          </>
        ),
        slaTargets: "64 Kbps min\u00a0·\u00a0200ms max\u00a0·\u00a05% max",
      }}
      right={{
        // Source detail rows + aggregate — merged into currentState for layout reuse
        
        currentState: [
        ...(selectedSrc ? [
          { label: "SOURCE ID",       value: selectedSrc.id },
          { label: "TRAFFIC SRC",     value: selectedSrc.name },
          { label: "SRC PKT RATE",    value: `${selectedSrc.pktRate} pkts/min` },  // was "PKT RATE"
          { label: "LAST ARRIVAL",    value: `${fmtArrival(selectedSrc.lastArrival)} ago` },
          { label: "SRC HB LATENCY",  value: selectedSrc.status !== "missed" ? `${selectedSrc.latency}ms` : "—" },  // was "HB LATENCY"
        ] : []),
        { label: "——",            value: "" },
        { label: "BANDWIDTH",     value: `${(last.thrpt * 1000).toFixed(2)} Kbps` },
        { label: "HB LATENCY",    value: `${last.lat!.toFixed(1)}ms` },   // aggregate — keep as-is
        { label: "PACKET LOSS",   value: `${last.loss.toFixed(2)}%` },
        { label: "PKT RATE",      value: `${last.pktRate?.toFixed(0)} pkts/min` },  // aggregate — keep as-is
        { label: "ALLOCATED",     value: "64 Kbps", highlight: true },
      ],
        slaThresholds: [
          { label: "MIN THRPT", value: "64 Kbps" },
          { label: "MAX LAT",   value: "200ms" },
          { label: "MAX LOSS",  value: "5%" },
          { label: "PRIORITY",  value: "P2 (Low)", highlight: true },
        ],
        recentCycles,
        recentCols: ["LAT", "LOSS"],
      }}
      history={{
        rows:       history,
        title:      "History — Last 50 Cycles — IoT Slice (mMTC)",
        thrptHeader: "BW (KBPS)",
        renderThrpt: (row) => (row.thrpt * 1000).toFixed(2),
        renderAlloc: () => "64",
      }}
    >
      {/* Packet Rate */}
      <div style={{ background: "var(--bg-surface)" }}>
        <div className="panel-hdr"><span className="panel-hdr-title">Packet Rate</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gIoPkt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4ADE80" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#4ADE80" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 60]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <Area type="stepAfter" dataKey="pktRate" name="pkts/min"
                stroke="#4ADE80" strokeWidth={1.5} fill="url(#gIoPkt)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Heartbeat Latency */}
      <div style={{ background: "var(--bg-surface)" }}>
        <div className="panel-hdr"><span className="panel-hdr-title">Heartbeat Latency</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 250]} tickCount={5} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={IOT_SLA.maxLat} stroke="#FB2C36" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Line type="monotone" dataKey="lat" name="ms"
                stroke="#4ADE80" strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Packet Loss */}
      <div style={{ background: "var(--bg-surface)" }}>
        <div className="panel-hdr"><span className="panel-hdr-title">Packet Loss</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gIoLoss" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#FB2C36" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 6]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={IOT_SLA.maxLoss} stroke="#EAB308" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="loss" name="%"
                stroke="#FB2C36" strokeWidth={1.5} fill="url(#gIoLoss)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Active Sources */}
      <div style={{ background: "var(--bg-surface)" }}>
        <div className="panel-hdr"><span className="panel-hdr-title">Active Sources</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gIoSrc" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4ADE80" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#4ADE80" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 10]} tickCount={4} />
              <Tooltip content={<SliceTooltip decimals={0} />} />
              <Area type="stepAfter" dataKey="sources" name="sources"
                stroke="#4ADE80" strokeWidth={1.5} fill="url(#gIoSrc)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </SliceLayout>
  );
}
