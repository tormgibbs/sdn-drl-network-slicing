import type { MetricRowItem } from "../../../types/slice1";

export function CurrentStatePanel({ rows }: { rows: MetricRowItem[] }) {
  return (
    <div className="border-b border-white/10">
      <div className="px-4 h-8 flex items-center border-b border-white/10 bg-white/[0.03]">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Current State</span>
      </div>
      {rows.map(({ label, value, highlight }, idx) => (
        <div
          key={`${label}-${idx}`}
          className={[
            "flex items-center justify-between px-4 py-1.5",
            highlight ? "bg-white/[0.04]" : "hover:bg-white/[0.02]",
          ].join(" ")}
        >
          <span className="font-mono text-[10px] text-white/35 uppercase tracking-wider">{label}</span>
          <span className={[
            "font-mono text-[11px]",
            highlight ? "text-blue-400" : "text-white/80",
          ].join(" ")}>{value}</span>
        </div>
      ))}
    </div>
  );
}