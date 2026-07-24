import type { SLACellItem } from "../../../types/slice1";

export function SLAThresholdsPanel({ cells }: { cells: SLACellItem[] }) {
  return (
    <div className="border-b border-white/10">
      <div className="px-4 h-8 flex items-center border-b border-white/10 bg-white/[0.03]">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">SLA Thresholds</span>
      </div>
      <div className="grid grid-cols-2 gap-px bg-white/10 m-2 rounded overflow-hidden">
        {cells.map(({ label, value, highlight }) => (
          <div
            key={label}
            className={[
              "flex flex-col px-3 py-2",
              highlight ? "bg-white/[0.06]" : "bg-zinc-950",
            ].join(" ")}
          >
            <span className="font-mono text-[9px] text-white/30 uppercase tracking-widest mb-0.5">{label}</span>
            <span className={[
              "font-mono text-[12px] font-semibold",
              highlight ? "text-blue-400" : "text-white/75",
            ].join(" ")}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}