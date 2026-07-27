import type { ChartConfig } from "#/components/ui/chart";
import type { SliceKey } from "#/types/slice";

export const SLICE_KEYS: SliceKey[] = ["vle", "student_portal", "admin", "iot", "general"];

export const SLICE_CHART_CONFIG = {
  vle: { label: "VLE", color: "var(--chart-1)" },
  student_portal: { label: "Student Portal", color: "var(--chart-2)" },
  admin: { label: "Admin", color: "var(--chart-3)" },
  iot: { label: "IoT", color: "var(--chart-4)" },
  general: { label: "General", color: "var(--chart-5)" },
} satisfies ChartConfig;