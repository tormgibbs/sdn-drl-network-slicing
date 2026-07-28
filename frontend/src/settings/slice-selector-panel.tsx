import { capacityBarColor } from "../data/settings";

type SliceMetaItem = { id: string; label: string };

export function SliceSelectorPanel({
  sliceMeta,
  selectedSlice,
  onSelectSlice,
  totalDemand,
  capacityMbps,
  capacityPct,
  onApplyAll,
  onResetDefaults,
  saving,
  hasMounted,
}: {
  sliceMeta:       SliceMetaItem[];
  selectedSlice:   string;
  onSelectSlice:   (id: string) => void;
  totalDemand:     number;
  capacityMbps:    number;
  capacityPct:     number;
  onApplyAll:      () => void;
  onResetDefaults: () => void;
  saving:          boolean;
  hasMounted:      boolean;
}) {
  return (
    <aside className="w-[220px] flex-shrink-0 border-r border-neutral-800 bg-black flex flex-col overflow-hidden">

      <div className="h-8 flex items-center px-4 border-b border-neutral-800 bg-neutral-950">
        <span className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
          Slices
        </span>
      </div>

      <ul className="flex-1 overflow-y-auto">
        {sliceMeta.map((s) => {
          const isActive = s.id === selectedSlice;
          return (
            <li
              key={s.id}
              onClick={() => onSelectSlice(s.id)}
              className={[
                "relative border-b border-neutral-800 h-9 flex items-center px-4 cursor-pointer transition-colors duration-100",
                "border-l-2",
                isActive
                  ? "border-l-neutral-100 bg-neutral-900"
                  : "border-l-transparent hover:bg-neutral-950",
              ].join(" ")}
            >
              <span className={`font-mono text-[13px] ${isActive ? "text-neutral-100" : "text-neutral-400"}`}>
                {s.label}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="border-t border-neutral-800 p-4 bg-black flex flex-col gap-2">
        <span className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
          Total Demand
        </span>

        <div className="flex items-baseline gap-1">
          <span className="font-mono text-[30px] font-medium text-neutral-100 tracking-tight">
            {totalDemand.toFixed(1)}
          </span>
          <span className="font-mono text-xs text-neutral-500">Mbps</span>
        </div>

        <span className="font-mono text-[10px] text-neutral-500">
          of {capacityMbps} Mbps capacity
        </span>

        <div className="w-full h-1 bg-neutral-900 relative overflow-hidden mt-1">
          <div
            className="absolute left-0 top-0 h-full transition-all duration-300"
            style={{
              width:      `${capacityPct}%`,
              background: capacityBarColor(capacityPct),
            }}
          />
        </div>

        <div className="flex flex-col gap-1.5 mt-2">
          <button
            onClick={onApplyAll}
            disabled={saving || !hasMounted}
            className="w-full py-1.5 bg-neutral-100 text-black font-mono text-[10px] font-semibold tracking-widest uppercase disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white transition-colors"
          >
            {saving ? "SAVING..." : "APPLY ALL"}
          </button>
          <button
            onClick={onResetDefaults}
            disabled={!hasMounted}
            className="w-full py-1.5 bg-transparent border border-neutral-800 text-neutral-400 font-mono text-[10px] font-medium tracking-widest uppercase hover:bg-neutral-950 hover:text-neutral-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            RESET DEFAULTS
          </button>
        </div>
      </div>
    </aside>
  );
}