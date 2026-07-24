import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect } from "react";
import { getDynamicState, initialData } from "#/data/dashboard";
import { computeSlaStatus } from "#/lib/sla";
import { SliceTable } from "#/components/primitives/slice-table.tsx";
import { PerformanceCharts } from "#/components/primitives/performance-charts";
import { SidePanel } from "#/components/primitives/side-panel";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import { postTrafficScenario, getTrafficState, postAgentControl } from "#/lib/api";
import type { Mode, Scenario } from "#/types/slice";

export const Route = createFileRoute("/_app/")({ component: Home });

// TODO: confirm correct model with teammate — ivy/juniper/kingwood/laurel are
// the candidates seen in models/selected/. .zip is appended automatically by
// the backend if omitted, so either "models/selected/ivy" or the full
// "models/selected/ivy.zip" works.
const DEMO_MODEL_PATH = "models/selected/ivy";

function Home() {
  const [scenarioMode, setScenarioMode] = useState<Scenario>("normal");
  const [isSwitchingScenario, setIsSwitchingScenario] = useState(false);
  const [isAgentBusy, setIsAgentBusy] = useState(false);

  const scenarioPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const liveMetrics = useLiveMetricsStore((s) => s.metrics);
  const agent = useLiveMetricsStore((s) => s.agent);
  const agentRunning = agent !== null;

  // Mode fed into getDynamicState is a cosmetic pre-live-data mock-fallback
  // placeholder only — "heuristic" is never produced here, since it was never
  // a real live/switchable backend state (confirmed: static/heuristic/DRL are
  // offline experimental conditions, not live toggles). Not a real mode
  // selection; purely picks which mock dataset to show before the first WS
  // tick arrives.
  const mockFallbackMode: Mode = agentRunning ? "agent" : "static";
  const dynamicData = getDynamicState(mockFallbackMode, scenarioMode);

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

  const slaSourceMetrics = liveMetrics ?? dynamicData.metrics;
  const nominalCount = sliceKeys.filter(
    (key) =>
      computeSlaStatus(slaSourceMetrics[key], initialData.slices[key]) ===
      "NOMINAL",
  ).length;
  const slaSatisfaction = ((nominalCount / sliceKeys.length) * 100).toFixed(1);

  const reward = agent?.reward ?? null;

  // Clean up any in-flight poll on unmount
  useEffect(() => {
    return () => {
      if (scenarioPollRef.current) clearInterval(scenarioPollRef.current);
    };
  }, []);

  const handleScenarioChange = async (scenario: Scenario) => {
    setScenarioMode(scenario);
    setIsSwitchingScenario(true);

    try {
      await postTrafficScenario({ scenario });
    } catch (err) {
      console.error("scenario switch request failed", err);
      setIsSwitchingScenario(false);
      return;
    }

    // Confirmation lag is real: the backend only picks up the new scenario at
    // the next traffic loop boundary, not immediately. Worst case is one full
    // loop duration + inter_loop_gap_sec (~65s default) — this is expected
    // backend behavior (confirmed from traffic/runner.py), not a bug.
    if (scenarioPollRef.current) clearInterval(scenarioPollRef.current);
    scenarioPollRef.current = setInterval(async () => {
      try {
        const state = await getTrafficState();
        if (state.last_loop?.scenario === scenario) {
          setIsSwitchingScenario(false);
          if (scenarioPollRef.current) clearInterval(scenarioPollRef.current);
        }
      } catch (err) {
        console.error("traffic state poll failed", err);
      }
    }, 2500);
  };

  const handleAgentStart = async () => {
    setIsAgentBusy(true);
    try {
      // "start" synchronously loads a PPO model from disk on the backend
      // before responding — expect a real, if usually short, delay here.
      await postAgentControl({ action: "start", model_path: DEMO_MODEL_PATH });
    } catch (err) {
      console.error("agent start request failed", err);
    } finally {
      // Confirmation that the agent is actually running comes from the WS
      // `agent` field turning non-null, not from this response — the WS
      // envelope only updates on its own broadcast cadence, so there's a
      // small (seconds-scale) additional lag beyond this request resolving.
      setIsAgentBusy(false);
    }
  };

  const handleAgentStop = async () => {
    setIsAgentBusy(true);
    try {
      await postAgentControl({ action: "stop" });
    } catch (err) {
      console.error("agent stop request failed", err);
    } finally {
      setIsAgentBusy(false);
    }
  };

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
        agentRunning={agentRunning}
        isAgentBusy={isAgentBusy}
        onAgentStart={handleAgentStart}
        onAgentStop={handleAgentStop}
        scenarioMode={scenarioMode}
        isSwitchingScenario={isSwitchingScenario}
        onScenarioChange={handleScenarioChange}
        slaSatisfaction={slaSatisfaction}
        reward={reward}
      />
    </div>
  );
}