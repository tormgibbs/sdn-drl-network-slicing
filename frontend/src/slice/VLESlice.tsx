import { useState, useEffect, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { SliceLayout }  from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { VLE_SLA, VLE_RECENT, genVLETelemetry, buildVLEHistory } from "../data/slices";
import type { SliceSharedProps } from "../types/sliceShared";

export function VLESlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const [range,   setRange]  = useState<"1M" | "5M" | "15M">("1M");
  const [data,    setData]   = useState(() => genVLETelemetry(60));
  const [history]            = useState(() => buildVLEHistory(50));

  const pts  = range === "1M" ? 60 : range === "5M" ? 300 : 900;
  const tick = useCallback(() => setData(genVLETelemetry(pts)), [pts]);
  useEffect(() => { tick(); const id = setInterval(tick, 3000); return () => clearInterval(id); }, [tick]);

  const last   = data[data.length - 1] ?? { thrpt: 48.2, lat: 1.2, loss: 0.0, alloc: 50.0 };
  const slaMet = last.lat <= VLE_SLA.maxLat && last.thrpt >= VLE_SLA.minThrpt && last.loss <= VLE_SLA.maxLoss;

  // Report SLA status up to slices.tsx so the switcher dot stays live
  useEffect(() => { onSlaChange(slaMet); }, [slaMet, onSlaChange]);

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange={range}
      onTimeRangeChange={setRange}
      telemetryLabel="Telemetry Timeline"
      header={{
        name:        "VLE",
        priority:    "P5",
        slaMet,
        metricChips: [`${last.thrpt.toFixed(1)} Mbps`, `${last.lat.toFixed(1)}ms`, `${last.loss.toFixed(1)}%`],
        slaTargets:  "50 Mbps min · 100ms max · 0.5% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT",  value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "LATENCY",     value: `${last.lat.toFixed(1)}ms` },
          { label: "PACKET LOSS", value: `${last.loss.toFixed(1)}%` },
          { label: "ALLOCATED",   value: "50.0 Mbps", highlight: true },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "50 Mbps" },
          { label: "MAX LAT",   value: "100ms" },
          { label: "MAX LOSS",  value: "0.5%" },
          { label: "PRIORITY",  value: "P5 (Critical)", highlight: true },
        ],
        recentCycles: VLE_RECENT.map((c) => ({ ...c })),
      }}
      history={{ rows: history, title: "History — Last 50 Cycles" }}
    >
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Throughput</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gVleThrpt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2B7FFF" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[30, 60]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={VLE_SLA.minThrpt} stroke="#6B7280" strokeDasharray="4 3"
                label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="thrpt" name="Mbps"
                stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gVleThrpt)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Latency</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 10]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={VLE_SLA.maxLat} stroke="#FB2C36" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Line type="monotone" dataKey="lat" name="ms"
                stroke="#2B7FFF" strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Packet Loss</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gVleLoss" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#FB2C36" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 2]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={VLE_SLA.maxLoss} stroke="#EAB308" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="loss" name="%"
                stroke="#FB2C36" strokeWidth={1.5} fill="url(#gVleLoss)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Allocation History</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gVleAlloc" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2B7FFF" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[40, 55]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <Area type="stepAfter" dataKey="alloc" name="Mbps"
                stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gVleAlloc)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </SliceLayout>
  );
}
