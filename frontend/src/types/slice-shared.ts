// ── Props every slice component receives from the slices.tsx route ────────────
// Add this to your existing types/slice1.ts (or wherever your slice types live)

import type { SliceKey, SliceTab } from "../components/primitives/SliceSwitcher";

export interface SliceSharedProps {
  /** Full tab list with live slaOk — passed into SliceLayout */
  switcherTabs:  SliceTab[];
  /** Which slice is currently visible */
  activeSlice:   SliceKey;
  /** Called when user clicks a different tab */
  onSliceChange: (key: SliceKey) => void;
  /** Called whenever this slice's SLA status changes — keeps the dot live */
  onSlaChange:   (ok: boolean) => void;
}
