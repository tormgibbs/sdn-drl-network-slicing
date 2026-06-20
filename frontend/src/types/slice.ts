// types.ts

export type SliceKey = "vle" | "student_portal" | "admin" | "iot" | "general";
export type Mode = "agent" | "static" | "heuristic";
export type Scenario = "normal" | "registration_spike" | "quiz_spike";
export type SLAStatus = "NOMINAL" | "WARNING" | "VIOLATION";

export type SliceConfig = {
  name: string;
  priority: number;
  priority_label: string;
  max_latency_ms: number;
  max_loss_pct: number;
  min_throughput_bps: number;
};

export type Metric = {
  tx_throughput_bps: number;
  latency_ms: number | null;
  loss_pct: number | null;
};

// what GET /state returns
export type StateResponse = {
  slices: Record<SliceKey, SliceConfig>;
  metrics: Record<SliceKey, Metric>;
  allocations: Record<SliceKey, number>;
  mode: Mode;
  traffic: Record<SliceKey, TrafficConfig>;
  system: SystemInfo;
};

// what WebSocket pushes every 5 seconds
export type WSMessage = {
  metrics: Record<SliceKey, Metric>;
  allocations: Record<SliceKey, number>;
  traffic?: Record<SliceKey, TrafficConfig>;
  timestamp: string;
};

export type TrafficConfig = {
  device_count: number;
  pattern: "mixed" | "continuous";
  continuous_bps?: number;
  on_off_bps?: number;
  mean_on_sec?: number;
  mean_off_sec?: number;
  target_bps?: number;
};

export type SystemInfo = {
  ues_attached: number;
  switches_connected: number;
  controller_healthy: boolean;
};

// export type SliceName =
//   | 'vle'
//   | 'student_portal'
//   | 'admin'
//   | 'iot'
//   | 'general'

// export interface SliceMetrics {
//   tx_throughput_bps: number
//   latency_ms: number | null
//   loss_pct: number | null
// }

// export interface SliceAllocation {
//   [slice: string]: number
// }

// export interface SliceSLA {
//   max_latency_ms: number
//   max_loss_pct: number
//   min_throughput_bps: number
//   priority: number
// }

// export interface SliceTrafficConfig {
//   device_count: number
//   pattern: 'continuous' | 'mixed'
//   target_bps?: number
//   continuous_bps?: number
//   on_off_bps?: number
//   mean_on_sec?: number
//   mean_off_sec?: number
// }

// export type SlaStatus = 'met' | 'warning' | 'violated'
