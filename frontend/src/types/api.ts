import type {
	SliceMetrics,
	SliceName,
	SliceSLA,
	SliceTrafficConfig,
} from "./slice";

export interface SystemStatus {
	ues_attached: number;
	switches_connected: number;
	controller_healthy: boolean;
}

export type ControllerMode = "agent" | "static" | "heuristic";

export interface StateResponse {
	metrics: Record<SliceName, SliceMetrics>;
	allocations: Record<SliceName, number>;
	mode: ControllerMode;
	slices: Record<SliceName, SliceSLA>;
	traffic: Record<SliceName, SliceTrafficConfig>;
	system: SystemStatus;
}

export interface WsMessage {
	metrics: Record<SliceName, SliceMetrics>;
	allocations: Record<SliceName, number>;
	traffic: Record<SliceName, SliceTrafficConfig>;
	timestamp: string;
}
