// frontend/src/components/primitives/side-panel/index.tsx
import type { Scenario } from "#/types/slice";
import { AgentPerformance } from "./agent-performance";
import { ScenarioSwitcher } from "./scenario-switcher";
import { StatusBlock } from "./status-block";

type SidePanelProps = {
	agentRunning: boolean;
	isAgentBusy: boolean;
	onAgentStart: () => void;
	onAgentStop: () => void;
	trafficRunning: boolean;
	isTrafficBusy: boolean;
	onTrafficStart: () => void;
	onTrafficStop: () => void;
	scenarioMode: Scenario | undefined;
	isSwitchingScenario: boolean;
	onScenarioChange: (scenario: Scenario) => void;
	slaSatisfaction: string;
	reward: number | null;
};

export function SidePanel({
	agentRunning,
	isAgentBusy,
	onAgentStart,
	onAgentStop,
	trafficRunning,
	isTrafficBusy,
	onTrafficStart,
	onTrafficStop,
	scenarioMode,
	isSwitchingScenario,
	onScenarioChange,
	slaSatisfaction,
	reward,
}: SidePanelProps) {
	const showAgentPerformance = agentRunning && reward !== null;

	return (
		<div className="flex flex-col gap-6">
			<StatusBlock
				title="Agent Status"
				running={agentRunning}
				busy={isAgentBusy}
				onStart={onAgentStart}
				onStop={onAgentStop}
				startLabel="Start Agent"
				stopLabel="Stop Agent"
			/>

			<div className="flex flex-col gap-3">
				<StatusBlock
					title="Traffic Generator"
					running={trafficRunning}
					busy={isTrafficBusy}
					onStart={onTrafficStart}
					onStop={onTrafficStop}
					startLabel="Start Traffic"
					stopLabel="Stop Traffic"
				/>
				<ScenarioSwitcher
					scenarioMode={scenarioMode}
					isSwitching={isSwitchingScenario}
					disabled={!trafficRunning || isSwitchingScenario}
					onChange={onScenarioChange}
				/>
			</div>

			{showAgentPerformance && (
				<AgentPerformance reward={reward!} slaSatisfaction={slaSatisfaction} />
			)}
		</div>
	);
}
