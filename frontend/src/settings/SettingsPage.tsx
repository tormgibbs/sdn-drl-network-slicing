import { useState, useEffect, useCallback } from "react";
import { RefreshCw, Info } from "lucide-react";
import {
  SLICE_META,
  STORAGE_KEY,
  CAPACITY_MBPS,
  buildDefaults,
  headroomColor,
  capacityBarColor,
} from "../data/settings";
import type { SliceTrafficConfig, ConfigMap } from "../types/settings";

// ── ConfigInput ───────────────────────────────────────────────────────────────

function ConfigInput({
  label,
  value,
  onChange,
  hint,
  readOnly,
}: {
  label:     string;
  value:     string | number;
  onChange?: (v: string) => void;
  hint?:     string;
  readOnly?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
        {label}
      </label>

      {readOnly ? (
        <div className="h-8 border border-neutral-800 flex items-center px-2 font-mono text-[13px] text-neutral-100 bg-black">
          {value}
        </div>
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          className="h-8 bg-black border border-neutral-800 outline-none px-2 font-mono text-[13px] text-neutral-100 w-full focus:border-neutral-100 transition-colors"
        />
      )}

      {hint && (
        <span className="font-mono text-[10px] text-neutral-500 mt-0.5">{hint}</span>
      )}
    </div>
  );
}

// ── SettingsPage ──────────────────────────────────────────────────────────────

export function SettingsPage() {
  const [selectedSlice, setSelectedSlice] = useState("vle");
  const [configs,       setConfigs]       = useState<ConfigMap>(buildDefaults());
  const [saving,        setSaving]        = useState(false);
  const [savedAt,       setSavedAt]       = useState<string | null>(null);
  const [loading,       setLoading]       = useState(true);

  // Load from localStorage
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
    setLoading(false);
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
    { label: "BASELINE",         value: `${current.continuous_rate_mbps} Mbps`, color: "text-neutral-100" },
    { label: "PEAK BURST",       value: `+${peakBurst} Mbps`,                   color: "text-neutral-100" },
    { label: "SLA MINIMUM",      value: `${meta.slaMinMbps} Mbps`,              color: "text-neutral-400" },
    { label: "CAPACITY HEADROOM",value: `${headroom.toFixed(1)} Mbps`,          color: "" },
  ];

  return (
    // NOTE: AppSidebar lives in _app.tsx — not rendered here
    <div className="flex flex-col h-full overflow-hidden bg-black">

      {/* ── Top bar ── */}
      <div className="h-12 flex-shrink-0 flex items-center justify-between px-4 bg-neutral-950 border-b border-neutral-800">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] tracking-widest uppercase text-neutral-500">
            SETTINGS
          </span>
          <span className="text-neutral-700">/</span>
          <span className="font-mono text-[11px] tracking-widest uppercase text-neutral-100">
            TRAFFIC
          </span>
        </div>

        <div className="flex items-center gap-4">
          {savedAt && (
            <span className="font-mono text-[10px] tracking-wide text-green-400">
              SAVED {savedAt}
            </span>
          )}
          <button
            onClick={() => window.location.reload()}
            className="text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            <RefreshCw size={14} />
          </button>
          {/* Avatar / initials */}
          <div className="w-6 h-6 rounded-full bg-neutral-900 border border-neutral-700 flex items-center justify-center font-mono text-[10px] text-neutral-400">
            CK
          </div>
        </div>
      </div>

      {/* ── Content row ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Slice selector panel ── */}
        <aside className="w-[220px] flex-shrink-0 border-r border-neutral-800 bg-black flex flex-col overflow-hidden">

          {/* Panel header */}
          <div className="h-8 flex items-center px-4 border-b border-neutral-800 bg-neutral-950">
            <span className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
              Slices
            </span>
          </div>

          {/* Slice list */}
          <ul className="flex-1 overflow-y-auto">
            {SLICE_META.map((s) => {
              const isActive = s.id === selectedSlice;
              return (
                <li
                  key={s.id}
                  onClick={() => setSelectedSlice(s.id)}
                  className={[
                    "relative border-b border-neutral-800 h-9 flex items-center px-4 cursor-pointer transition-colors duration-100",
                    "border-l-2",
                    isActive
                      ? "border-l-neutral-100 bg-neutral-900"
                      : "border-l-transparent hover:bg-neutral-950",
                  ].join(" ")}
                >
                  <span className={`font-mono text-[13px] ${isActive ? "text-neutral-100" : "text-neutral-400"}`}>
                    {s.label}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Total demand + actions */}
          <div className="border-t border-neutral-800 p-4 bg-black flex flex-col gap-2">
            <span className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
              Total Demand
            </span>

            <div className="flex items-baseline gap-1">
              <span className="font-mono text-[30px] font-medium text-neutral-100 tracking-tight">
                {totalDemand.toFixed(1)}
              </span>
              <span className="font-mono text-xs text-neutral-500">Mbps</span>
            </div>

            <span className="font-mono text-[10px] text-neutral-500">
              of {CAPACITY_MBPS} Mbps capacity
            </span>

            {/* Capacity bar */}
            <div className="w-full h-1 bg-neutral-900 relative overflow-hidden mt-1">
              <div
                className="absolute left-0 top-0 h-full transition-all duration-300"
                style={{
                  width:      `${capacityPct}%`,
                  background: capacityBarColor(capacityPct),
                }}
              />
            </div>

            {/* Buttons */}
            <div className="flex flex-col gap-1.5 mt-2">
              <button
                onClick={applyAll}
                disabled={saving || loading}
                className="w-full py-1.5 bg-neutral-100 text-black font-mono text-[10px] font-semibold tracking-widest uppercase disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                {saving ? "SAVING..." : "APPLY ALL"}
              </button>
              <button
                onClick={resetDefaults}
                className="w-full py-1.5 bg-transparent border border-neutral-800 text-neutral-400 font-mono text-[10px] font-medium tracking-widest uppercase hover:bg-neutral-950 hover:text-neutral-200 transition-colors"
              >
                RESET DEFAULTS
              </button>
            </div>
          </div>
        </aside>

        {/* ── Config canvas ── */}
        <section className="flex-1 flex flex-col overflow-hidden relative bg-neutral-950">

          {/* Config header */}
          <div className="px-6 pt-5 pb-4 border-b border-neutral-800 flex justify-between items-end flex-shrink-0 bg-neutral-950">
            <div className="flex items-center gap-3">
              <span className="font-mono text-2xl font-medium text-neutral-100 tracking-tight">
                {meta.label}
              </span>
              <span
                className="font-mono text-[10px] px-2 py-0.5 border rounded-sm"
                style={{
                  color:       meta.priorityColor,
                  borderColor: meta.priorityColor + "44",
                  background:  meta.priorityColor + "12",
                }}
              >
                {meta.priorityLabel}
              </span>
              <span className="font-mono text-[10px] px-2 py-0.5 border border-neutral-700 text-neutral-400 rounded-sm">
                {meta.pattern}
              </span>
            </div>
            <span className="font-mono text-[13px] text-neutral-500">
              {current.continuous_device_count.toLocaleString()} devices
            </span>
          </div>

          {/* Two-column config */}
          <div className="flex-1 flex overflow-auto pb-[88px]">

            {/* Left: Continuous */}
            <div className="w-1/2 border-r border-neutral-800 p-6 flex flex-col gap-5 bg-neutral-950">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="font-mono text-[10px] font-semibold tracking-[0.12em] uppercase text-neutral-100">
                  Continuous
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <ConfigInput
                  label="Device Count"
                  value={current.continuous_device_count}
                  onChange={(v) => updateField("continuous_device_count", v)}
                />
                <ConfigInput
                  label="Port"
                  value={current.continuous_port}
                  readOnly
                />
              </div>

              <ConfigInput
                label="Target Rate (Mbps)"
                value={current.continuous_rate_mbps}
                onChange={(v) => updateField("continuous_rate_mbps", v)}
                hint={`Derived: ${derivedBps} bps`}
              />

              <div className="mt-auto border-t border-neutral-800 pt-4 flex items-center gap-2">
                <Info size={13} className="text-neutral-500 flex-shrink-0" />
                <span className="font-mono text-xs text-neutral-400">
                  {current.continuous_rate_mbps} Mbps continuous baseline
                </span>
              </div>
            </div>

            {/* Right: On/Off Burst */}
            <div className="w-1/2 p-6 flex flex-col gap-5 bg-neutral-950">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-orange-600" />
                <span className="font-mono text-[10px] font-semibold tracking-[0.12em] uppercase text-neutral-100">
                  On / Off Burst
                </span>
              </div>

              {/* Burst rate + port row */}
              <div className="flex flex-col gap-1">
                <label className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
                  BURST RATE (Mbps)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={current.burst_rate_mbps}
                    onChange={(e) => updateField("burst_rate_mbps", e.target.value)}
                    className="flex-1 h-8 bg-black border border-neutral-800 outline-none px-2 font-mono text-[13px] text-neutral-100 focus:border-neutral-100 transition-colors"
                  />
                  <div className="h-8 border border-neutral-800 flex items-center px-2 gap-2 bg-black min-w-[88px] justify-between">
                    <span className="font-mono text-[9px] tracking-widest text-neutral-500">PORT</span>
                    <span className="font-mono text-[13px] text-neutral-100">{current.burst_port}</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <ConfigInput
                  label="Mean On (s)"
                  value={current.mean_on_seconds}
                  onChange={(v) => updateField("mean_on_seconds", v)}
                />
                <ConfigInput
                  label="Mean Off (s)"
                  value={current.mean_off_seconds}
                  onChange={(v) => updateField("mean_off_seconds", v)}
                />
              </div>

              {/* Timeline preview */}
              <div className="flex flex-col gap-1.5">
                <label className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
                  Timeline Preview
                </label>
                <div className="w-full h-2 flex bg-black border border-neutral-800 overflow-hidden">
                  <div
                    className="h-full transition-all duration-300"
                    style={{ width: `${dutyCycle}%`, background: "#EA580C", opacity: 0.85 }}
                  />
                </div>
              </div>

              <div className="mt-auto border-t border-neutral-800 pt-4 flex justify-between items-center">
                <span className="font-mono text-xs text-neutral-400">
                  ~{dutyCycle.toFixed(0)}% duty cycle
                </span>
                <span className="font-mono text-xs text-neutral-100">
                  Peak demand +{current.burst_rate_mbps} Mbps
                </span>
              </div>
            </div>
          </div>

          {/* ── Sticky footer ── */}
          <div className="absolute bottom-0 left-0 right-0 border-t border-neutral-800 bg-black">

            {/* Metrics row */}
            <div className="px-4 py-2 flex justify-end gap-8">
              {footerMetrics.map(({ label, value, color }, i) => (
                <div key={label} className="flex flex-col items-end gap-0.5">
                  <span className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
                    {label}
                  </span>
                  <span
                    className={`font-mono text-[13px] ${color}`}
                    style={i === 3 ? { color: headroomColor(headroom) } : undefined}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>

            {/* Banner */}
            <div className="bg-neutral-950 border-t border-neutral-800 py-1.5 flex items-center justify-center gap-2">
              <RefreshCw size={12} className="text-neutral-500" />
              <span className="font-mono text-[10px] tracking-widest uppercase text-neutral-500">
                Changes take effect on the next traffic loop · Maximum delay 60 seconds
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
