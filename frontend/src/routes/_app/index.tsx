// frontend/src/routes/_app/index.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PerformanceCharts } from "#/components/primitives/performance-charts";
import { SidePanel } from "#/components/primitives/side-panel";
import { SliceTable } from "#/components/primitives/slice-table.tsx";
import { initialData } from "#/data/dashboard";
import { useTrafficControl } from "#/hooks/use-traffic-control";
import { postControllerSwitch } from "#/lib/api";
import type { ActiveController } from "#/lib/schemas";
import { computeSlaStatus } from "#/lib/sla";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";

export const Route = createFileRoute("/_app/")({ component: Home });

const DEMO_MODEL_PATH = "models/selected/magnolia";
const MAX_BW_BPS = 100_000_000; // matches network.total_bandwidth_bps in config/slices.yaml

function Home() {
  const [isSwitchingController, setIsSwitchingController] = useState(false);
  const traffic = useTrafficControl();

  const liveMetrics = useLiveMetricsStore((s) => s.metrics);
  const metricsHistory = useLiveMetricsStore((s) => s.metricsHistory);
  const activeController = useLiveMetricsStore((s) => s.activeController);
  const agent = useLiveMetricsStore((s) => s.agent);
  const heuristicHistory = useLiveMetricsStore((s) => s.heuristicHistory);

  const sliceKeys = Object.keys(initialData.slices) as Array<keyof typeof initialData.slices>;

  const totalAllocatedKbps = agent
    ? Object.values(agent.allocation_kbps).reduce((a, b) => a + b, 0)
    : 0;
  const utilisedPct = agent
    ? (((totalAllocatedKbps * 1000) / MAX_BW_BPS) * 100).toFixed(1)
    : "0.0";

  const totalAggregate = liveMetrics
    ? sliceKeys.reduce(
        (sum, key) => sum + liveMetrics[key].tx_throughput_bps,
        0,
      ) / 1_000_000
    : 0;

  const breachedSlice = liveMetrics
    ? sliceKeys.find((key) => {
        const latency = liveMetrics[key].latency_ms ?? 0;
        return latency > initialData.slices[key].max_latency_ms;
      })
    : undefined;

  const nominalCount = sliceKeys.filter((key) => {
    const metric = liveMetrics?.[key] ?? null;
    return (
      metric !== null &&
      computeSlaStatus(metric, initialData.slices[key]) === "NOMINAL"
    );
  }).length;
  const slaSatisfaction = ((nominalCount / sliceKeys.length) * 100).toFixed(1);

  const reward = agent?.reward ?? null;
  const triggerCount = heuristicHistory.reduce(
    (sum, p) => sum + p.triggered.length,
    0,
  );

  const handleControllerChange = async (controller: ActiveController) => {
    setIsSwitchingController(true);
    try {
      await postControllerSwitch(
        controller === "agent"
          ? { controller, model_path: DEMO_MODEL_PATH }
          : { controller },
      );
    } catch (err) {
      console.error("controller switch failed", err);
    } finally {
      setIsSwitchingController(false);
    }
  };

  return (
    <div className="text-foreground p-4 flex justify-between gap-8">
      <div className="flex-1 flex flex-col gap-4">
        <SliceTable metrics={liveMetrics} utilisedPct={utilisedPct} />
        <PerformanceCharts
          metricsHistory={metricsHistory}
          totalAggregate={totalAggregate}
          breachedSlice={breachedSlice}
        />
      </div>
      <div className="w-80 shrink-0">
        <SidePanel
          activeController={activeController}
          isSwitchingController={isSwitchingController}
          onControllerChange={handleControllerChange}
          trafficRunning={traffic.running}
          isTrafficBusy={traffic.isTrafficBusy}
          onTrafficStart={traffic.startTraffic}
          onTrafficStop={traffic.stopTraffic}
          scenarioMode={traffic.scenarioMode}
          isSwitchingScenario={traffic.isSwitchingScenario}
          onScenarioChange={traffic.switchScenario}
          slaSatisfaction={slaSatisfaction}
          reward={reward}
          triggerCount={triggerCount}
        />
      </div>
    </div>
  );
}