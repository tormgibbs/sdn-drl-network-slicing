// components/dashboard/performance-charts.tsx
import { useState, useMemo } from "react";
import { Line, LineChart, XAxis, YAxis, Tooltip } from "recharts";
import { generateHistory, initialData } from "#/data/dashboard";
import type { WSMessage } from "#/types/slice";

const TIME_RANGE_POINTS = { "1M": 12, "5M": 60, "15M": 180 };

const SLICE_LINES = [
  { key: "vle", stroke: "#3b82f6" },
  { key: "student_portal", stroke: "#22c55e" },
  { key: "admin", stroke: "#f97316" },
  { key: "iot", stroke: "#ef4444" },
  { key: "general", stroke: "#a855f7" },
];

// const CustomTooltip = ({ active, payload }: any) => {
//   if (!active || !payload?.length) return null;
//   return (
//     <div className="bg-background border border-border px-2 py-1 text-xs font-mono">
//       {payload.map((p: any) => (
//         <div key={p.dataKey} style={{ color: p.color }}>
//           {p.dataKey}: {Number(p.value).toFixed(1)}
//         </div>
//       ))}
//     </div>
//   );
// };

type PerformanceChartsProps = {
  dynamicData: WSMessage;
  totalAggregate: number;
  breachedSlice: keyof typeof initialData.slices | undefined;
};

export function PerformanceCharts({
  dynamicData,
  totalAggregate,
  breachedSlice,
}: PerformanceChartsProps) {
  const [timeRange, setTimeRange] = useState<"1M" | "5M" | "15M">("1M");

  const history = useMemo(
    () => generateHistory(dynamicData, TIME_RANGE_POINTS[timeRange]),
    [dynamicData, timeRange],
  );

  const throughputData = history.map((snap, i) => ({
    time: i,
    vle: snap.metrics.vle.tx_throughput_bps / 1_000_000,
    student_portal: snap.metrics.student_portal.tx_throughput_bps / 1_000_000,
    admin: snap.metrics.admin.tx_throughput_bps / 1_000_000,
    iot: snap.metrics.iot.tx_throughput_bps / 1_000_000,
    general: snap.metrics.general.tx_throughput_bps / 1_000_000,
  }));

  const latencyData = history.map((snap, i) => ({
    time: i,
    vle: snap.metrics.vle.latency_ms,
    student_portal: snap.metrics.student_portal.latency_ms,
    admin: snap.metrics.admin.latency_ms,
    iot: snap.metrics.iot.latency_ms,
    general: snap.metrics.general.latency_ms,
  }));

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
          <LineChart width={280} height={200} data={throughputData}>
            <XAxis dataKey="time" hide />
            <YAxis hide />
            {SLICE_LINES.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.stroke}
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
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
          <LineChart width={280} height={200} data={latencyData}>
            <XAxis dataKey="time" hide />
            <YAxis hide />
            {SLICE_LINES.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.stroke}
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </div>
      </div>
    </div>
  );
}
