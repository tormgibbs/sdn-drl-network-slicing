import { RefreshCw } from "lucide-react";

export function SettingsTopBar({ savedAt }: { savedAt: string | null }) {
  return (
    <div className="h-12 flex-shrink-0 flex items-center justify-between px-4 bg-neutral-950 border-b border-neutral-800">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[11px] tracking-widest uppercase text-neutral-500">
          SETTINGS
        </span>
        <span className="text-neutral-700">/</span>
        <span className="font-mono text-[11px] tracking-widest uppercase text-neutral-100">
          TRAFFIC
        </span>
      </div>

      <div className="flex items-center gap-4">
        {savedAt && (
          <span className="font-mono text-[10px] tracking-wide text-green-400">
            SAVED {savedAt}
          </span>
        )}
        <button
          onClick={() => window.location.reload()}
          className="text-neutral-500 hover:text-neutral-300 transition-colors"
        >
          <RefreshCw size={14} />
        </button>
        <div className="w-6 h-6 rounded-full bg-neutral-900 border border-neutral-700 flex items-center justify-center font-mono text-[10px] text-neutral-400">
          CK
        </div>
      </div>
    </div>
  );
}