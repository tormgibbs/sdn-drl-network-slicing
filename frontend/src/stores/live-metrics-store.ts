import { create } from "zustand";
import type { MetricsResponse, AgentState } from "#/lib/schemas";

const AGENT_HISTORY_LIMIT = 100;

export interface AgentHistoryPoint {
  step: number;
  reward: number;
  allocation_kbps: Record<string, number>;
  timestamp: string;
}

interface LiveMetricsState {
  metrics: MetricsResponse | null;
  lastUpdated: number | null;
  setMetrics: (m: MetricsResponse) => void;

  agent: AgentState | null;
  agentHistory: AgentHistoryPoint[];
  setAgentState: (a: AgentState | null) => void;
}

export const useLiveMetricsStore = create<LiveMetricsState>((set) => ({
  metrics: null,
  lastUpdated: null,
  setMetrics: (m) => set({ metrics: m, lastUpdated: Date.now() }),

  agent: null,
  agentHistory: [],
  setAgentState: (a) =>
    set((state) => {
      if (a === null) {
        // Agent stopped running — clear current state but keep history
        // so a demo can still show "what it did before it stopped."
        return { agent: null };
      }
      const point: AgentHistoryPoint = {
        step: a.step,
        reward: a.reward,
        allocation_kbps: a.allocation_kbps,
        timestamp: a.timestamp,
      };
      return {
        agent: a,
        agentHistory: [...state.agentHistory, point].slice(-AGENT_HISTORY_LIMIT),
      };
    }),
}));