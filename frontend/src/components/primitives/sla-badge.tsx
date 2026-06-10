import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SlaStatus } from "@/types/slice";

const CONFIG: Record<SlaStatus, { label: string; className: string }> = {
	met: {
		label: "MET",
		className: "bg-success/10 text-success border-success/20",
	},
	warning: {
		label: "WARNING",
		className: "bg-warning/10 text-warning border-warning/20",
	},
	violated: {
		label: "VIOLATED",
		className: "bg-error/10 text-error border-error/20",
	},
};

interface Props {
	status: SlaStatus;
}

export function SlaBadge({ status }: Props) {
	const { label, className } = CONFIG[status];
	return (
		<Badge variant="outline" className={cn("font-mono text-xs", className)}>
			{label}
		</Badge>
	);
}
