// frontend/src/components/primitives/performance-charts/metric-chart.tsx
import { Line, LineChart } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "#/components/ui/chart";
import { PanelFrame } from "../panel-frame";
import { SLICE_CHART_CONFIG, SLICE_KEYS } from "./chart-config";

type MetricChartProps = {
  title: string;
  headerRight?: React.ReactNode;
  data: Record<string, number>[];
};

export function MetricChart({ title, headerRight, data }: MetricChartProps) {
  return (
    <PanelFrame title={title} headerRight={headerRight}>
      {data.length === 0 ? (
        <div className="h-[200px] flex items-center justify-center text-xs font-mono text-muted-foreground uppercase tracking-wider">
          No data yet
        </div>
      ) : (
        <ChartContainer config={SLICE_CHART_CONFIG} className="h-[200px] w-full">
          <LineChart data={data}>
            <ChartTooltip content={<ChartTooltipContent indicator="dot" />} />
            {SLICE_KEYS.map((key) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={`var(--color-${key})`}
                dot={false}
                activeDot={{ r: 3 }}
                strokeWidth={1.5}
              />
            ))}
          </LineChart>
        </ChartContainer>
      )}
    </PanelFrame>
  );
}
