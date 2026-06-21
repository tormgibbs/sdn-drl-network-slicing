import { Card, CardContent } from "#/components/ui/card";
import { Line, LineChart, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer } from "recharts";
import type { episodeHistory } from "#/data/agent-data.ts";

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-background border border-border px-2 py-1 text-xs font-mono">
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {Number(p.value).toFixed(2)}
        </div>
      ))}
    </div>
  );
};

type EpisodeChartsProps = {
  history: typeof episodeHistory;
};

export function EpisodeCharts({ history }: EpisodeChartsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 my-8">
      {/* Reward Over Episodes */}
      <Card className="bg-muted border-none rounded-none">
        <CardContent className="pt-6">
          <div className="flex justify-between items-center mb-4">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              Reward Over Episodes
            </p>
            <p className="text-xs font-mono text-blue-400">
              EP 0 → EP {history[history.length - 1].episode}
            </p>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={history}>
              <XAxis
                dataKey="episode"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) =>
                  v === 0
                    ? "0"
                    : v === history[history.length - 1].episode
                      ? String(v)
                      : ""
                }
              />
              <YAxis hide />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="reward"
                stroke="#3b82f6"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* SLA Satisfaction Over Episodes */}
      <Card className="bg-muted border-none rounded-none">
        <CardContent className="pt-6">
          <div className="flex justify-between items-center mb-4">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              SLA Satisfaction Over Episodes
            </p>
            <p className="text-xs font-mono text-green-400">TARGET: 90%</p>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={history}>
              <XAxis
                dataKey="episode"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) =>
                  v === 0
                    ? "0%"
                    : v === history[history.length - 1].episode
                      ? "90%"
                      : ""
                }
              />
              <YAxis hide domain={[0, 100]} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="sla_pct"
                stroke="#22c55e"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
