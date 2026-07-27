import type { SliceMetricPoint } from "#/stores/live-metrics-store";
import type { SliceKey } from "#/types/slice";
import { SLICE_KEYS } from "./chart-config";

export const TIME_RANGE_POINTS = { "1M": 12, "5M": 60, "15M": 100 } as const;
export type TimeRange = keyof typeof TIME_RANGE_POINTS;

export function buildChartWindow(
  metricsHistory: Record<SliceKey, SliceMetricPoint[]>,
  pointCount: number,
  extract: (point: SliceMetricPoint) => number,
) {
  const pointsAvailable = metricsHistory.vle.length;
  const sliceStart = Math.max(0, pointsAvailable - pointCount);

  return Array.from({ length: pointsAvailable - sliceStart }, (_, i) => {
    const idx = sliceStart + i;
    const row: Record<string, number> = { time: i };
    for (const key of SLICE_KEYS) {
      row[key] = extract(metricsHistory[key][idx]);
    }
    return row;
  });
}

export function buildWindow(
  metricsHistory: Record<SliceKey, SliceMetricPoint[]>,
  pointCount: number,
  extract: (point: SliceMetricPoint) => number,
) {
  const pointsAvailable = metricsHistory.vle.length;
  const sliceStart = Math.max(0, pointsAvailable - pointCount);

  return Array.from({ length: pointsAvailable - sliceStart }, (_, i) => {
    const idx = sliceStart + i;
    const row: Record<string, number> = { time: i };
    for (const key of SLICE_KEYS) {
      row[key] = extract(metricsHistory[key][idx]);
    }
    return row;
  });
}