import type { AgentStats, BaselineRow, EpisodeData } from "../types/agent-dashboard";

export const episodeHistory: EpisodeData[] = Array.from(
  { length: 1241 },
  (_, i) => ({
    episode: i,
    reward: parseFloat((-1.5 + (i / 1240) * 4.2).toFixed(2)),
    sla_pct: parseFloat((40 + (i / 1240) * 54.2).toFixed(1)),
  }),
);

export const recentEpisodes: EpisodeData[] = [
  { episode: 1240, reward: 2.45, sla_pct: 94 },
  { episode: 1239, reward: 2.21, sla_pct: 91 },
  { episode: 1238, reward: 1.89, sla_pct: 87 },
  { episode: 1237, reward: 1.44, sla_pct: 79 },
  { episode: 1236, reward: -0.12, sla_pct: 61 },
];

export const baselineComparison: BaselineRow[] = [
  { mode: "PPO AGENT", reward: 2.45, sla_pct: 94.2, violations: 3 },
  { mode: "HEURISTIC", reward: 1.12, sla_pct: 81.4, violations: 14 },
  { mode: "STATIC", reward: -0.34, sla_pct: 63.7, violations: 38 },
];

export const agentStats: AgentStats = {
  reward_signal: 2.45,
  sla_satisfaction: 94.2,
  episodes_trained: 1240,
  violations: 3,
};
