import { cn } from "@/lib/utils";

interface Props {
	label: string;
	value: string;
	muted?: boolean;
}

export function MetricRow({ label, value, muted = false }: Props) {
	return (
		<div className="flex items-center justify-between gap-4 py-1">
			<span className={cn("text-sm", muted && "text-muted-foreground")}>
				{label}
			</span>
			<span className="font-mono text-sm tabular-nums">{value}</span>
		</div>
	);
}
