// ── Types for the Settings / Traffic Config page ─────────────────────────────

export interface SliceTrafficConfig {
  id?:                      string;
  slice_id:                 string;
  updated_at?:              string;
  continuous_device_count:  number;
  continuous_port:          number;
  continuous_rate_mbps:     number;
  burst_rate_mbps:          number;
  burst_port:               number;
  mean_on_seconds:          number;
  mean_off_seconds:         number;
}

export interface SliceMeta {
  id:             string;
  label:          string;
  priorityLabel:  string;
  priorityColor:  string;
  pattern:        string;
  devices:        number;
  slaMinMbps:     number;
  defaultConfig:  SliceDefaultConfig;
}

export type SliceDefaultConfig = Omit<SliceTrafficConfig, "id" | "slice_id" | "updated_at">;

export type ConfigMap = Record<string, SliceDefaultConfig>;

export interface FooterMetric {
  label: string;
  value: string;
  color: string;
}
