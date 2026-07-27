import { Line, LineChart } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "#/components/ui/chart";
import { SLICE_CHART_CONFIG, SLICE_KEYS } from "./chart-config";

type MetricChartProps = {
  title: string;
  headerRight?: React.ReactNode;
  data: Record<string, number>[];
};

export function MetricChart({ title, headerRight, data }: MetricChartProps) {
  return (
    <div className="bg-grid-small border border-border p-4">
      <div className="flex justify-between items-center mb-4">
        <p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
          {title}
        </p>
        {headerRight}
      </div>
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
    </div>
  );
}