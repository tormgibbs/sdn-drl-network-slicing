import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { STUDENT_PORTAL_SLA, genStudentPortalTelemetry, buildStudentPortalHistory } from "../data/slices";
import { useSliceTelemetry } from "#/hooks/use-slicetelemetry";
import { useReportSla } from "#/hooks/use-reportsla";
import { buildRecentCycles } from "../utils/slice-utils";
import type { SliceSharedProps } from "../types/sliceShared";

export function StudentPortalSlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { range, setRange, data, history } = useSliceTelemetry(
    genStudentPortalTelemetry,
    buildStudentPortalHistory,
    3000,
  );

  const last = data[data.length - 1] ?? { thrpt: 26.1, lat: 28, loss: 0.0, reqRate: 5.2, sessions: 142 };
  const slaMet =
    last.lat! <= STUDENT_PORTAL_SLA.maxLat &&
    last.thrpt >= STUDENT_PORTAL_SLA.minThrpt &&
    last.loss <= STUDENT_PORTAL_SLA.maxLoss;

  useReportSla(slaMet, onSlaChange);

  const recentCycles = buildRecentCycles(history);

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange={range}
      onTimeRangeChange={setRange}
      telemetryLabel="Telemetry Timeline — HTTP Transaction Traffic (eMBB)"
      header={{
        name: "Student Portal",
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
          { label: "THROUGHPUT", value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "RESP LATENCY", value: `${last.lat!.toFixed(1)}ms` },
          { label: "PACKET LOSS", value: `${last.loss.toFixed(3)}%` },
          { label: "REQ RATE", value: `${last.reqRate?.toFixed(1)} req/s` },
          { label: "SESSIONS", value: String(last.sessions) },
          { label: "ALLOCATED", value: "25.0 Mbps", highlight: true },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "25 Mbps" },
          { label: "MAX LAT", value: "50ms" },
          { label: "MAX LOSS", value: "0.1%" },
          { label: "PRIORITY", value: "P4 (High)", highlight: true },
        ],
        recentCycles,
      }}
      history={{
        rows: history,
        title: "History — Last 50 Cycles — Student Portal Slice",
      }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gSpThrpt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2B7FFF" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[10, 40]} tickCount={4} />
          <Tooltip content={<SliceTooltip decimals={2} />} />
          <ReferenceLine
            y={STUDENT_PORTAL_SLA.minThrpt}
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
            stroke="#2B7FFF"
            strokeWidth={1.5}
            fill="url(#gSpThrpt)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="HTTP Response Latency">
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 80]} tickCount={5} />
          <Tooltip content={<SliceTooltip decimals={3} />} />
          <ReferenceLine
            y={STUDENT_PORTAL_SLA.maxLat}
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
            stroke="#2B7FFF"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ChartPanel>

      <ChartPanel title="Packet Loss">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
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
            fill="url(#gSpLoss)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Concurrent HTTP Sessions">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gSpSess" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#4ADE80" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#4ADE80" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 250]} tickCount={4} />
          <Tooltip content={<SliceTooltip decimals={0} />} />
          <Area
            type="monotone"
            dataKey="sessions"
            name="sessions"
            stroke="#4ADE80"
            strokeWidth={1.5}
            fill="url(#gSpSess)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}