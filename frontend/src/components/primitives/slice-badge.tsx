import { Badge } from "@/components/ui/badge";
import type { SliceSLA } from "@/types/slice";

interface Props {
	priority: SliceSLA["priority"];
}

export function SliceBadge({ priority }: Props) {
	return (
		<Badge variant="outline" className="font-mono text-xs">
			P{priority}
		</Badge>
	);
}
