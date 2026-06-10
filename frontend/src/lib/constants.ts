import type { SliceName } from "@/types/slice";

export const SLICE_COLORS: Record<SliceName, string> = {
	vle: "#2B7FFF",
	student_portal: "#00C950",
	admin: "#FF6900",
	iot: "#A6A09B",
	general: "rgba(250,250,249,0.4)",
};

export const SLICE_LABELS: Record<SliceName, string> = {
	vle: "VLE",
	student_portal: "Student Portal",
	admin: "Admin",
	iot: "IoT",
	general: "General",
};

export const SLICE_ORDER: SliceName[] = [
	"vle",
	"student_portal",
	"admin",
	"iot",
	"general",
];

// Total link capacity in bps (100 Mbps)
export const CAPACITY_BPS = 100_000_000;

// How many data points to keep in chart history
export const CHART_HISTORY_LENGTH = 60;

// Mock WebSocket push interval in ms
export const MOCK_INTERVAL_MS = 5000;
