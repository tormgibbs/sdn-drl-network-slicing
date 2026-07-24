export interface SliceHeaderProps {
  name:        string;
  priority:    string;
  slaMet:      boolean | null; // null = no data received yet, distinct from a confirmed violation
  metricChips: string[];
  extraChips?: React.ReactNode;
  slaTargets:  string;
}

export function SliceHeader({ name, priority, slaMet, metricChips, extraChips, slaTargets }: SliceHeaderProps) {
  const slaBadgeClass =
    slaMet === null
      ? "text-white/40 border-white/15 bg-white/5"
      : slaMet
      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
      : "text-red-400 border-red-500/30 bg-red-500/10";

  const slaBadgeLabel = slaMet === null ? "NO DATA" : slaMet ? "MET" : "VIOLATION";

  return (
    <div className="flex flex-wrap items-center gap-2 px-4 h-11 border-b border-white/10 bg-zinc-950">
      <span className="font-mono text-[13px] font-semibold text-white tracking-wide">{name}</span>

      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded border border-white/15 text-white/50 bg-white/5">
        {priority}
      </span>

      <span className={[
        "font-mono text-[9px] px-1.5 py-0.5 rounded border font-medium tracking-widest uppercase",
        slaBadgeClass,
      ].join(" ")}>
        {slaBadgeLabel}
      </span>

      <div className="flex gap-1.5 ml-2">
        {metricChips.map((v) => (
          <span key={v} className="font-mono text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/70 bg-white/5">
            {v}
          </span>
        ))}
      </div>

      {extraChips && <div className="flex gap-1.5">{extraChips}</div>}

      <span className="font-mono text-[10px] text-white/30 ml-auto">{slaTargets}</span>
    </div>
  );
}