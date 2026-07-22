import { useState, useEffect, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { SliceLayout }  from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { GENERAL_SLA, PROTO_COLORS, genGeneralTelemetry, buildGeneralHistory } from "../data/slices";

import type { SliceSharedProps } from "../types/sliceShared";

export function GeneralSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const [range,   setRange]  = useState<"1M" | "5M" | "15M">("1M");
  const [data,    setData]   = useState(() => genGeneralTelemetry(60));
  const [history]            = useState(() => buildGeneralHistory(50));

  const pts  = range === "1M" ? 60 : range === "5M" ? 300 : 900;
  const tick = useCallback(() => setData(genGeneralTelemetry(pts)), [pts]);
  useEffect(() => { tick(); const id = setInterval(tick, 3000); return () => clearInterval(id); }, [tick]);

  const last   = data[data.length - 1] ?? { thrpt: 6.2, lat: 310, loss: 3.1, https: 2.8, udp: 1.9, tcp: 1.1, dns: 0.4 };
  const slaMet = last.lat! <= GENERAL_SLA.maxLat && last.thrpt >= GENERAL_SLA.minThrpt && last.loss <= GENERAL_SLA.maxLoss;

  // Report SLA status up to slices.tsx
  useEffect(() => { onSlaChange(slaMet); }, [slaMet, onSlaChange]);

  // Protocol breakdown percentages
  const totalP = (last.https ?? 0) + (last.udp ?? 0) + (last.tcp ?? 0) + (last.dns ?? 0) || 1;
  const protoPct = {
    "HTTPS / TLS":   (((last.https ?? 0) / totalP) * 100).toFixed(1),
    "UDP Streaming": (((last.udp   ?? 0) / totalP) * 100).toFixed(1),
    "TCP File Xfer": (((last.tcp   ?? 0) / totalP) * 100).toFixed(1),
    "DNS / Other":   (((last.dns   ?? 0) / totalP) * 100).toFixed(1),
  };
  // const protoColors = [PROTO_COLORS.https, PROTO_COLORS.udp, PROTO_COLORS.tcp, PROTO_COLORS.dns];

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
      telemetryLabel="Telemetry Timeline — Variable Background Traffic (eMBB)"
      header={{
        name:     "General",
        priority: "P1",
        slaMet,
        metricChips: [
          `${last.thrpt.toFixed(1)} Mbps`,
          `${last.lat!.toFixed(1)}ms`,
          `${last.loss.toFixed(2)}%`,
        ],
        extraChips: (
          <>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border" style={{ color: PROTO_COLORS.https, borderColor: PROTO_COLORS.https + "44" }}>
              HTTPS {protoPct["HTTPS / TLS"]}%
            </span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded border" style={{ color: PROTO_COLORS.udp, borderColor: PROTO_COLORS.udp + "44" }}>
              UDP {protoPct["UDP Streaming"]}%
            </span>
          </>
        ),
        slaTargets: "5 Mbps min\u00a0·\u00a0500ms max\u00a0·\u00a010% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT",  value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "E2E LATENCY", value: `${last.lat!.toFixed(1)}ms` },
          { label: "PACKET LOSS", value: `${last.loss.toFixed(2)}%` },
          { label: "ALLOCATED",   value: "5.0 Mbps", highlight: true },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "5 Mbps" },
          { label: "MAX LAT",   value: "500ms" },
          { label: "MAX LOSS",  value: "10%" },
          { label: "PRIORITY",  value: "P1 (Lowest)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows:  history,
        title: "History — Last 50 Cycles — General Traffic Slice",
      }}
    >
      {/* Throughput */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Throughput</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="gGnThrpt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2B7FFF" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 15]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={GENERAL_SLA.minThrpt} stroke="#6B7280" strokeDasharray="4 3"
                label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="thrpt" name="Mbps"
                stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gGnThrpt)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* E2E Latency */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">E2E Latency</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 600]} tickCount={5} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={GENERAL_SLA.maxLat} stroke="#FB2C36" strokeDasharray="4 3"
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
                <linearGradient id="gGnLoss" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#FB2C36" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 12]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <ReferenceLine y={GENERAL_SLA.maxLoss} stroke="#EAB308" strokeDasharray="4 3"
                label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }} />
              <Area type="monotone" dataKey="loss" name="%"
                stroke="#FB2C36" strokeWidth={1.5} fill="url(#gGnLoss)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Protocol Distribution (stacked area) */}
      <div className="bg-zinc-950">
        <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]"><span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Protocol Breakdown</span></div>
        <div style={{ padding: "8px 4px 4px" }}>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="2 4" />
              <XAxis dataKey="i" hide />
              <YAxis domain={[0, 15]} tickCount={4} />
              <Tooltip content={<SliceTooltip />} />
              <Area type="monotone" stackId="1" dataKey="dns"   name="DNS/Other"  stroke={PROTO_COLORS.dns}   fill={PROTO_COLORS.dns   + "30"} strokeWidth={1} dot={false} isAnimationActive={false} />
              <Area type="monotone" stackId="1" dataKey="tcp"   name="TCP File"   stroke={PROTO_COLORS.tcp}   fill={PROTO_COLORS.tcp   + "30"} strokeWidth={1} dot={false} isAnimationActive={false} />
              <Area type="monotone" stackId="1" dataKey="udp"   name="UDP Stream" stroke={PROTO_COLORS.udp}   fill={PROTO_COLORS.udp   + "30"} strokeWidth={1} dot={false} isAnimationActive={false} />
              <Area type="monotone" stackId="1" dataKey="https" name="HTTPS/TLS"  stroke={PROTO_COLORS.https} fill={PROTO_COLORS.https + "30"} strokeWidth={1} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/*
        The Protocol Distribution bar chart from the original right column is
        now also rendered inline here as a fifth panel (optional slot outside the
        2×2 grid) — or can be added to the right column via a custom slot.
        Keeping it in the chart area keeps SliceLayout generic.
      */}
    </SliceLayout>
  );
}
