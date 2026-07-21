import { useState, useEffect, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { SliceLayout }  from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import {
  STUDENT_PORTAL_SLA,
  genStudentPortalTelemetry,
  buildStudentPortalHistory,
} from "../data/slices";

import type { SliceSharedProps } from "../types/sliceShared";

export function StudentPortalSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const [range,   setRange]  = useState<"1M" | "5M" | "15M">("1M");
  const [data,    setData]   = useState(() => genStudentPortalTelemetry(60));
  const [history]            = useState(() => buildStudentPortalHistory(50));

  const pts  = range === "1M" ? 60 : range === "5M" ? 300 : 900;
  const tick = useCallback(() => setData(genStudentPortalTelemetry(pts)), [pts]);
  useEffect(() => { tick(); const id = setInterval(tick, 3000); return () => clearInterval(id); }, [tick]);

  const last   = data[data.length - 1] ?? { thrpt: 26.1, lat: 28, loss: 0.0, reqRate: 5.2, sessions: 142 };
  const slaMet = last.lat! <= STUDENT_PORTAL_SLA.maxLat
    && last.thrpt >= STUDENT_PORTAL_SLA.minThrpt
    && last.loss  <= STUDENT_PORTAL_SLA.maxLoss;

  // Report SLA status up to slices.tsx
  useEffect(() => { onSlaChange(slaMet); }, [slaMet, onSlaChange]);

  // Build recent cycles from live history so Recent Cycles uses generated data
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
      telemetryLabel="Telemetry Timeline — HTTP Transaction Traffic (eMBB)"
      header={{
        name:     "Student Portal",
        priority: "P4",
        slaMet,
        metricChips: [
          `${last.thrpt.toFixed(1)} Mbps`,
          `${last.lat!.toFixed(1)}ms`,
          `${last.loss.toFixed(3)}%`,
        ],
        extraChips: (
          <>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/50 bg-white/5">
              {last.reqRate?.toFixed(1)} req/s
            </span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/50 bg-white/5">
              {last.sessions} sessions
            </span>
          </>
        ),
        slaTargets: "25 Mbps min\u00a0·\u00a050ms max\u00a0·\u00a00.1% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT",   value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "RESP LATENCY", value: `${last.lat!.toFixed(1)}ms` },
          { label: "PACKET LOSS",  value: `${last.loss.toFixed(3)}%` },
          { label: "REQ RATE",     value: `${last.reqRate?.toFixed(1)} req/s` },
          { label: "SESSIONS",     value: String(last.sessions) },
          { label: "ALLOCATED",    value: "25.0 Mbps", highlight: true },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "25 Mbps" },
          { label: "MAX LAT",   value: "50ms" },
          { label: "MAX LOSS",  value: "0.1%" },
          { label: "PRIORITY",  value: "P4 (High)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows:  history,
        title: "History — Last 50 Cycles — Student Portal Slice",
      }}
    >
      {/* Throughput */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Throughput</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gSpThrpt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2B7FFF" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[10, 40]} tickCount={4} />
              <Tooltip content={<SliceTooltip decimals={2} />} />
              <ReferenceLine y={STUDENT_PORTAL_SLA.minThrpt} stroke="#6B7280" strokeDasharray="4 3"
                label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="thrpt" name="Mbps"
                stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gSpThrpt)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* HTTP Response Latency */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">HTTP Response Latency</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 80]} tickCount={5} />
              <Tooltip content={<SliceTooltip decimals={3} />} />
              <ReferenceLine y={STUDENT_PORTAL_SLA.maxLat} stroke="#FB2C36" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Line type="monotone" dataKey="lat" name="ms"
                stroke="#2B7FFF" strokeWidth={1.5} dot={false} isAnimationActive={false} />
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
                <linearGradient id="gSpLoss" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#FB2C36" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 0.3]} tickCount={4} />
              <Tooltip content={<SliceTooltip decimals={3} />} />
              <ReferenceLine y={STUDENT_PORTAL_SLA.maxLoss} stroke="#EAB308" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="loss" name="%"
                stroke="#FB2C36" strokeWidth={1.5} fill="url(#gSpLoss)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Concurrent Sessions */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Concurrent HTTP Sessions</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gSpSess" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4ADE80" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#4ADE80" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 250]} tickCount={4} />
              <Tooltip content={<SliceTooltip decimals={0} />} />
              <Area type="monotone" dataKey="sessions" name="sessions"
                stroke="#4ADE80" strokeWidth={1.5} fill="url(#gSpSess)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </SliceLayout>
  );
}
