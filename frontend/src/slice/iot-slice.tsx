import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { useLiveSliceData, type SliceSLA } from "#/hooks/use-live-slice-data";
import { useReportSla } from "#/hooks/use-reportsla";
import { initialData } from "#/data/dashboard";
import { formatBps } from "#/lib/format";
import type { SliceSharedProps } from "../types/sliceShared";

// Sourced from initialData.slices.iot — the single place SLA thresholds are
// defined, kept in sync with config/slices.yaml. This value already
// happened to match slices.yaml before this change (64_000), so this isn't
// fixing an active bug — it's closing the same future-drift risk that let
// the other four slices' hardcoded constants go stale silently. Do not
// hardcode values here again — if slices.yaml changes, update dashboard.ts
// and this reads the new value automatically.
const IOT_SLA: SliceSLA = {
  minThrpt: initialData.slices.iot.min_throughput_bps,
  maxLat: initialData.slices.iot.max_latency_ms,
  maxLoss: initialData.slices.iot.max_loss_pct,
};

export function IoTSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { current, history, slaMet, allocationBps } = useLiveSliceData("iot", IOT_SLA);

  useReportSla(slaMet ?? false, onSlaChange);

  const thrptKbps = current ? (current.tx_throughput_bps / 1000) : null;
  const allocKbps = allocationBps !== null ? allocationBps / 1000 : null;

  const chartData = history.map((p, i) => ({
    i,
    thrpt: p.tx_throughput_bps / 1000, // Kbps, matches IoT's original unit convention
    lat: p.latency_ms,
    loss: p.loss_pct,
  }));

  const evalSla = (lat: number, thrpt: number, loss: number) =>
    (lat <= IOT_SLA.maxLat && thrpt >= IOT_SLA.minThrpt && loss <= IOT_SLA.maxLoss
      ? "MET"
      : "VIOLATION") as "MET" | "VIOLATION";

  const recentCycles = history
    .slice(-7)
    .reverse()
    .map((p, i) => ({
      id: `iot-${history.length - i}`,
      thrpt: +(p.tx_throughput_bps / 1000).toFixed(2),
      lat: p.latency_ms,
      status: evalSla(p.latency_ms, p.tx_throughput_bps, p.loss_pct),
    }));

  const historyRows = history.map((p, i) => ({
    ts: new Date(p.timestamp).toISOString(),
    id: `iot-${i}`,
    thrpt: p.tx_throughput_bps / 1000,
    lat: p.latency_ms,
    loss: p.loss_pct,
    alloc: allocKbps ?? 0,
    sla: evalSla(p.latency_ms, p.tx_throughput_bps, p.loss_pct),
  }));

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange="1M"
      onTimeRangeChange={() => {}}
      telemetryLabel="Telemetry Timeline — Heartbeat / Control Traffic (mMTC)"
      header={{
        name: "IoT",
        priority: "P2",
        slaMet: slaMet,
        metricChips: current
          ? [
              `${thrptKbps!.toFixed(2)} Kbps`,
              `${current.latency_ms.toFixed(1)}ms`,
              `${current.loss_pct.toFixed(2)}%`,
            ]
          : ["— Kbps", "—ms", "—%"],
        slaTargets: `${formatBps(IOT_SLA.minThrpt)} min\u00a0·\u00a0${IOT_SLA.maxLat}ms max\u00a0·\u00a0${IOT_SLA.maxLoss}% max`,
      }}
      right={{
        currentState: [
          { label: "BANDWIDTH", value: current ? `${thrptKbps!.toFixed(2)} Kbps` : "—" },
          { label: "HB LATENCY", value: current ? `${current.latency_ms.toFixed(1)}ms` : "—" },
          { label: "PACKET LOSS", value: current ? `${current.loss_pct.toFixed(2)}%` : "—" },
          {
            label: "ALLOCATED",
            value: allocKbps !== null ? `${allocKbps.toFixed(2)} Kbps` : "AGENT INACTIVE",
            highlight: true,
          },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: formatBps(IOT_SLA.minThrpt) },
          { label: "MAX LAT", value: `${IOT_SLA.maxLat}ms` },
          { label: "MAX LOSS", value: `${IOT_SLA.maxLoss}%` },
          { label: "PRIORITY", value: "P2 (Low)", highlight: true },
        ],
        recentCycles,
        recentCols: ["LAT", "LOSS"],
      }}
      history={{
        rows: historyRows,
        title: "History — Last 50 Cycles — IoT Slice (mMTC)",
        thrptHeader: "BW (KBPS)",
        renderThrpt: (row) => row.thrpt.toFixed(2),
        renderAlloc: () => (allocKbps !== null ? allocKbps.toFixed(2) : "—"),
      }}
    >
      <ChartPanel title="Heartbeat Latency">
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 250]} tickCount={5} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={IOT_SLA.maxLat}
            stroke="#FB2C36"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#FB2C36", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Line type="monotone" dataKey="lat" name="ms" stroke="#4ADE80" strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartPanel>

      <ChartPanel title="Packet Loss">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gIoLoss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FB2C36" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 6]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={IOT_SLA.maxLoss}
            stroke="#EAB308"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="loss" name="%" stroke="#FB2C36" strokeWidth={1.5} fill="url(#gIoLoss)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}