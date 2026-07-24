import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { useLiveSliceData, type SliceSLA } from "#/hooks/use-live-slice-data";
import { useReportSla } from "#/hooks/use-reportsla";
import type { SliceSharedProps } from "../types/sliceShared";

const VLE_SLA: SliceSLA = { minThrpt: 50_000_000, maxLat: 100, maxLoss: 0.5 };

export function VLESlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { current, history, slaMet, allocationBps } = useLiveSliceData("vle", VLE_SLA);

  useReportSla(slaMet ?? false, onSlaChange);

  const thrptMbps = current ? current.tx_throughput_bps / 1_000_000 : null;
  const allocMbps = allocationBps !== null ? allocationBps / 1_000_000 : null;

  const chartData = history.map((p, i) => ({
    i,
    thrpt: p.tx_throughput_bps / 1_000_000,
    lat: p.latency_ms,
    loss: p.loss_pct,
  }));

  // Synthesized id (structural bookkeeping, not a claimed backend value) +
  // real ts from accumulated history, per team decision.
  const recentCycles = history
    .slice(-7)
    .reverse()
    .map((p, i) => ({
      id: `vle-${history.length - i}`,
      thrpt: p.tx_throughput_bps / 1_000_000,
      lat: p.latency_ms,
      status: (p.latency_ms <= VLE_SLA.maxLat &&
        p.tx_throughput_bps >= VLE_SLA.minThrpt &&
        p.loss_pct <= VLE_SLA.maxLoss
        ? "MET"
        : "VIOLATION") as "MET" | "VIOLATION",
    }));

  const historyRows = history.map((p, i) => ({
    ts: new Date(p.timestamp).toISOString(),
    id: `vle-${i}`,
    thrpt: p.tx_throughput_bps / 1_000_000,
    lat: p.latency_ms,
    loss: p.loss_pct,
    alloc: allocMbps ?? 0,
    sla: (p.latency_ms <= VLE_SLA.maxLat &&
      p.tx_throughput_bps >= VLE_SLA.minThrpt &&
      p.loss_pct <= VLE_SLA.maxLoss
      ? "MET"
      : "VIOLATION") as "MET" | "VIOLATION",
  }));

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange="1M"
      onTimeRangeChange={() => {}}
      telemetryLabel="Telemetry Timeline"
      header={{
        name: "VLE",
        priority: "P5",
        slaMet: slaMet,
        metricChips: current
          ? [
              `${thrptMbps!.toFixed(1)} Mbps`,
              `${current.latency_ms.toFixed(1)}ms`,
              `${current.loss_pct.toFixed(1)}%`,
            ]
          : ["— Mbps", "—ms", "—%"],
        slaTargets: "50 Mbps min · 100ms max · 0.5% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT", value: current ? `${thrptMbps!.toFixed(1)} Mbps` : "—" },
          { label: "LATENCY", value: current ? `${current.latency_ms.toFixed(1)}ms` : "—" },
          { label: "PACKET LOSS", value: current ? `${current.loss_pct.toFixed(1)}%` : "—" },
          {
            label: "ALLOCATED",
            value: allocMbps !== null ? `${allocMbps.toFixed(1)} Mbps` : "AGENT INACTIVE",
            highlight: true,
          },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "50 Mbps" },
          { label: "MAX LAT", value: "100ms" },
          { label: "MAX LOSS", value: "0.5%" },
          { label: "PRIORITY", value: "P5 (Critical)", highlight: true },
        ],
        recentCycles,
      }}
      history={{ rows: historyRows, title: "History — Last 50 Cycles" }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gVleThrpt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2B7FFF" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[30, 60]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={50}
            stroke="#6B7280"
            strokeDasharray="4 3"
            label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="thrpt" name="Mbps" stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gVleThrpt)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Latency">
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 10]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={100}
            stroke="#FB2C36"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Line type="monotone" dataKey="lat" name="ms" stroke="#2B7FFF" strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartPanel>

      <ChartPanel title="Packet Loss">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gVleLoss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FB2C36" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 2]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={0.5}
            stroke="#EAB308"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="loss" name="%" stroke="#FB2C36" strokeWidth={1.5} fill="url(#gVleLoss)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}