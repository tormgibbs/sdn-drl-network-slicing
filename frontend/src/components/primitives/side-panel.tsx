import { Activity, ChartNoAxesCombined, Cpu, TrendingDown, TrendingUp, Play, Square } from "lucide-react";
import { RadioGroup } from "./radio-group";
import type { Scenario } from "#/types/slice";

const SCENARIO_OPTIONS: { value: Scenario; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "registration_spike", label: "Registration Spike" },
  { value: "quiz_spike", label: "Quiz Spike" },
];

type SidePanelProps = {
  agentRunning: boolean;
  isAgentBusy: boolean;
  onAgentStart: () => void;
  onAgentStop: () => void;
  scenarioMode: Scenario;
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
  scenarioMode,
  isSwitchingScenario,
  onScenarioChange,
  slaSatisfaction,
  reward,
}: SidePanelProps) {
  const showAgentPerformance = agentRunning && reward !== null;
  const isPositive = (reward ?? 0) >= 0;

  return (
    <div>
      {/* Agent Status — replaces the old three-way Agent/Static/Heuristic
          radio group. Static/heuristic are offline experimental conditions
          (fixed-duration comparison runs), not live/switchable backend
          states, so there is no real "mode toggle" to expose here — only
          whether the DRL agent is actually running right now. */}
      <div className="mb-4">
        <div className="flex gap-2">
          <Cpu size={20} />
          <p className="font-bold uppercase mb-4">Agent Status</p>
        </div>
        <div className="flex items-center gap-3 p-2">
          <span
            className={`w-2 h-2 rounded-full ${
              agentRunning ? "bg-green-500" : "bg-white/30"
            }`}
          />
          <span className="uppercase font-medium">
            {agentRunning ? "Running" : "Not Running"}
          </span>
        </div>
        <button
          onClick={agentRunning ? onAgentStop : onAgentStart}
          disabled={isAgentBusy}
          className="flex items-center gap-2 mt-2 p-2 w-full justify-center border border-white/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer bg-transparent"
        >
          {agentRunning ? <Square size={16} /> : <Play size={16} />}
          <span className="uppercase">
            {isAgentBusy
              ? agentRunning
                ? "Stopping..."
                : "Starting..."
              : agentRunning
              ? "Stop Agent"
              : "Start Agent"}
          </span>
        </button>
      </div>

      {/* Active Scenario */}
      <div className="mt-8 mb-4">
        <div className="flex gap-2">
          <Activity size={20} />
          <p className="font-bold uppercase mb-4">Active Scenario</p>
        </div>
        <RadioGroup
          options={SCENARIO_OPTIONS}
          value={scenarioMode}
          onChange={onScenarioChange}
        />
        {/* Scenario switches only take effect at the next traffic loop
            boundary on the backend, not instantly — this can take up to
            ~65s in the worst case (confirmed from traffic/runner.py). This
            indicator reflects that real delay rather than hiding it. */}
        {isSwitchingScenario && (
          <p className="mt-2 text-sm text-white/50 uppercase">
            Switching to {SCENARIO_OPTIONS.find((o) => o.value === scenarioMode)?.label}...
          </p>
        )}
      </div>

      {/* Agent Performance — only when agent is running AND live agent data exists */}
      {showAgentPerformance && (
        <div className="mt-8 mb-4">
          <div className="flex gap-2">
            <ChartNoAxesCombined size={20} />
            <p className="font-bold uppercase mb-4">Agent Performance</p>
          </div>
          <div className="my-4">
            <p className="uppercase">Reward Signal</p>
            <p
              className={`text-3xl font-bold flex items-center gap-2 ${
                isPositive ? "text-green-500" : "text-red-500"
              }`}
            >
              <span>
                {isPositive ? "+" : ""}
                {reward!.toFixed(2)}
              </span>
              {isPositive ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
            </p>
          </div>
          <div className="my-4">
            <p className="uppercase">SLA Satisfaction</p>
            <p className="text-3xl font-bold">{slaSatisfaction}%</p>
          </div>
        </div>
      )}
    </div>
  );
}