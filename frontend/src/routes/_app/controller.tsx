// frontend/src/routes/_app/agent.tsx
import { createFileRoute } from "@tanstack/react-router";
import { AllocationTrendChart } from "#/components/primitives/agent-dashboard/allocation-trend-chart";
import { RewardTrendChart } from "#/components/primitives/agent-dashboard/reward-trend-chart";
import { StatPanel } from "#/components/primitives/agent-dashboard/stat-panel";
import { TriggerTimeline } from "#/components/primitives/agent-dashboard/trigger-timeline";
import { useAgentDashboard } from "#/hooks/use-agent-dashboard";

export const Route = createFileRoute("/_app/controller")({ component: AgentPage });

function AgentPage() {
	const {
		activeController,
		sliceKeys,
		slaSatisfactionPct,
		agent,
		agentHistory,
		heuristicHistory,
	} = useAgentDashboard();

	if (activeController === null) {
		return (
			<div className="p-4 font-mono text-xs text-muted-foreground">
				Waiting for controller state…
			</div>
		);
	}

	const slaLabel =
		slaSatisfactionPct !== null ? `${slaSatisfactionPct.toFixed(1)}%` : "—";
	const slaColor =
		slaSatisfactionPct !== null && slaSatisfactionPct < 70
			? "#FB2C36"
			: "#00C950";

	return (
		<div className="p-4 flex flex-col gap-4 flex-1 min-h-0">
			<div className="grid grid-cols-3 gap-4">
				<StatPanel
					label="Active Controller"
					value={activeController.toUpperCase()}
				/>
				<StatPanel
					label="SLA Satisfaction"
					value={slaLabel}
					valueColor={slaColor}
				/>
				{activeController === "agent" && (
					<StatPanel
						label="Latest Reward"
						value={agent ? agent.reward.toFixed(2) : "—"}
					/>
				)}
				{activeController === "heuristic" && (
					<StatPanel
						label="Total Triggers"
						value={String(
							heuristicHistory.reduce((sum, p) => sum + p.triggered.length, 0),
						)}
					/>
				)}
				{activeController === "static" && (
					<StatPanel label="Mode" value="Static Allocation" />
				)}
			</div>

			{activeController === "agent" && (
				<div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
					<RewardTrendChart
						history={agentHistory.map((p) => ({
							step: p.step,
							reward: p.reward,
						}))}
					/>
					<AllocationTrendChart
						history={agentHistory.map((p, i) => ({
							i,
							allocation_kbps: p.allocation_kbps,
						}))}
						sliceKeys={sliceKeys}
					/>
				</div>
			)}

			{activeController === "heuristic" && (
				<div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
					<AllocationTrendChart
						history={heuristicHistory.map((p, i) => ({
							i,
							allocation_kbps: p.allocation_kbps,
						}))}
						sliceKeys={sliceKeys}
					/>
					<TriggerTimeline history={heuristicHistory} />
				</div>
			)}

			{activeController === "static" && (
				<div className="font-mono text-xs text-muted-foreground px-1">
					No active control policy — meters hold their last configured
					allocation.
				</div>
			)}
		</div>
	);
}
