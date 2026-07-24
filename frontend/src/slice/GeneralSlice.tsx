import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { useLiveSliceData, type SliceSLA } from "#/hooks/use-live-slice-data";
import { useReportSla } from "#/hooks/use-reportsla";
import type { SliceSharedProps } from "../types/sliceShared";

const GENERAL_SLA: SliceSLA = { minThrpt: 5_000_000, maxLat: 500, maxLoss: 10.0 };

export function GeneralSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { current, history, slaMet, allocationBps } = useLiveSliceData("general", GENERAL_SLA);

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
    (lat <= GENERAL_SLA.maxLat && thrpt >= GENERAL_SLA.minThrpt && loss <= GENERAL_SLA.maxLoss
      ? "MET"
      : "VIOLATION") as "MET" | "VIOLATION";

  const recentCycles = history
    .slice(-7)
    .reverse()
    .map((p, i) => ({
      id: `gen-${history.length - i}`,
      thrpt: p.tx_throughput_bps / 1_000_000,
      lat: p.latency_ms,
      status: evalSla(p.latency_ms, p.tx_throughput_bps, p.loss_pct),
    }));

  const historyRows = history.map((p, i) => ({
    ts: new Date(p.timestamp).toISOString(),
    id: `gen-${i}`,
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
      telemetryLabel="Telemetry Timeline — Variable Background Traffic (eMBB)"
      header={{
        name: "General",
        priority: "P1",
        slaMet: slaMet,
        metricChips: current
          ? [
              `${thrptMbps!.toFixed(1)} Mbps`,
              `${current.latency_ms.toFixed(1)}ms`,
              `${current.loss_pct.toFixed(2)}%`,
            ]
          : ["— Mbps", "—ms", "—%"],
        slaTargets: "5 Mbps min\u00a0·\u00a0500ms max\u00a0·\u00a010% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT", value: current ? `${thrptMbps!.toFixed(1)} Mbps` : "—" },
          { label: "E2E LATENCY", value: current ? `${current.latency_ms.toFixed(1)}ms` : "—" },
          { label: "PACKET LOSS", value: current ? `${current.loss_pct.toFixed(2)}%` : "—" },
          {
            label: "ALLOCATED",
            value: allocMbps !== null ? `${allocMbps.toFixed(1)} Mbps` : "AGENT INACTIVE",
            highlight: true,
          },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "5 Mbps" },
          { label: "MAX LAT", value: "500ms" },
          { label: "MAX LOSS", value: "10%" },
          { label: "PRIORITY", value: "P1 (Lowest)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows: historyRows,
        title: "History — Last 50 Cycles — General Traffic Slice",
      }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gGnThrpt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2B7FFF" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 15]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={5}
            stroke="#6B7280"
            strokeDasharray="4 3"
            label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="thrpt" name="Mbps" stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gGnThrpt)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="E2E Latency">
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 600]} tickCount={5} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={500}
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
            <linearGradient id="gGnLoss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FB2C36" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 12]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={10.0}
            stroke="#EAB308"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="loss" name="%" stroke="#FB2C36" strokeWidth={1.5} fill="url(#gGnLoss)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}