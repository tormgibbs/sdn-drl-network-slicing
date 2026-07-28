import type { SliceKey } from "#/types/slice";
import type { SliceSLA } from "#/hooks/use-live-slice-data";

export type ChartSpec = {
  type: "area" | "line";
  title: string;
  dataKey: "thrpt" | "lat" | "loss";
  color: string;
  yDomain: [number, number];
  yTickCount?: number;
  slaLine?: { value: number; color: string; label: string };
};

export type SliceViewConfig = {
  key: SliceKey;
  name: string;
  priority: string;
  priorityLabel: string;
  sla: SliceSLA;
  unitDivisor: number;
  unitLabel: string;
  throughputLabel?: string;
  latencyLabel?: string;
  telemetryLabel?: string;
  recentCols?: [string, string];
  thrptHeader?: string;
  charts: ChartSpec[];
};