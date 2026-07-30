// types.ts
import type { Metric, SliceConfig } from "#/lib/schemas";

export type SliceKey = "vle" | "student_portal" | "admin" | "iot" | "general";
export type SliceName = SliceKey; // alias — newer naming used elsewhere in the codebase

export type Mode = "agent" | "static" | "heuristic";
export type Scenario = "normal" | "registration" | "quiz" | "general_spike" | "chaos";
export type SLAStatus = "NOMINAL" | "WARNING" | "VIOLATION";

export type { Metric, SliceConfig } from "#/lib/schemas";
export type SliceMetrics = Metric; // alias — newer naming used elsewhere

// what GET /state returns
export type StateResponse = {
	slices: Record<SliceKey, SliceConfig>;
	metrics: Record<SliceKey, Metric>;
	allocations: Record<SliceKey, number>;
	mode: Mode;
	traffic: Record<SliceKey, TrafficConfig>;
	system: SystemInfo;
};

// config thresholds per slice — derived from SliceConfig so they can't drift apart
export type SliceSLA = Pick<
	SliceConfig,
	"max_latency_ms" | "max_loss_pct" | "min_throughput_bps" | "priority"
>;

// computed status for a slice at a point in time — was the old "SliceSLA"
export type SliceSLAStatus = {
	priority: number;
	priority_label: string;
	sla_status: SLAStatus;
};

// what WebSocket pushes every 5 seconds
export type WSMessage = {
	metrics: Record<SliceKey, Metric>;
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
export type SliceTrafficConfig = TrafficConfig; // alias — newer naming used elsewhere

export type SystemInfo = {
	ues_attached: number;
	switches_connected: number;
	controller_healthy: boolean;
};
