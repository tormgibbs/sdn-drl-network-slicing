// frontend/src/components/primitives/side-panel/index.tsx
import type { ActiveController } from "#/lib/schemas";
import type { Scenario } from "#/types/slice";
import { AgentPerformance } from "./agent-performance";
import { ControllerSwitch } from "./controller-switch";
import { HeuristicPerformance } from "./heuristic-performance";
import { ScenarioSwitcher } from "./scenario-switcher";
import { StatusBlock } from "./status-block";

type SidePanelProps = {
	activeController: ActiveController | null;
	isSwitchingController: boolean;
	onControllerChange: (controller: ActiveController) => void;
	trafficRunning: boolean;
	isTrafficBusy: boolean;
	onTrafficStart: () => void;
	onTrafficStop: () => void;
	scenarioMode: Scenario | undefined;
	isSwitchingScenario: boolean;
	onScenarioChange: (scenario: Scenario) => void;
	slaSatisfaction: string;
	reward: number | null;
	triggerCount: number;
};

export function SidePanel({
	activeController,
	isSwitchingController,
	onControllerChange,
	trafficRunning,
	isTrafficBusy,
	onTrafficStart,
	onTrafficStop,
	scenarioMode,
	isSwitchingScenario,
	onScenarioChange,
	slaSatisfaction,
	reward,
	triggerCount,
}: SidePanelProps) {
	return (
		<div className="flex flex-col gap-6">
			<ControllerSwitch
				activeController={activeController}
				isSwitching={isSwitchingController}
				onChange={onControllerChange}
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
			{activeController === "agent" && reward !== null && (
				<AgentPerformance reward={reward} slaSatisfaction={slaSatisfaction} />
			)}
			{activeController === "heuristic" && (
				<HeuristicPerformance
					triggerCount={triggerCount}
					slaSatisfaction={slaSatisfaction}
				/>
			)}
		</div>
	);
}
