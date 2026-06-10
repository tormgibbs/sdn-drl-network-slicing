import { create } from "zustand";
import { CHART_HISTORY_LENGTH } from "@/lib/constants";
import type { ControllerMode, StateResponse, WsMessage } from "@/types/api";
import type {
	SliceMetrics,
	SliceName,
	SliceTrafficConfig,
} from "@/types/slice";

export interface ChartDataPoint {
	timestamp: string;
	tx_throughput_bps: number;
	latency_ms: number | null;
	loss_pct: number | null;
}

interface NetworkStore {
	// Current snapshot
	metrics: StateResponse["metrics"] | null;
	allocations: StateResponse["allocations"] | null;
	slices: StateResponse["slices"] | null;
	traffic: Record<SliceName, SliceTrafficConfig> | null;
	mode: ControllerMode;
	system: StateResponse["system"] | null;

	// Time series history per slice for charts
	history: Record<SliceName, ChartDataPoint[]>;

	// Hydrate from GET /state on initial load
	hydrate: (state: StateResponse) => void;

	// Apply incoming WebSocket push
	applyPush: (msg: WsMessage) => void;

	// Update mode locally after POST /mode
	setMode: (mode: ControllerMode) => void;
}

const SLICE_NAMES: SliceName[] = [
	"vle",
	"student_portal",
	"admin",
	"iot",
	"general",
];

function emptyHistory(): Record<SliceName, ChartDataPoint[]> {
	return {
		vle: [],
		student_portal: [],
		admin: [],
		iot: [],
		general: [],
	};
}

function appendHistory(
	history: Record<SliceName, ChartDataPoint[]>,
	metrics: Record<SliceName, SliceMetrics>,
	timestamp: string,
): Record<SliceName, ChartDataPoint[]> {
	const next = { ...history };

	for (const slice of SLICE_NAMES) {
		const m = metrics[slice];
		const point: ChartDataPoint = {
			timestamp,
			tx_throughput_bps: m.tx_throughput_bps,
			latency_ms: m.latency_ms,
			loss_pct: m.loss_pct,
		};

		const prev = next[slice];
		next[slice] = [...prev, point].slice(-CHART_HISTORY_LENGTH);
	}

	return next;
}

export const useNetworkStore = create<NetworkStore>((set) => ({
	metrics: null,
	allocations: null,
	slices: null,
	traffic: null,
	mode: "agent",
	system: null,
	history: emptyHistory(),

	hydrate: (state) =>
		set((store) => ({
			metrics: state.metrics,
			allocations: state.allocations,
			slices: state.slices,
			traffic: state.traffic,
			mode: state.mode,
			system: state.system,
			history: appendHistory(
				store.history,
				state.metrics,
				new Date().toISOString(),
			),
		})),

	applyPush: (msg) =>
		set((store) => ({
			metrics: msg.metrics,
			allocations: msg.allocations,
			traffic: msg.traffic,
			history: appendHistory(store.history, msg.metrics, msg.timestamp),
		})),

	setMode: (mode) => set({ mode }),
}));
