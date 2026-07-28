// frontend/src/slice/iot-slice.tsx
import { initialData } from "#/data/dashboard";
import { SliceDetailView } from "../components/primitives/slice-detail-view";
import type { SliceSharedProps } from "../types/slice-shared";
import type { SliceViewConfig } from "../types/slice-view-config";

const IOT_CONFIG: SliceViewConfig = {
	key: "iot",
	name: "IoT",
	priority: "P2",
	priorityLabel: "P2 (Low)",
	sla: {
		minThrpt: initialData.slices.iot.min_throughput_bps,
		maxLat: initialData.slices.iot.max_latency_ms,
		maxLoss: initialData.slices.iot.max_loss_pct,
	},
	unitDivisor: 1_000_000,
	unitLabel: "Mbps",
	charts: [
		{
			type: "area",
			title: "Throughput",
			dataKey: "thrpt",
			color: "#2B7FFF",
			yDomain: [0, 0.5],
			slaLine: {
				value: initialData.slices.iot.min_throughput_bps / 1e6,
				color: "#6B7280",
				label: "SLA MIN",
			},
		},
		{
			type: "line",
			title: "Latency",
			dataKey: "lat",
			color: "#2B7FFF",
			yDomain: [0, 20],
			slaLine: {
				value: initialData.slices.iot.max_latency_ms,
				color: "#FB2C36",
				label: "SLA MAX",
			},
		},
		{
			type: "area",
			title: "Packet Loss",
			dataKey: "loss",
			color: "#FB2C36",
			yDomain: [0, 6],
			slaLine: {
				value: initialData.slices.iot.max_loss_pct,
				color: "#FF6900",
				label: "SLA MAX",
			},
		},
	],
};

export function IoTSlice(props: SliceSharedProps) {
	return <SliceDetailView config={IOT_CONFIG} {...props} />;
}
