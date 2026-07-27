// frontend/src/components/primitives/side-panel/scenario-switcher.tsx

import type { Scenario } from "#/types/slice";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

const SCENARIO_OPTIONS: { value: Scenario; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "registration", label: "Registration" },
  { value: "exam_period", label: "Exam Period" },
  { value: "general_spike", label: "General Spike" },
  { value: "chaos", label: "Chaos" },
];

type ScenarioSwitcherProps = {
	scenarioMode: Scenario | undefined;
	isSwitching: boolean;
	disabled: boolean;
	onChange: (scenario: Scenario) => void;
};

export function ScenarioSwitcher({
	scenarioMode,
	isSwitching,
	disabled,
	onChange,
}: ScenarioSwitcherProps) {
	return (
		<div className="flex flex-col gap-2">
			<p className="text-[11px] font-mono uppercase tracking-wider text-white/50">
				Active Scenario
			</p>
			<RadioGroup
				value={scenarioMode ?? "normal"}
				onValueChange={onChange}
				disabled={disabled}
			>
				{SCENARIO_OPTIONS.map((option) => (
					<div key={option.value} className="flex items-center gap-3">
						<RadioGroupItem value={option.value} id={option.value} />
						<Label htmlFor={option.value}>{option.label}</Label>
					</div>
				))}
			</RadioGroup>
			{isSwitching && (
				<p className="text-sm text-white/50 uppercase">
					Switching to{" "}
					{SCENARIO_OPTIONS.find((o) => o.value === scenarioMode)?.label}...
				</p>
			)}
		</div>
	);
}
