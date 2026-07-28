// frontend/src/slice/admin-slice.tsx
import { initialData } from "#/data/dashboard";
import { SliceDetailView } from "../components/primitives/slice-detail-view";
import type { SliceSharedProps } from "../types/slice-shared";
import type { SliceViewConfig } from "../types/slice-view-config";

const ADMIN_CONFIG: SliceViewConfig = {
	key: "admin",
	name: "Admin",
	priority: "P3",
	priorityLabel: "P3 (Medium)",
	sla: {
		minThrpt: initialData.slices.admin.min_throughput_bps,
		maxLat: initialData.slices.admin.max_latency_ms,
		maxLoss: initialData.slices.admin.max_loss_pct,
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
				value: initialData.slices.admin.min_throughput_bps / 1e6,
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
				value: initialData.slices.admin.max_latency_ms,
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
				value: initialData.slices.admin.max_loss_pct,
				color: "#FF6900",
				label: "SLA MAX",
			},
		},
	],
};

export function AdminSlice(props: SliceSharedProps) {
	return <SliceDetailView config={ADMIN_CONFIG} {...props} />;
}
