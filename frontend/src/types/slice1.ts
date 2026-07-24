// ── Shared types for network slice pages ─────────────────────────────────────

export type TimeRange = "1M" | "5M" | "15M";

// Per-slice-cycle SLA status, used by the five individual slice detail pages
// (VLE/Admin/StudentPortal/IoT/General). Deliberately distinct from
// types/slice.ts's SLAStatus (NOMINAL | WARNING | VIOLATION), which is a
// separate, dashboard-level concept used by computeSlaStatus/index.tsx and
// sla-badge.tsx. These two used to share the name "SLAStatus" despite being
// different types — renamed here to remove the collision. See schemas.ts
// history for context if this resurfaces.
export type SliceCycleStatus = "MET" | "VIOLATION";

// SLA thresholds for a slice
export interface SLAConfig {
  minThrpt: number;   // Mbps (or Kbps for IoT — callers normalise)
  maxLat:   number;   // ms
  maxLoss:  number;   // percent
}

// One telemetry data point — core fields every slice uses
export interface TelemetryPoint {
  i:     number;
  thrpt: number;
  lat:   number;
  loss:  number;
  // optional extra fields per slice
  alloc?:    number;
  txRate?:   number;   // Admin: DB tx/s
  flows?:    number;   // Admin: active TCP flows
  reqRate?:  number;   // StudentPortal: req/s
  sessions?: number;   // StudentPortal: concurrent sessions
  pktRate?:  number;   // IoT: pkts/min
  sources?:  number;   // IoT: active heartbeat sources
  // GeneralSlice protocol breakdown
  https?: number;
  udp?:   number;
  tcp?:   number;
  dns?:   number;
}

// One history row (full table)
export interface HistoryRow {
  ts:    string;
  id:    string;
  thrpt: number;
  lat:   number;
  loss:  number;
  alloc: number;
  sla:   SliceCycleStatus;
}

// Recent-cycle mini table row (right-column panel)
export interface RecentCycle {
  id:     string;
  thrpt:  number;
  lat:    number;
  status: SliceCycleStatus;
}

// IoT traffic source
export interface TrafficSource {
  id:          string;
  name:        string;
  lastArrival: number;   // ms ago
  pktRate:     number;   // pkts/min
  latency:     number;   // ms
  status:      "on-schedule" | "delayed" | "missed";
}

// A single metric row in the right-column "Current State" panel
export interface MetricRowItem {
  label:     string;
  value:     string;
  highlight?: boolean;
}

// A single cell in the right-column "SLA Thresholds" grid
export interface SLACellItem {
  label:     string;
  value:     string;
  highlight?: boolean;
}

// Tooltip payload (recharts)
export interface TooltipPayload {
  name:   string;
  value:  number;
  color?: string;
}