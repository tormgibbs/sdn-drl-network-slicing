import { CAPACITY_BPS, SLICE_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { SliceName } from "@/types/slice";

interface Props {
	slice: SliceName;
	allocationBps: number;
	capacityBps?: number;
	className?: string;
}

export function AllocationBar({
	slice,
	allocationBps,
	capacityBps = CAPACITY_BPS,
	className,
}: Props) {
	const pct = Math.min(100, (allocationBps / capacityBps) * 100);
	return (
		<div className={cn("h-1.5 w-full rounded-full bg-muted/20", className)}>
			<div
				className="h-full rounded-full transition-all duration-500"
				style={{ width: `${pct}%`, backgroundColor: SLICE_COLORS[slice] }}
			/>
		</div>
	);
}
