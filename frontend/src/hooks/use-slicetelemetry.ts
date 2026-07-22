import { useState, useEffect, useCallback } from "react";

export type TimeRange = "1M" | "5M" | "15M";

const POINTS_BY_RANGE: Record<TimeRange, number> = {
  "1M": 60,
  "5M": 300,
  "15M": 900,
};

export function useSliceTelemetry<TData, THistoryRow>(
  genTelemetry: (points: number) => TData[],
  buildHistory: (n: number) => THistoryRow[],
  tickMs = 3000,
  historyPoints = 50,
) {
  const [range, setRange] = useState<TimeRange>("1M");
  const [data, setData] = useState<TData[]>(() => genTelemetry(60));
  const [history] = useState<THistoryRow[]>(() => buildHistory(historyPoints));

  const pts = POINTS_BY_RANGE[range];
  const tick = useCallback(() => setData(genTelemetry(pts)), [pts, genTelemetry]);

  useEffect(() => {
    tick();
    const id = setInterval(tick, tickMs);
    return () => clearInterval(id);
  }, [tick, tickMs]);

  return { range, setRange, data, history };
}