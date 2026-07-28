import type { TooltipPayload } from "../../types/slice1";

interface SliceTooltipProps {
  active?:   boolean;
  payload?:  TooltipPayload[];
  decimals?: number;
}

export function SliceTooltip({ active, payload, decimals = 2 }: SliceTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-950 border border-white/10 rounded px-3 py-2 font-mono text-[11px] shadow-lg">
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color || "#e5e2e1" }}>
          {p.name}:{" "}
          <strong>
            {typeof p.value === "number" ? p.value.toFixed(decimals) : p.value}
          </strong>
        </div>
      ))}
    </div>
  );
}
