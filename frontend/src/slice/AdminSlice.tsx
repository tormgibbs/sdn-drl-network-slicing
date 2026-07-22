import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { ADMIN_SLA, genAdminTelemetry, buildAdminHistory } from "../data/slices";
import { useSliceTelemetry } from "#/hooks/use-slicetelemetry";
import { useReportSla } from "#/hooks/use-reportsla";
import { buildRecentCycles } from "../utils/slice-utils"; 
import type { SliceSharedProps } from "../types/sliceShared";

export function AdminSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { range, setRange, data, history } = useSliceTelemetry(
    genAdminTelemetry,
    buildAdminHistory,
    3000,
  );

  const last = data[data.length - 1] ?? { thrpt: 11.2, lat: 82, loss: 0.3, txRate: 3.8, flows: 47 };
  const slaMet =
    last.lat! <= ADMIN_SLA.maxLat &&
    last.thrpt >= ADMIN_SLA.minThrpt &&
    last.loss <= ADMIN_SLA.maxLoss;

  useReportSla(slaMet, onSlaChange);

const recentCycles = buildRecentCycles(history);

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange={range}
      onTimeRangeChange={setRange}
      telemetryLabel="Telemetry Timeline — Institutional Traffic (eMBB · Stable)"
      header={{
        name: "Admin Systems",
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
          { label: "THROUGHPUT", value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "TX LATENCY", value: `${last.lat!.toFixed(1)}ms` },
          { label: "PACKET LOSS", value: `${last.loss.toFixed(2)}%` },
          { label: "TX RATE", value: `${last.txRate?.toFixed(1)} tx/s` },
          { label: "ACTIVE FLOWS", value: String(last.flows) },
          { label: "ALLOCATED", value: "10.0 Mbps", highlight: true },
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
        rows: history,
        title: "History — Last 50 Cycles — Admin Systems Slice",
      }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
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
            y={ADMIN_SLA.minThrpt}
            stroke="#6B7280"
            strokeDasharray="4 3"
            label={{
              value: "SLA MIN",
              position: "insideBottomLeft",
              fill: "#6B7280",
              fontSize: 9,
              fontFamily: "JetBrains Mono,monospace",
            }}
          />
          <Area
            type="monotone"
            dataKey="thrpt"
            name="Mbps"
            stroke="#EAB308"
            strokeWidth={1.5}
            fill="url(#gAdThrpt)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Transaction Latency">
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 200]} tickCount={5} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={ADMIN_SLA.maxLat}
            stroke="#FB2C36"
            strokeDasharray="4 3"
            label={{
              value: "SLA MAX",
              position: "insideTopLeft",
              fill: "#FB2C36",
              fontSize: 9,
              fontFamily: "JetBrains Mono,monospace",
            }}
          />
          <Line
            type="monotone"
            dataKey="lat"
            name="ms"
            stroke="#EAB308"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ChartPanel>

      <ChartPanel title="Packet Loss">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
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
            y={ADMIN_SLA.maxLoss}
            stroke="#EAB308"
            strokeDasharray="4 3"
            label={{
              value: "SLA MAX",
              position: "insideTopLeft",
              fill: "#EAB308",
              fontSize: 9,
              fontFamily: "JetBrains Mono,monospace",
            }}
          />
          <Area
            type="monotone"
            dataKey="loss"
            name="%"
            stroke="#FB2C36"
            strokeWidth={1.5}
            fill="url(#gAdLoss)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Transaction Rate">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gAdTx" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EAB308" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 10]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <Area
            type="stepAfter"
            dataKey="txRate"
            name="tx/s"
            stroke="#EAB308"
            strokeWidth={1.5}
            fill="url(#gAdTx)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}