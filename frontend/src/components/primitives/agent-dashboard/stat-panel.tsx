// frontend/src/components/primitives/agent-dashboard/stat-panel.tsx
import { PanelFrame } from "../panel-frame";

export function StatPanel({
	label,
	value,
	valueColor,
}: {
	label: string;
	value: string;
	valueColor?: string;
}) {
	return (
		<PanelFrame title={label} motif={false}>
			<div className="flex items-center justify-center h-full py-4">
				<span
					className="font-mono text-2xl"
					style={valueColor ? { color: valueColor } : undefined}
				>
					{value}
				</span>
			</div>
		</PanelFrame>
	);
}
