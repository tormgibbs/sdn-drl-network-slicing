import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SLAStatus } from "@/types/slice";

const CONFIG: Record<SLAStatus, { label: string; className: string }> = {
	NOMINAL: {
		label: "NOMINAL",
		className: "bg-success/10 text-success border-success/20",
	},
	WARNING: {
		label: "WARNING",
		className: "bg-warning/10 text-warning border-warning/20",
	},
	VIOLATION: {
		label: "VIOLATION",
		className: "bg-error/10 text-error border-error/20",
	},
};

interface Props {
	status: SLAStatus;
}

export function SlaBadge({ status }: Props) {
	const { label, className } = CONFIG[status];
	return (
		<Badge variant="outline" className={cn("font-mono text-xs", className)}>
			{label}
		</Badge>
	);
}
