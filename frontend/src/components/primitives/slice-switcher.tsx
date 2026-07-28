// frontend/src/components/primitives/slice-switcher.tsx
export type SliceKey = "vle" | "student_portal" | "admin" | "iot" | "general";

export interface SliceTab {
	key: SliceKey;
	label: string;
	priority: string;
	slaOk: boolean;
}

interface SliceSwitcherProps {
	tabs: SliceTab[];
	active: SliceKey;
	onChange: (key: SliceKey) => void;
}

export function SliceSwitcher({ tabs, active, onChange }: SliceSwitcherProps) {
	return (
		<div className="flex overflow-x-auto border-b border-border bg-background">
			{tabs.map((t) => {
				const isActive = t.key === active;
				return (
					<button
						key={t.key}
						type="button"
						onClick={() => onChange(t.key)}
						className={[
							"px-4 h-9 shrink-0 border-b-2 transition-colors duration-150",
							"font-mono text-[11px] whitespace-nowrap cursor-pointer bg-transparent border-0",
							isActive
								? "border-b-foreground text-foreground bg-accent"
								: "border-b-transparent text-muted-foreground hover:text-foreground",
						].join(" ")}
					>
						{t.label}
					</button>
				);
			})}
		</div>
	);
}
