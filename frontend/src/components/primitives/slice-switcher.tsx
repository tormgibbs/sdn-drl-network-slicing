export type SliceKey = "vle" | "student_portal" | "admin" | "iot" | "general";

export interface SliceTab {
  key:      SliceKey;
  label:    string;
  priority: string;
  slaOk:    boolean;
}

interface SliceSwitcherProps {
  tabs:     SliceTab[];
  active:   SliceKey;
  onChange: (key: SliceKey) => void;
}

export function SliceSwitcher({ tabs, active, onChange }: SliceSwitcherProps) {
  return (
    <div className="flex overflow-x-auto border-b border-white/10 bg-black">
      {tabs.map((t) => {
        const isActive = t.key === active;
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={[
              "flex items-center gap-2 px-4 h-9 shrink-0 border-b-2 transition-colors duration-150",
              "font-mono text-[11px] whitespace-nowrap cursor-pointer bg-transparent border-0",
              isActive
                ? "border-b-blue-500 text-white bg-white/5"
                : "border-b-transparent text-white/40 hover:text-white/70",
            ].join(" ")}
          >
            {/* SLA dot */}
            <span className={[
              "w-1.5 h-1.5 rounded-full shrink-0",
              t.slaOk ? "bg-emerald-400" : "bg-red-500",
            ].join(" ")} />

            {t.label}

            {/* Priority badge */}
            <span className={[
              "font-mono text-[9px] px-1.5 py-0.5 rounded border",
              isActive
                ? "text-blue-400 border-blue-500/30 bg-blue-500/10"
                : "text-white/30 border-white/10",
            ].join(" ")}>
              {t.priority}
            </span>
          </button>
        );
      })}
    </div>
  );
}
