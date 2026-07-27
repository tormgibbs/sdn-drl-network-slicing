import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { useLiveSliceData, type SliceSLA } from "#/hooks/use-live-slice-data";
import { useReportSla } from "#/hooks/use-reportsla";
import { initialData } from "#/data/dashboard";
import { formatBps } from "#/lib/format";
import type { SliceSharedProps } from "../types/sliceShared";

// Sourced from initialData.slices.student_portal — the single place SLA
// thresholds are defined, kept in sync with config/slices.yaml. Previously
// this file held its own hardcoded { minThrpt: 25_000_000, ... } constant —
// ~8x higher than the real backend config (real value is 3_000_000). Do not
// hardcode values here again — if slices.yaml changes, update dashboard.ts
// and this reads the new value automatically.
const STUDENT_PORTAL_SLA: SliceSLA = {
  minThrpt: initialData.slices.student_portal.min_throughput_bps,
  maxLat: initialData.slices.student_portal.max_latency_ms,
  maxLoss: initialData.slices.student_portal.max_loss_pct,
};

export function StudentPortalSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { current, history, slaMet, allocationBps } = useLiveSliceData("student_portal", STUDENT_PORTAL_SLA);

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
    (lat <= STUDENT_PORTAL_SLA.maxLat && thrpt >= STUDENT_PORTAL_SLA.minThrpt && loss <= STUDENT_PORTAL_SLA.maxLoss
      ? "MET"
      : "VIOLATION") as "MET" | "VIOLATION";

  const recentCycles = history
    .slice(-7)
    .reverse()
    .map((p, i) => ({
      id: `sp-${history.length - i}`,
      thrpt: p.tx_throughput_bps / 1_000_000,
      lat: p.latency_ms,
      status: evalSla(p.latency_ms, p.tx_throughput_bps, p.loss_pct),
    }));

  const historyRows = history.map((p, i) => ({
    ts: new Date(p.timestamp).toISOString(),
    id: `sp-${i}`,
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
      telemetryLabel="Telemetry Timeline — HTTP Transaction Traffic (eMBB)"
      header={{
        name: "Student Portal",
        priority: "P4",
        slaMet: slaMet,
        metricChips: current
          ? [
              `${thrptMbps!.toFixed(1)} Mbps`,
              `${current.latency_ms.toFixed(1)}ms`,
              `${current.loss_pct.toFixed(3)}%`,
            ]
          : ["— Mbps", "—ms", "—%"],
        slaTargets: `${formatBps(STUDENT_PORTAL_SLA.minThrpt)} min\u00a0·\u00a0${STUDENT_PORTAL_SLA.maxLat}ms max\u00a0·\u00a0${STUDENT_PORTAL_SLA.maxLoss}% max`,
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT", value: current ? `${thrptMbps!.toFixed(1)} Mbps` : "—" },
          { label: "RESP LATENCY", value: current ? `${current.latency_ms.toFixed(1)}ms` : "—" },
          { label: "PACKET LOSS", value: current ? `${current.loss_pct.toFixed(3)}%` : "—" },
          {
            label: "ALLOCATED",
            value: allocMbps !== null ? `${allocMbps.toFixed(1)} Mbps` : "AGENT INACTIVE",
            highlight: true,
          },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: formatBps(STUDENT_PORTAL_SLA.minThrpt) },
          { label: "MAX LAT", value: `${STUDENT_PORTAL_SLA.maxLat}ms` },
          { label: "MAX LOSS", value: `${STUDENT_PORTAL_SLA.maxLoss}%` },
          { label: "PRIORITY", value: "P4 (High)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows: historyRows,
        title: "History — Last 50 Cycles — Student Portal Slice",
      }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gSpThrpt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2B7FFF" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          {/* Domain widened from the old [10, 40] (tuned around the old
              wrong 25 Mbps threshold) to [0, 15]. The corrected 3 Mbps SLA
              MIN line and real live throughput (observed ~1-11 Mbps live)
              both would have fallen entirely below the old domain's floor
              of 10. */}
          <YAxis domain={[0, 15]} tickCount={4} />
          <Tooltip content={<SliceTooltip decimals={2} />} />
          <ReferenceLine
            y={STUDENT_PORTAL_SLA.minThrpt / 1_000_000}
            stroke="#6B7280"
            strokeDasharray="4 3"
            label={{ value: "SLA MIN", position: "insideBottomLeft", fill: "#6B7280", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="thrpt" name="Mbps" stroke="#2B7FFF" strokeWidth={1.5} fill="url(#gSpThrpt)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="HTTP Response Latency">
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 80]} tickCount={5} />
          <Tooltip content={<SliceTooltip decimals={3} />} />
          <ReferenceLine
            y={STUDENT_PORTAL_SLA.maxLat}
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
            <linearGradient id="gSpLoss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FB2C36" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#FB2C36" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 0.3]} tickCount={4} />
          <Tooltip content={<SliceTooltip decimals={3} />} />
          <ReferenceLine
            y={STUDENT_PORTAL_SLA.maxLoss}
            stroke="#EAB308"
            strokeDasharray="4 3"
            label={{ value: "SLA MAX", position: "insideTopLeft", fill: "#EAB308", fontSize: 9, fontFamily: "JetBrains Mono,monospace" }}
          />
          <Area type="monotone" dataKey="loss" name="%" stroke="#FB2C36" strokeWidth={1.5} fill="url(#gSpLoss)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}