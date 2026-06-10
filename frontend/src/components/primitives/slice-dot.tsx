import { SLICE_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { SliceName } from "@/types/slice";

interface Props {
	slice: SliceName;
	size?: number;
	className?: string;
}

export function SliceDot({ slice, size = 8, className }: Props) {
	return (
		<span
			className={cn("inline-block rounded-full shrink-0", className)}
			style={{
				width: size,
				height: size,
				backgroundColor: SLICE_COLORS[slice],
			}}
		/>
	);
}
