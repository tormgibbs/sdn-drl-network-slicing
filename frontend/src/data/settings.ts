// ── Settings page data ────────────────────────────────────────────────────────
import type { SliceMeta, ConfigMap } from "../types/settings";

export const STORAGE_KEY   = "sdn_slice_traffic_config";
export const CAPACITY_MBPS = 100;

export const SLICE_META: SliceMeta[] = [
  {
    id:            "vle",
    label:         "VLE",
    priorityLabel: "High Priority",
    priorityColor: "#FB2C36",
    pattern:       "Mixed Pattern",
    devices:       3000,
    slaMinMbps:    40,
    defaultConfig: {
      continuous_device_count: 3000,
      continuous_port:         5201,
      continuous_rate_mbps:    50,
      burst_rate_mbps:         30,
      burst_port:              5202,
      mean_on_seconds:         15,
      mean_off_seconds:        45,
    },
  },
  {
    id:            "student",
    label:         "Student Portal",
    priorityLabel: "Med Priority",
    priorityColor: "#EAB308",
    pattern:       "Transaction",
    devices:       1500,
    slaMinMbps:    20,
    defaultConfig: {
      continuous_device_count: 1500,
      continuous_port:         5211,
      continuous_rate_mbps:    25,
      burst_rate_mbps:         15,
      burst_port:              5212,
      mean_on_seconds:         20,
      mean_off_seconds:        40,
    },
  },
  {
    id:            "admin",
    label:         "Admin",
    priorityLabel: "Med Priority",
    priorityColor: "#EAB308",
    pattern:       "Stable",
    devices:       200,
    slaMinMbps:    8,
    defaultConfig: {
      continuous_device_count: 200,
      continuous_port:         5221,
      continuous_rate_mbps:    10,
      burst_rate_mbps:         5,
      burst_port:              5222,
      mean_on_seconds:         10,
      mean_off_seconds:        60,
    },
  },
  {
    id:            "iot",
    label:         "IoT",
    priorityLabel: "Low Priority",
    priorityColor: "#4ADE80",
    pattern:       "Periodic",
    devices:       800,
    slaMinMbps:    0.05,
    defaultConfig: {
      continuous_device_count: 800,
      continuous_port:         5231,
      continuous_rate_mbps:    0.064,
      burst_rate_mbps:         0.05,
      burst_port:              5232,
      mean_on_seconds:         30,
      mean_off_seconds:        90,
    },
  },
  {
    id:            "general",
    label:         "General",
    priorityLabel: "Low Priority",
    priorityColor: "#4ADE80",
    pattern:       "Variable",
    devices:       500,
    slaMinMbps:    4,
    defaultConfig: {
      continuous_device_count: 500,
      continuous_port:         5241,
      continuous_rate_mbps:    5,
      burst_rate_mbps:         8,
      burst_port:              5242,
      mean_on_seconds:         25,
      mean_off_seconds:        35,
    },
  },
];

export function buildDefaults(): ConfigMap {
  return Object.fromEntries(
    SLICE_META.map((s) => [s.id, { ...s.defaultConfig }])
  );
}

export function headroomColor(headroom: number): string {
  if (headroom < 5)  return "#FB2C36";
  if (headroom < 15) return "#EAB308";
  return "#10B981";
}

export function capacityBarColor(pct: number): string {
  if (pct > 90) return "#FB2C36";
  if (pct > 75) return "#EA580C";
  return "#EAB308";
}
