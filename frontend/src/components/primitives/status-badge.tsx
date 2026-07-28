import { Badge } from "#/components/ui/badge";
import { cn } from "#/lib/utils";

type StatusBadgeProps = {
	label: string;
	className?: string;
	variant?: "outline" | "secondary";
};

export function StatusBadge({
	label,
	className,
	variant = "outline",
}: StatusBadgeProps) {
	return (
		<Badge variant={variant} className={cn("rounded-none", className)}>
			{label}
		</Badge>
	);
}
