// ── Shared recharts tooltip for all slice pages ───────────────────────────────
import type { TooltipPayload } from "../../types/slice1";

interface SliceTooltipProps {
  active?:  boolean;
  payload?: TooltipPayload[];
  /** decimal places to show; defaults to 2 */
  decimals?: number;
}

export function SliceTooltip({ active, payload, decimals = 2 }: SliceTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#1C1B1B",
      border: "1px solid #2A2A2A",
      padding: "6px 10px",
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11,
    }}>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color || "#E5E2E1" }}>
          {p.name}:{" "}
          <strong>
            {typeof p.value === "number" ? p.value.toFixed(decimals) : p.value}
          </strong>
        </div>
      ))}
    </div>
  );
}