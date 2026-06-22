export type EpisodeData = {
  episode: number;
  reward: number;
  sla_pct: number;
};

export type BaselineRow = {
  mode: string;
  reward: number;
  sla_pct: number;
  violations: number;
};

export type AgentStats = {
  reward_signal: number;
  sla_satisfaction: number;
  episodes_trained: number;
  violations: number;
};
