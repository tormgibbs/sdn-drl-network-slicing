import { useState, useEffect, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { SliceLayout }  from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ADMIN_SLA, genAdminTelemetry, buildAdminHistory } from "../data/slices";

import type { SliceSharedProps } from "../types/sliceShared";

export function AdminSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const [range,   setRange]  = useState<"1M" | "5M" | "15M">("1M");
  const [data,    setData]   = useState(() => genAdminTelemetry(60));
  const [history]            = useState(() => buildAdminHistory(50));

  const pts  = range === "1M" ? 60 : range === "5M" ? 300 : 900;
  const tick = useCallback(() => setData(genAdminTelemetry(pts)), [pts]);
  useEffect(() => { tick(); const id = setInterval(tick, 3000); return () => clearInterval(id); }, [tick]);

  const last   = data[data.length - 1] ?? { thrpt: 11.2, lat: 82, loss: 0.3, txRate: 3.8, flows: 47 };
  const slaMet = last.lat! <= ADMIN_SLA.maxLat && last.thrpt >= ADMIN_SLA.minThrpt && last.loss <= ADMIN_SLA.maxLoss;

  // Report SLA status up to slices.tsx
  useEffect(() => { onSlaChange(slaMet); }, [slaMet, onSlaChange]);

  const recentCycles = history.slice(0, 7).map((r) => ({
    id:     r.id,
    thrpt:  r.thrpt,
    lat:    r.lat,
    status: r.sla,
  }));

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      // ── time range ──
      timeRange={range}
      onTimeRangeChange={setRange}
      telemetryLabel="Telemetry Timeline — Institutional Traffic (eMBB · Stable)"
      header={{
        name:     "Admin Systems",
        priority: "P3",
        slaMet,
        metricChips: [
          `${last.thrpt.toFixed(1)} Mbps`,
          `${last.lat!.toFixed(1)}ms`,
          `${last.loss.toFixed(2)}%`,
        ],
        extraChips: (
          <>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/50 bg-white/5">
              {last.txRate?.toFixed(1)} tx/s
            </span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/50 bg-white/5">
              {last.flows} flows
            </span>
          </>
        ),
        slaTargets: "10 Mbps min\u00a0·\u00a0150ms max\u00a0·\u00a01% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT",   value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "TX LATENCY",   value: `${last.lat!.toFixed(1)}ms` },
          { label: "PACKET LOSS",  value: `${last.loss.toFixed(2)}%` },
          { label: "TX RATE",      value: `${last.txRate?.toFixed(1)} tx/s` },
          { label: "ACTIVE FLOWS", value: String(last.flows) },
          { label: "ALLOCATED",    value: "10.0 Mbps", highlight: true },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "10 Mbps" },
          { label: "MAX LAT",   value: "150ms" },
          { label: "MAX LOSS",  value: "1%" },
          { label: "PRIORITY",  value: "P3 (Med)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows:  history,
        title: "History — Last 50 Cycles — Admin Systems Slice",
      }}
    >
      {/* Throughput */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Throughput</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gAdThrpt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#EAB308" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[5, 20]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={ADMIN_SLA.minThrpt} stroke="#6B7280" strokeDasharray="4 3"
                label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="thrpt" name="Mbps"
                stroke="#EAB308" strokeWidth={1.5} fill="url(#gAdThrpt)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Transaction Latency */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Transaction Latency</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 200]} tickCount={5} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={ADMIN_SLA.maxLat} stroke="#FB2C36" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Line type="monotone" dataKey="lat" name="ms"
                stroke="#EAB308" strokeWidth={1.5} dot={false} isAnimationActive={false} />
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
                <linearGradient id="gAdLoss" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#FB2C36" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 2]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={ADMIN_SLA.maxLoss} stroke="#EAB308" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="loss" name="%"
                stroke="#FB2C36" strokeWidth={1.5} fill="url(#gAdLoss)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Transaction Rate */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Transaction Rate</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gAdTx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#EAB308" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 10]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <Area type="stepAfter" dataKey="txRate" name="tx/s"
                stroke="#EAB308" strokeWidth={1.5} fill="url(#gAdTx)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </SliceLayout>
  );
}
