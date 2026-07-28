// frontend/src/components/primitives/side-panel/controller-switch.tsx

import type { ActiveController } from "#/lib/schemas";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

const CONTROLLER_OPTIONS: { value: ActiveController; label: string }[] = [
	{ value: "static", label: "Static" },
	{ value: "heuristic", label: "Heuristic" },
	{ value: "agent", label: "PPO Agent" },
];

type ControllerSwitchProps = {
	activeController: ActiveController | null;
	isSwitching: boolean;
	onChange: (controller: ActiveController) => void;
};

export function ControllerSwitch({
	activeController,
	isSwitching,
	onChange,
}: ControllerSwitchProps) {
	return (
		<div className="flex flex-col gap-2">
			<p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
				Control Policy
			</p>
			<RadioGroup
				value={activeController ?? undefined}
				onValueChange={onChange}
				disabled={isSwitching || activeController === null}
			>
				{CONTROLLER_OPTIONS.map((option) => (
					<div key={option.value} className="flex items-center gap-3">
						<RadioGroupItem value={option.value} id={`ctrl-${option.value}`} />
						<Label htmlFor={`ctrl-${option.value}`}>{option.label}</Label>
					</div>
				))}
			</RadioGroup>
			{isSwitching && (
				<p className="text-sm font-mono text-muted-foreground uppercase">
					Switching controller…
				</p>
			)}
		</div>
	);
}
