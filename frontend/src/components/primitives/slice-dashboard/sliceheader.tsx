// frontend/src/components/primitives/slice-dashboard/sliceheader.tsx
export interface SliceHeaderProps {
  name: string;
  priority: string;
  slaMet: boolean | null; // null = no data received yet, distinct from a confirmed violation
  metricChips: string[];
  extraChips?: React.ReactNode;
  slaTargets: string;
}

export function SliceHeader({ name, slaMet, extraChips }: SliceHeaderProps) {
  const slaBadgeClass =
    slaMet === null
      ? "text-muted-foreground border-border bg-accent"
      : slaMet
      ? "text-[#00C950] border-[#00C950]/30 bg-[#00C950]/10"
      : "text-[#FB2C36] border-[#FB2C36]/30 bg-[#FB2C36]/10";
  const slaBadgeLabel = slaMet === null ? "NO DATA" : slaMet ? "MET" : "VIOLATION";

  return (
    <div className="flex items-center gap-3 px-4 h-11 border-b border-border bg-card">
      <span className="font-mono text-[13px] font-medium text-foreground tracking-wide">
        {name}
      </span>
      <span
        className={[
          "font-mono text-[9px] px-1.5 py-0.5 border font-medium tracking-wider uppercase",
          slaBadgeClass,
        ].join(" ")}
      >
        {slaBadgeLabel}
      </span>
      {extraChips && <div className="flex gap-1.5 ml-auto">{extraChips}</div>}
    </div>
  );
}
