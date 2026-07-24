import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { getDynamicState, initialData } from "#/data/dashboard";
import { computeSlaStatus } from "#/lib/sla";
import { SliceTable } from "#/components/primitives/slice-table.tsx";
import { PerformanceCharts } from "#/components/primitives/performance-charts";
import { SidePanel } from "#/components/primitives/side-panel";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import type { Mode, Scenario } from "#/types/slice";

export const Route = createFileRoute("/_app/")({ component: Home });

function Home() {
  const [controllerMode, setControllerMode] = useState<Mode>("agent");
  const [scenarioMode, setScenarioMode] = useState<Scenario>("normal");

  const liveMetrics = useLiveMetricsStore((s) => s.metrics);
  const agent = useLiveMetricsStore((s) => s.agent);

  const dynamicData = getDynamicState(controllerMode, scenarioMode);

  const totalAllocated = Object.values(dynamicData.allocations).reduce(
    (a, b) => a + b,
    0,
  );
  const MAX_BW = 1_000_000_000;
  const utilisedPct = ((totalAllocated / MAX_BW) * 100).toFixed(1);

  const totalAggregate =
    (dynamicData.metrics.vle.tx_throughput_bps +
      dynamicData.metrics.student_portal.tx_throughput_bps +
      dynamicData.metrics.admin.tx_throughput_bps +
      dynamicData.metrics.iot.tx_throughput_bps +
      dynamicData.metrics.general.tx_throughput_bps) /
    1_000_000;

  const sliceKeys = Object.keys(
    initialData.slices,
  ) as Array<keyof typeof initialData.slices>;

  const breachedSlice = sliceKeys.find((key) => {
    const latency = dynamicData.metrics[key].latency_ms ?? 0;
    return latency > initialData.slices[key].max_latency_ms;
  });

  // slaSatisfaction for SidePanel: live-sourced once the WS delivers metrics,
  // falls back to mock data before the first tick arrives. Main dashboard
  // (SliceTable/PerformanceCharts) stays on dynamicData for now — full
  // index.tsx rewire (mode derivation, scenario POST) is a separate,
  // later task per Section 10 — do not partially migrate it here.
  const slaSourceMetrics = liveMetrics ?? dynamicData.metrics;
  const nominalCount = sliceKeys.filter(
    (key) =>
      computeSlaStatus(slaSourceMetrics[key], initialData.slices[key]) ===
      "NOMINAL",
  ).length;
  const slaSatisfaction = ((nominalCount / sliceKeys.length) * 100).toFixed(1);

  const reward = agent?.reward ?? null;

  return (
    <div className="text-foreground p-4 flex justify-between gap-8">
      {/* Main Dashboard */}
      <div className="bg-muted p-4 flex-1">
        <div className="flex justify-between items-center mb-4">
          <p className="font-semibold text-3xl">Network Slice Status</p>
          <p>SYNC: 1.2ms ago</p>
        </div>

        <SliceTable dynamicData={dynamicData} utilisedPct={utilisedPct} />
        <PerformanceCharts
          dynamicData={dynamicData}
          totalAggregate={totalAggregate}
          breachedSlice={breachedSlice}
        />
      </div>

      {/* Side Panel */}
      <SidePanel
        controllerMode={controllerMode}
        scenarioMode={scenarioMode}
        slaSatisfaction={slaSatisfaction}
        reward={reward}
        onModeChange={setControllerMode}
        onScenarioChange={setScenarioMode}
      />
    </div>
  );
}