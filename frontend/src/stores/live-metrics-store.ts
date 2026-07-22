import { create } from "zustand";
import type { MetricsResponse } from "#/lib/schemas";

interface LiveMetricsState {
  metrics: MetricsResponse | null;
  lastUpdated: number | null;
  setMetrics: (m: MetricsResponse) => void;
}

export const useLiveMetricsStore = create<LiveMetricsState>((set) => ({
  metrics: null,
  lastUpdated: null,
  setMetrics: (m) => set({ metrics: m, lastUpdated: Date.now() }),
}));