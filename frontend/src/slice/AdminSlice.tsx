import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { useLiveSliceData, type SliceSLA } from "#/hooks/use-live-slice-data";
import { useReportSla } from "#/hooks/use-reportsla";
import type { SliceSharedProps } from "../types/sliceShared";

const ADMIN_SLA: SliceSLA = { minThrpt: 10_000_000, maxLat: 150, maxLoss: 1.0 };

export function AdminSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { current, history, slaMet, allocationBps } = useLiveSliceData("admin", ADMIN_SLA);

  useReportSla(slaMet ?? false, onSlaChange);

  const thrptMbps = current ? current.tx_throughput_bps / 1_000_000 : null;
  const allocMbps = allocationBps !== null ? allocationBps / 1_000_000 : null;

  const chartData = history.map((p, i) => ({
    i,
    thrpt: p.tx_throughput_bps / 1_000_000,
    lat: p.latency_ms,
    loss: p.loss_pct,
  }));

  const evalSla = (lat: number, thrpt: number, loss: number) =>
    (lat <= ADMIN_SLA.maxLat && thrpt >= ADMIN_SLA.minThrpt && loss <= ADMIN_SLA.maxLoss
      ? "MET"
      : "VIOLATION") as "MET" | "VIOLATION";

  const recentCycles = history
    .slice(-7)
    .reverse()
    .map((p, i) => ({
      id: `admin-${history.length - i}`,
      thrpt: p.tx_throughput_bps / 1_000_000,
      lat: p.latency_ms,
      status: evalSla(p.latency_ms, p.tx_throughput_bps, p.loss_pct),
    }));

  const historyRows = history.map((p, i) => ({
    ts: new Date(p.timestamp).toISOString(),
    id: `admin-${i}`,
    thrpt: p.tx_throughput_bps / 1_000_000,
    lat: p.latency_ms,
    loss: p.loss_pct,
    alloc: allocMbps ?? 0,
    sla: evalSla(p.latency_ms, p.tx_throughput_bps, p.loss_pct),
  }));

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange="1M"
      onTimeRangeChange={() => {}}
      telemetryLabel="Telemetry Timeline — Institutional Traffic (eMBB · Stable)"
      header={{
        name: "Admin Systems",
        priority: "P3",
        slaMet: slaMet,
        metricChips: current
          ? [
              `${thrptMbps!.toFixed(1)} Mbps`,
              `${current.latency_ms.toFixed(1)}ms`,
              `${current.loss_pct.toFixed(2)}%`,
            ]
          : ["— Mbps", "—ms", "—%"],
        slaTargets: "10 Mbps min\u00a0·\u00a0150ms max\u00a0·\u00a01% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT", value: current ? `${thrptMbps!.toFixed(1)} Mbps` : "—" },
          { label: "TX LATENCY", value: current ? `${current.latency_ms.toFixed(1)}ms` : "—" },
          { label: "PACKET LOSS", value: current ? `${current.loss_pct.toFixed(2)}%` : "—" },
          {
            label: "ALLOCATED",
            value: allocMbps !== null ? `${allocMbps.toFixed(1)} Mbps` : "AGENT INACTIVE",
            highlight: true,
          },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "10 Mbps" },
          { label: "MAX LAT", value: "150ms" },
          { label: "MAX LOSS", value: "1%" },
          { label: "PRIORITY", value: "P3 (Med)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows: historyRows,
        title: "History — Last 50 Cycles — Admin Systems Slice",
      }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gAdThrpt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EAB308" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[5, 20]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={10}
            stroke="#6B7280"
            strokeDasharray="4 3"
            label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="thrpt" name="Mbps" stroke="#EAB308" strokeWidth={1.5} fill="url(#gAdThrpt)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Transaction Latency">
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 200]} tickCount={5} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={150}
            stroke="#FB2C36"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Line type="monotone" dataKey="lat" name="ms" stroke="#EAB308" strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartPanel>

      <ChartPanel title="Packet Loss">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gAdLoss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FB2C36" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 2]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={1.0}
            stroke="#EAB308"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="loss" name="%" stroke="#FB2C36" strokeWidth={1.5} fill="url(#gAdLoss)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}