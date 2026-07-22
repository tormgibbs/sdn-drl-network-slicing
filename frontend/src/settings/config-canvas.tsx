import { Info } from "lucide-react";
import { ConfigInput } from "./config-input";
import type { ConfigMap } from "../types/settings";

type SliceConfigValue = ConfigMap[string];
type SliceMetaItem = {
  id: string;
  label: string;
  priorityColor: string;
  priorityLabel: string;
  pattern: string;
};

export function ConfigCanvas({
  meta,
  current,
  updateField,
  derivedBps,
  dutyCycle,
  hasMounted,
}: {
  meta:        SliceMetaItem;
  current:     SliceConfigValue;
  updateField: (field: keyof SliceConfigValue, raw: string) => void;
  derivedBps:  string;
  dutyCycle:   number;
  hasMounted:  boolean;
}) {
  if (!hasMounted) {
    return (
      <section className="flex-1 flex items-center justify-center bg-neutral-950">
        <span className="font-mono text-[11px] tracking-widest uppercase text-neutral-600">
          Loading configuration…
        </span>
      </section>
    );
  }

  return (
    <section className="flex-1 flex flex-col overflow-hidden relative bg-neutral-950">
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
    </section>
  );
}