// frontend/src/components/primitives/slice-dashboard/chartpanel.tsx

import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";
import { PanelFrame } from "../panel-frame";
export function ChartPanel({
	title,
	children,
}: {
	title: string;
	children: ReactNode;
}) {
	return (
		<PanelFrame title={title} overflow="hidden">
			<ResponsiveContainer width="100%" height="100%">
				{children}
			</ResponsiveContainer>
		</PanelFrame>
	);
}
