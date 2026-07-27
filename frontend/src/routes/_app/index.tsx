import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect } from "react";
import { initialData } from "#/data/dashboard";
import { computeSlaStatus } from "#/lib/sla";
import { SliceTable } from "#/components/primitives/slice-table.tsx";
import { PerformanceCharts } from "#/components/primitives/performance-charts";
import { SidePanel } from "#/components/primitives/side-panel";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import { postTrafficScenario, getTrafficState, postAgentControl } from "#/lib/api";
import type { Scenario } from "#/types/slice";

export const Route = createFileRoute("/_app/")({ component: Home });

// Confirmed with teammate: laurel is the model for the demo.
const DEMO_MODEL_PATH = "models/selected/laurel";

// Matches the units MAX_BW was already defined in (bps) before this file
// went mock-free. agent.allocation_kbps arrives in kbps from the backend,
// so it's converted once here rather than silently mixing units.
const MAX_BW_BPS = 1_000_000_000;

function formatSync(lastUpdated: number | null, nowTick: number): string | null {
  if (lastUpdated === null) return null;
  const elapsedMs = nowTick - lastUpdated;
  if (elapsedMs < 1000) return "SYNC: just now";
  const elapsedSec = Math.floor(elapsedMs / 1000);
  if (elapsedSec < 60) return `SYNC: ${elapsedSec}s ago`;
  const elapsedMin = Math.floor(elapsedSec / 60);
  return `SYNC: ${elapsedMin}m ago`;
}

function Home() {
  const [scenarioMode, setScenarioMode] = useState<Scenario>("normal");
  const [isSwitchingScenario, setIsSwitchingScenario] = useState(false);
  const [isAgentBusy, setIsAgentBusy] = useState(false);

  // Drives the "SYNC: Xs ago" label — ticks once a second purely to force a
  // re-render so elapsed time stays current; it holds no state of its own,
  // the real source of truth is still lastUpdated from the store.
  const [nowTick, setNowTick] = useState(() => Date.now());

  const scenarioPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const liveMetrics = useLiveMetricsStore((s) => s.metrics);
  const metricsHistory = useLiveMetricsStore((s) => s.metricsHistory);
  const agent = useLiveMetricsStore((s) => s.agent);
  const lastUpdated = useLiveMetricsStore((s) => s.lastUpdated);
  const agentRunning = agent !== null;

  useEffect(() => {
    const id = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const syncLabel = formatSync(lastUpdated, nowTick);

  const sliceKeys = Object.keys(
    initialData.slices,
  ) as Array<keyof typeof initialData.slices>;

  // Real allocation source: the agent's own per-tick allocation_kbps.
  // Genuinely absent (not zero, not mocked) whenever the agent isn't
  // running or hasn't produced a result yet.
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

  // Same null-check-before-call pattern as slice-table.tsx: computeSlaStatus
  // takes non-nullable SliceMetrics, so a slice with no live data yet is
  // simply not counted as NOMINAL rather than being passed null into it.
  const nominalCount = sliceKeys.filter((key) => {
    const metric = liveMetrics?.[key] ?? null;
    return metric !== null && computeSlaStatus(metric, initialData.slices[key]) === "NOMINAL";
  }).length;
  const slaSatisfaction = ((nominalCount / sliceKeys.length) * 100).toFixed(1);

  const reward = agent?.reward ?? null;

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
      await postAgentControl({ action: "start", model_path: DEMO_MODEL_PATH });
    } catch (err) {
      console.error("agent start request failed", err);
    } finally {
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
          {syncLabel && <p>{syncLabel}</p>}
        </div>

        <SliceTable metrics={liveMetrics} utilisedPct={utilisedPct} />
        <PerformanceCharts
          metricsHistory={metricsHistory}
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