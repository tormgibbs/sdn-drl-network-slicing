// frontend/src/components/primitives/side-panel/status-block.tsx
import { Play, Square } from "lucide-react";

type StatusBlockProps = {
	title: string;
	running: boolean;
	busy: boolean;
	onStart: () => void;
	onStop: () => void;
	startLabel: string;
	stopLabel: string;
};

export function StatusBlock({
	title,
	running,
	busy,
	onStart,
	onStop,
	startLabel,
	stopLabel,
}: StatusBlockProps) {
	return (
		<div className="flex flex-col gap-2">
			<p className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
				{title}
			</p>
			<div className="flex items-center gap-3">
				<span
					className={`w-2 h-2 ${running ? "bg-[#00C950]" : "bg-muted-foreground"}`}
				/>
				<span className="uppercase font-medium text-sm">
					{running ? "Running" : "Not Running"}
				</span>
			</div>
			<button
				onClick={running ? onStop : onStart}
				disabled={busy}
				type="button"
				className="flex items-center gap-2 p-2 w-full justify-center border border-border disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer bg-transparent hover:bg-accent"
			>
				{running ? <Square size={16} /> : <Play size={16} />}
				<span className="uppercase text-sm">
					{busy
						? running
							? "Stopping..."
							: "Starting..."
						: running
							? stopLabel
							: startLabel}
				</span>
			</button>
		</div>
	);
}
