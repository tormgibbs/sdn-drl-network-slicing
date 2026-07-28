// frontend/src/slice/student-portal-slice.tsx
import { initialData } from "#/data/dashboard";
import { SliceDetailView } from "../components/primitives/slice-detail-view";
import type { SliceSharedProps } from "../types/slice-shared";
import type { SliceViewConfig } from "../types/slice-view-config";

const STUDENT_PORTAL_CONFIG: SliceViewConfig = {
	key: "student_portal",
	name: "Student Portal",
	priority: "P4",
	priorityLabel: "P4 (High)",
	sla: {
		minThrpt: initialData.slices.student_portal.min_throughput_bps,
		maxLat: initialData.slices.student_portal.max_latency_ms,
		maxLoss: initialData.slices.student_portal.max_loss_pct,
	},
	unitDivisor: 1_000_000,
	unitLabel: "Mbps",
	charts: [
		{
			type: "area",
			title: "Throughput",
			dataKey: "thrpt",
			color: "#2B7FFF",
			yDomain: [0, 15],
			slaLine: {
				value: initialData.slices.student_portal.min_throughput_bps / 1e6,
				color: "#6B7280",
				label: "SLA MIN",
			},
		},
		{
			type: "line",
			title: "Latency",
			dataKey: "lat",
			color: "#2B7FFF",
			yDomain: [0, 10],
			slaLine: {
				value: initialData.slices.student_portal.max_latency_ms,
				color: "#FB2C36",
				label: "SLA MAX",
			},
		},
		{
			type: "area",
			title: "Packet Loss",
			dataKey: "loss",
			color: "#FB2C36",
			yDomain: [0, 2],
			slaLine: {
				value: initialData.slices.student_portal.max_loss_pct,
				color: "#FF6900",
				label: "SLA MAX",
			},
		},
	],
};

export function StudentPortalSlice(props: SliceSharedProps) {
	return <SliceDetailView config={STUDENT_PORTAL_CONFIG} {...props} />;
}
