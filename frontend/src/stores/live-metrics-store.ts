import { create } from "zustand";
import type { MetricsResponse, AgentState } from "#/lib/schemas";
import type { SliceKey } from "#/types/slice";

const AGENT_HISTORY_LIMIT = 100;
const SLICE_HISTORY_LIMIT = 100;

export interface AgentHistoryPoint {
  step: number;
  reward: number;
  allocation_kbps: Record<string, number>;
  timestamp: string;
}

export interface SliceMetricPoint {
  timestamp: number; // Date.now() at receipt — no server timestamp per-metric, only envelope-level
  latency_ms: number;
  loss_pct: number;
  tx_throughput_bps: number;
}

const SLICE_KEYS: SliceKey[] = ["vle", "student_portal", "admin", "iot", "general"];

interface LiveMetricsState {
  metrics: MetricsResponse | null;
  metricsHistory: Record<SliceKey, SliceMetricPoint[]>;
  lastUpdated: number | null;
  setMetrics: (m: MetricsResponse) => void;
  agent: AgentState | null;
  agentHistory: AgentHistoryPoint[];
  setAgentState: (a: AgentState | null) => void;
}

function emptyHistory(): Record<SliceKey, SliceMetricPoint[]> {
  return SLICE_KEYS.reduce(
    (acc, key) => ({ ...acc, [key]: [] }),
    {} as Record<SliceKey, SliceMetricPoint[]>,
  );
}

export const useLiveMetricsStore = create<LiveMetricsState>((set) => ({
  metrics: null,
  metricsHistory: emptyHistory(),
  lastUpdated: null,
  setMetrics: (m) =>
    set((state) => {
      const now = Date.now();
      const nextHistory = { ...state.metricsHistory };
      for (const key of SLICE_KEYS) {
        const slice = m[key]; // type inferred from MetricsResponse — SliceMetricsSchema shape, non-nullable
        const point: SliceMetricPoint = {
          timestamp: now,
          latency_ms: slice.latency_ms,
          loss_pct: slice.loss_pct,
          tx_throughput_bps: slice.tx_throughput_bps,
        };
        nextHistory[key] = [...state.metricsHistory[key], point].slice(-SLICE_HISTORY_LIMIT);
      }
      return { metrics: m, metricsHistory: nextHistory, lastUpdated: now };
    }),
  agent: null,
  agentHistory: [],
  setAgentState: (a) =>
    set((state) => {
      if (a === null) return { agent: null };
      const point: AgentHistoryPoint = {
        step: a.step, reward: a.reward, allocation_kbps: a.allocation_kbps, timestamp: a.timestamp,
      };
      return { agent: a, agentHistory: [...state.agentHistory, point].slice(-AGENT_HISTORY_LIMIT) };
    }),
}));