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
      <div className="px-4 py-2 border-b border-white/10">
        <div className="font-mono text-[9px] tracking-widest text-white/30 uppercase mb-1.5">
          Traffic Sources
        </div>
        <div className="flex gap-1 flex-wrap">
          <span className="font-mono text-[9px] px-1.5 py-0.5 rounded border text-emerald-400 border-emerald-500/30 bg-emerald-500/10 uppercase tracking-widest">{onSchedule} ON-TIME</span>
          {delayed > 0 && <span className="font-mono text-[9px] px-1.5 py-0.5 rounded border text-amber-400 border-amber-500/30 bg-amber-500/10 uppercase tracking-widest">{delayed} DELAYED</span>}
          {missed  > 0 && <span className="font-mono text-[9px] px-1.5 py-0.5 rounded border text-red-400 border-red-500/30 bg-red-500/10 uppercase tracking-widest">{missed} MISSED</span>}
        </div>
      </div>
      {sources.map((s) => (
        <button
          key={s.id}
          onClick={() => setSelSrc(s.id)}
          className="flex flex-col gap-0.5 w-full px-4 py-1.5 border-b border-white/10 cursor-pointer text-left bg-transparent border-0 border-l-2 transition-colors"
          style={{
            borderLeftColor: selSrc === s.id ? STATUS_COLOR[s.status] : "transparent",
            background: selSrc === s.id ? "rgba(255,255,255,0.04)" : "transparent",
          }}
        >
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: STATUS_COLOR[s.status] }} />
            <span className="text-[11px] font-medium text-white truncate">
              {s.name}
            </span>
          </div>
          <div className="font-mono text-[9px] text-white/30 pl-3">
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
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/50 bg-white/5">
              {last.pktRate?.toFixed(0)} pkts/min
            </span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/50 bg-white/5">
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
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Packet Rate</span></div>
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
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Heartbeat Latency</span></div>
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
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Packet Loss</span></div>
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
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Active Sources</span></div>
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
