import { RefreshCw } from "lucide-react";

type FooterMetric = { label: string; value: string; color: string };

export function SettingsFooter({
  metrics,
  headroomColorValue,
}: {
  metrics:            FooterMetric[];
  headroomColorValue: string;
}) {
  return (
    <div className="absolute bottom-0 left-0 right-0 border-t border-neutral-800 bg-black">
      <div className="px-4 py-2 flex justify-end gap-8">
        {metrics.map(({ label, value, color }, i) => (
          <div key={label} className="flex flex-col items-end gap-0.5">
            <span className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
              {label}
            </span>
            <span
              className={`font-mono text-[13px] ${color}`}
              style={i === 3 ? { color: headroomColorValue } : undefined}
            >
              {value}
            </span>
          </div>
        ))}
      </div>

      <div className="bg-neutral-950 border-t border-neutral-800 py-1.5 flex items-center justify-center gap-2">
        <RefreshCw size={12} className="text-neutral-500" />
        <span className="font-mono text-[10px] tracking-widest uppercase text-neutral-500">
          Changes take effect on the next traffic loop · Maximum delay 60 seconds
        </span>
      </div>
    </div>
  );
}