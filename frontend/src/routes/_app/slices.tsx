// frontend/src/routes/_app/slices.tsx

import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import type {
	SliceKey,
	SliceTab,
} from "../../components/primitives/slice-switcher";
import { AdminSlice } from "../../slice/admin-slice";
import { GeneralSlice } from "../../slice/general-slice";
import { IoTSlice } from "../../slice/iot-slice";
import { StudentPortalSlice } from "../../slice/student-portal-slice";
import { VLESlice } from "../../slice/vle-slice";

export const Route = createFileRoute("/_app/slices")({
	component: SlicesPage,
});

// ── Static tab config (labels + priorities) ───────────────────────────────────
// slaOk is injected at render time from each slice's live state via a callback.

const SLICE_TABS: Omit<SliceTab, "slaOk">[] = [
	{ key: "vle", label: "VLE", priority: "P5" },
	{ key: "student_portal", label: "Student Portal", priority: "P4" },
	{ key: "admin", label: "Admin", priority: "P3" },
	{ key: "iot", label: "IoT", priority: "P2" },
	{ key: "general", label: "General", priority: "P1" },
];

// ── SlicesPage ────────────────────────────────────────────────────────────────

function SlicesPage() {
	const [activeSlice, setActiveSlice] = useState<SliceKey>("vle");

	// Each slice reports its live SLA status up here so the switcher dots
	// stay reactive even when a slice is not the active one.
	const [slaStatus, setSlaStatus] = useState<Record<SliceKey, boolean>>({
		vle: true,
		student_portal: true,
		admin: true,
		iot: true,
		general: true,
	});

	const onSlaChange = (key: SliceKey, ok: boolean) => {
		setSlaStatus((prev) => (prev[key] === ok ? prev : { ...prev, [key]: ok }));
	};

	// Merge live slaOk into static tab config
	const switcherTabs: SliceTab[] = SLICE_TABS.map((t) => ({
		...t,
		slaOk: slaStatus[t.key],
	}));

	// Shared props every slice component receives
	const shared = {
		switcherTabs,
		activeSlice,
		onSliceChange: setActiveSlice,
	};

	return (
		<>
			{/*
        All five slices are always mounted so their telemetry intervals
        keep running in the background — the switcher just hides/shows them.
        This means the dots in the tab strip stay live for every slice at
        all times, not just the one currently on screen.
      */}
			<div style={{ display: activeSlice === "vle" ? "contents" : "none" }}>
				<VLESlice {...shared} onSlaChange={(ok: boolean) => onSlaChange("vle", ok)} />
			</div>
			<div
				style={{
					display: activeSlice === "student_portal" ? "contents" : "none",
				}}
			>
				<StudentPortalSlice
					{...shared}
					onSlaChange={(ok: boolean) => onSlaChange("student_portal", ok)}
				/>
			</div>
			<div style={{ display: activeSlice === "admin" ? "contents" : "none" }}>
				<AdminSlice
					{...shared}
					onSlaChange={(ok: boolean) => onSlaChange("admin", ok)}
				/>
			</div>
			<div style={{ display: activeSlice === "iot" ? "contents" : "none" }}>
				<IoTSlice {...shared} onSlaChange={(ok: boolean) => onSlaChange("iot", ok)} />
			</div>
			<div style={{ display: activeSlice === "general" ? "contents" : "none" }}>
				<GeneralSlice
					{...shared}
					onSlaChange={(ok: boolean) => onSlaChange("general", ok)}
				/>
			</div>
		</>
	);
}
