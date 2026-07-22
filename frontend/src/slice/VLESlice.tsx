import { Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, LineChart, ReferenceLine } from "recharts";
import { SliceLayout } from "../components/primitives/Slicelayout";
import { SliceTooltip } from "../components/primitives/SliceTooltip";
import { ChartPanel } from "../components/primitives/slice-dashboard/chartpanel";
import { VLE_SLA, VLE_RECENT, genVLETelemetry, buildVLEHistory } from "../data/slices";
import { useReportSla } from "#/hooks/use-reportsla";
import { useSliceTelemetry } from "#/hooks/use-slicetelemetry";

import type { SliceSharedProps } from "../types/sliceShared";

export function VLESlice({
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: SliceSharedProps) {
  const { range, setRange, data, history } = useSliceTelemetry(
    genVLETelemetry,
    buildVLEHistory,
    3000,
  );

  const last = data[data.length - 1] ?? { thrpt: 48.2, lat: 1.2, loss: 0.0, alloc: 50.0 };
  const slaMet =
    last.lat <= VLE_SLA.maxLat &&
    last.thrpt >= VLE_SLA.minThrpt &&
    last.loss <= VLE_SLA.maxLoss;

  useReportSla(slaMet, onSlaChange);

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      timeRange={range}
      onTimeRangeChange={setRange}
      telemetryLabel="Telemetry Timeline"
      header={{
        name: "VLE",
        priority: "P5",
        slaMet,
        metricChips: [
          `${last.thrpt.toFixed(1)} Mbps`,
          `${last.lat.toFixed(1)}ms`,
          `${last.loss.toFixed(1)}%`,
        ],
        slaTargets: "50 Mbps min · 100ms max · 0.5% max",
      }}
      right={{
        currentState: [
          { label: "THROUGHPUT", value: `${last.thrpt.toFixed(1)} Mbps` },
          { label: "LATENCY", value: `${last.lat.toFixed(1)}ms` },
          { label: "PACKET LOSS", value: `${last.loss.toFixed(1)}%` },
          { label: "ALLOCATED", value: "50.0 Mbps", highlight: true },
        ],
        slaThresholds: [
          { label: "MIN THRPT", value: "50 Mbps" },
          { label: "MAX LAT", value: "100ms" },
          { label: "MAX LOSS", value: "0.5%" },
          { label: "PRIORITY", value: "P5 (Critical)", highlight: true },
        ],
        recentCycles: VLE_RECENT.map((c) => ({ ...c })),
      }}
      history={{ rows: history, title: "History — Last 50 Cycles" }}
    >
      <ChartPanel title="Throughput">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
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
            y={VLE_SLA.minThrpt}
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
            fill="url(#gVleThrpt)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Latency">
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 10]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <ReferenceLine
            y={VLE_SLA.maxLat}
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
            y={VLE_SLA.maxLoss}
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
            fill="url(#gVleLoss)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>

      <ChartPanel title="Allocation History">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="gVleAlloc" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2B7FFF" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#2B7FFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis dataKey="i" hide />
          <YAxis domain={[40, 55]} tickCount={4} />
          <Tooltip content={<SliceTooltip />} />
          <Area
            type="stepAfter"
            dataKey="alloc"
            name="Mbps"
            stroke="#2B7FFF"
            strokeWidth={1.5}
            fill="url(#gVleAlloc)"
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartPanel>
    </SliceLayout>
  );
}