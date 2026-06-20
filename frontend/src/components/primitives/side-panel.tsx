// components/dashboard/side-panel.tsx
import { Activity, ChartNoAxesCombined, Cpu, TrendingUp } from "lucide-react";
import { RadioGroup } from "./radio-group";
import type { Mode, Scenario } from "#/types/slice";

const MODE_OPTIONS: { value: Mode; label: string }[] = [
  { value: "agent", label: "Agent RL" },
  { value: "static", label: "Static" },
  { value: "heuristic", label: "Heuristic" },
];

const SCENARIO_OPTIONS: { value: Scenario; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "registration_spike", label: "Registration Spike" },
  { value: "quiz_spike", label: "Quiz Spike" },
];

type SidePanelProps = {
  controllerMode: Mode;
  scenarioMode: Scenario;
  slaSatisfaction: string;
  onModeChange: (mode: Mode) => void;
  onScenarioChange: (scenario: Scenario) => void;
};

export function SidePanel({
  controllerMode,
  scenarioMode,
  slaSatisfaction,
  onModeChange,
  onScenarioChange,
}: SidePanelProps) {
  return (
    <div>
      {/* Controller Mode */}
      <div className="mb-4">
        <div className="flex gap-2">
          <Cpu size={20} />
          <p className="font-bold uppercase mb-4">Controller Mode</p>
        </div>
        <RadioGroup
          options={MODE_OPTIONS}
          value={controllerMode}
          onChange={onModeChange}
        />
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
      </div>

      {/* Agent Performance — only when mode is agent */}
      {controllerMode === "agent" && (
        <div className="mt-8 mb-4">
          <div className="flex gap-2">
            <ChartNoAxesCombined size={20} />
            <p className="font-bold uppercase mb-4">Agent Performance</p>
          </div>
          <div className="my-4">
            <p className="uppercase">Reward Signal</p>
            <p className="text-3xl font-bold text-green-500 flex items-center gap-2">
              <span>+2.45</span>
              <TrendingUp size={24} />
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
