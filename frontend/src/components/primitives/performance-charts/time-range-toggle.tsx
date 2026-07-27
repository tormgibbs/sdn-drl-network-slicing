type TimeRange = "1M" | "5M" | "15M";

type TimeRangeToggleProps = {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
};

const RANGES: TimeRange[] = ["1M", "5M", "15M"];

export function TimeRangeToggle({ value, onChange }: TimeRangeToggleProps) {
  return (
    <div className="flex gap-1">
      {RANGES.map((r) => (
        <button
          key={r}
          type="button"
          onClick={() => onChange(r)}
          className={`px-3 py-1 text-xs font-mono ${
            value === r ? "bg-primary text-primary-foreground" : "text-muted-foreground"
          }`}
        >
          {r}
        </button>
      ))}
    </div>
  );
}
