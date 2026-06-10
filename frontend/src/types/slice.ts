export type SliceName =
  | 'vle'
  | 'student_portal'
  | 'admin'
  | 'iot'
  | 'general'

export interface SliceMetrics {
  tx_throughput_bps: number
  latency_ms: number | null
  loss_pct: number | null
}

export interface SliceAllocation {
  [slice: string]: number
}

export interface SliceSLA {
  max_latency_ms: number
  max_loss_pct: number
  min_throughput_bps: number
  priority: number
}

export interface SliceTrafficConfig {
  device_count: number
  pattern: 'continuous' | 'mixed'
  target_bps?: number
  continuous_bps?: number
  on_off_bps?: number
  mean_on_sec?: number
  mean_off_sec?: number
}

export type SlaStatus = 'met' | 'warning' | 'violated'