import { createFileRoute } from "@tanstack/react-router";
import {
  agentStats,
  baselineComparison,
  episodeHistory,
  recentEpisodes,
} from "#/data/agent-data.ts";
import { StatCards } from "#/components/primitives/agent-dashboard/stats-cards.tsx";
import { EpisodeCharts } from "#/components/primitives/agent-dashboard/episode-charts";
import { BaselineComparison } from "#/components/primitives/agent-dashboard/baseline-comparison";
import { RecentEpisodes } from "#/components/primitives/agent-dashboard//recent-episodes";

export const Route = createFileRoute("/_app/agent")({ component: AgentPage });

function AgentPage() {
  return (
    <div className="p-4 space-y-4">
      <StatCards
        rewardSignal={agentStats.reward_signal}
        slaSatisfaction={agentStats.sla_satisfaction}
        episodesTrained={agentStats.episodes_trained}
        violations={agentStats.violations}
      />

      <EpisodeCharts history={episodeHistory} />

      <div className="grid grid-cols-2 gap-4">
        <BaselineComparison data={baselineComparison} />
        <RecentEpisodes episodes={recentEpisodes} />
      </div>
    </div>
  );
}
