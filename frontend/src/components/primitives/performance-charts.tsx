import { useState } from "react";
import { Line, LineChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { initialData } from "#/data/dashboard";
import type { SliceMetricPoint } from "#/stores/live-metrics-store";
import type { SliceKey } from "#/types/slice";

// How many of the most recent real ticks to show per range. Real data
// arrives at whatever cadence the backend broadcasts (not a fixed interval
// we control), so these are point-counts, not literal minutes — kept as a
// familiar mapping to the old "1M/5M/15M" labels rather than inventing new
// UI, but the underlying meaning has changed from "N minutes of mock data"
// to "N most recent real points, capped by history buffer size".
const TIME_RANGE_POINTS = { "1M": 12, "5M": 60, "15M": 100 };

const SLICE_LINES: { key: SliceKey; stroke: string }[] = [
  { key: "vle", stroke: "#3b82f6" },
  { key: "student_portal", stroke: "#22c55e" },
  { key: "admin", stroke: "#f97316" },
  { key: "iot", stroke: "#ef4444" },
  { key: "general", stroke: "#a855f7" },
];

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-background border border-border px-2 py-1 text-xs font-mono space-y-0.5">
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {Number(p.value).toFixed(1)}
        </div>
      ))}
    </div>
  );
};

type PerformanceChartsProps = {
  // Real per-slice rolling history from the live store — no fabricated
  // trailing data. Each array is empty until WS ticks start arriving, in
  // which case the chart renders with no lines rather than a mock trend.
  metricsHistory: Record<SliceKey, SliceMetricPoint[]>;
  totalAggregate: number;
  breachedSlice: SliceKey | undefined;
};

export function PerformanceCharts({
  metricsHistory,
  totalAggregate,
  breachedSlice,
}: PerformanceChartsProps) {
  const [timeRange, setTimeRange] = useState<"1M" | "5M" | "15M">("1M");
  const pointCount = TIME_RANGE_POINTS[timeRange];

  // All five slices' history arrays grow in lockstep (setMetrics appends to
  // every slice on every tick), so they're always the same length — safe to
  // zip by index rather than needing to align on timestamp.
  const pointsAvailable = metricsHistory.vle.length;
  const sliceStart = Math.max(0, pointsAvailable - pointCount);

  const throughputData = Array.from(
    { length: pointsAvailable - sliceStart },
    (_, i) => {
      const idx = sliceStart + i;
      const row: Record<string, number> = { time: i };
      for (const { key } of SLICE_LINES) {
        row[key] = metricsHistory[key][idx].tx_throughput_bps / 1_000_000;
      }
      return row;
    },
  );

  const latencyData = Array.from(
    { length: pointsAvailable - sliceStart },
    (_, i) => {
      const idx = sliceStart + i;
      const row: Record<string, number> = { time: i };
      for (const { key } of SLICE_LINES) {
        row[key] = metricsHistory[key][idx].latency_ms;
      }
      return row;
    },
  );

  return (
    <div className="mt-6">
      <div className="flex justify-between items-center mb-4">
        <p className="font-semibold uppercase tracking-widest">
          Performance Metrics
        </p>
        <div className="flex gap-1">
          {(["1M", "5M", "15M"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3 py-1 text-xs font-mono ${timeRange === r ? "bg-white text-black" : "text-muted-foreground"}`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Throughput Aggregate */}
        <div className="bg-background p-4">
          <div className="flex justify-between items-center mb-4">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              Throughput Aggregate
            </p>
            <p className="text-sm font-mono font-bold">
              {totalAggregate.toFixed(1)} Mbps
            </p>
          </div>
          {throughputData.length === 0 ? (
            <div className="h-[200px] flex items-center justify-center text-xs text-muted-foreground uppercase tracking-widest">
              No data yet
            </div>
          ) : (
            <ResponsiveContainer width={"100%"} height={200}>
              <LineChart data={throughputData}>
                <XAxis dataKey="time" hide />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} cursor={false} />
                {SLICE_LINES.map((s) => (
                  <Line
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    stroke={s.stroke}
                    dot={true}
                    activeDot={false}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Latency Per Slice */}
        <div className="bg-background p-4">
          <div className="flex justify-between items-center mb-4">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              Latency Per Slice
            </p>
            {breachedSlice && (
              <p className="text-xs font-mono text-red-500">
                Alert: {initialData.slices[breachedSlice].name} Breached
              </p>
            )}
          </div>
          {latencyData.length === 0 ? (
            <div className="h-[200px] flex items-center justify-center text-xs text-muted-foreground uppercase tracking-widest">
              No data yet
            </div>
          ) : (
            <ResponsiveContainer width={"100%"} height={200}>
              <LineChart data={latencyData}>
                <XAxis dataKey="time" hide />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} cursor={false} />
                {SLICE_LINES.map((s) => (
                  <Line
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    stroke={s.stroke}
                    activeDot={false}
                    dot={true}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}