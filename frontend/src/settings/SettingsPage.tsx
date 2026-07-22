import { useState, useEffect, useCallback } from "react";
import {
  SLICE_META,
  STORAGE_KEY,
  CAPACITY_MBPS,
  buildDefaults,
  headroomColor,
} from "../data/settings";
import type { SliceTrafficConfig, ConfigMap } from "../types/settings";

import { SettingsTopBar } from "./settings-topbar";
import { SliceSelectorPanel } from "./slice-selectorPanel";
import { ConfigCanvas } from "./config-canvas";
import { SettingsFooter } from "./settings-footer"; 

export function SettingsPage() {
  const [selectedSlice, setSelectedSlice] = useState("vle");
  const [configs,       setConfigs]       = useState<ConfigMap>(buildDefaults());
  const [saving,        setSaving]        = useState(false);
  const [savedAt,       setSavedAt]       = useState<string | null>(null);

  // Server and first client render must agree — both start "not mounted".
  // Only after this effect runs (client-only) do we know it's safe to
  // read localStorage and reveal real content — avoids the hydration
  // mismatch that a naively-initialized `loading` state caused.
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data: SliceTrafficConfig[] = JSON.parse(stored);
        if (Array.isArray(data) && data.length > 0) {
          const map: ConfigMap = { ...buildDefaults() };
          for (const row of data) {
            map[row.slice_id] = {
              continuous_device_count: row.continuous_device_count,
              continuous_port:         row.continuous_port,
              continuous_rate_mbps:    Number(row.continuous_rate_mbps),
              burst_rate_mbps:         Number(row.burst_rate_mbps),
              burst_port:              row.burst_port,
              mean_on_seconds:         row.mean_on_seconds,
              mean_off_seconds:        row.mean_off_seconds,
            };
          }
          setConfigs(map);
        }
      }
    } catch {
      // corrupted storage — fall back to defaults
    }
    setHasMounted(true);
  }, []);

  const current = configs[selectedSlice];
  const meta    = SLICE_META.find((s) => s.id === selectedSlice)!;

  const updateField = useCallback(
    (field: keyof typeof current, raw: string) => {
      const num   = parseFloat(raw);
      const value = isNaN(num) ? (raw as unknown as number) : num;
      setConfigs((prev) => ({
        ...prev,
        [selectedSlice]: { ...prev[selectedSlice], [field]: value },
      }));
    },
    [selectedSlice],
  );

  const totalDemand  = Object.values(configs).reduce((sum, c) => sum + c.continuous_rate_mbps, 0);
  const headroom     = CAPACITY_MBPS - totalDemand;
  const capacityPct  = Math.min((totalDemand / CAPACITY_MBPS) * 100, 100);
  const peakBurst    = current.burst_rate_mbps;
  const dutyCycle    = current.mean_on_seconds + current.mean_off_seconds > 0
    ? (current.mean_on_seconds / (current.mean_on_seconds + current.mean_off_seconds)) * 100
    : 0;
  const derivedBps   = (current.continuous_rate_mbps * 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 0 });

  const applyAll = () => {
    setSaving(true);
    try {
      const rows: SliceTrafficConfig[] = SLICE_META.map((s) => ({
        slice_id:   s.id,
        ...configs[s.id],
        updated_at: new Date().toISOString(),
      }));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
      setSavedAt(new Date().toLocaleTimeString());
    } catch {
      // storage full or unavailable
    }
    setSaving(false);
  };

  const resetDefaults = () => {
    setConfigs(buildDefaults());
    setSavedAt(null);
  };

  const footerMetrics = [
    { label: "BASELINE",          value: `${current.continuous_rate_mbps} Mbps`, color: "text-neutral-100" },
    { label: "PEAK BURST",        value: `+${peakBurst} Mbps`,                   color: "text-neutral-100" },
    { label: "SLA MINIMUM",       value: `${meta.slaMinMbps} Mbps`,              color: "text-neutral-400" },
    { label: "CAPACITY HEADROOM", value: `${headroom.toFixed(1)} Mbps`,          color: "" },
  ];

  return (
    // NOTE: AppSidebar lives in _app.tsx — not rendered here
    <div className="flex flex-col h-full overflow-hidden bg-black">
      <SettingsTopBar savedAt={savedAt} />

      <div className="flex flex-1 overflow-hidden">
        <SliceSelectorPanel
          sliceMeta={SLICE_META}
          selectedSlice={selectedSlice}
          onSelectSlice={setSelectedSlice}
          totalDemand={totalDemand}
          capacityMbps={CAPACITY_MBPS}
          capacityPct={capacityPct}
          onApplyAll={applyAll}
          onResetDefaults={resetDefaults}
          saving={saving}
          hasMounted={hasMounted}
        />

        <ConfigCanvas
          meta={meta}
          current={current}
          updateField={updateField}
          derivedBps={derivedBps}
          dutyCycle={dutyCycle}
          hasMounted={hasMounted}
        />
      </div>

      {hasMounted && (
        <SettingsFooter
          metrics={footerMetrics}
          headroomColorValue={headroomColor(headroom)}
        />
      )}
    </div>
  );
}