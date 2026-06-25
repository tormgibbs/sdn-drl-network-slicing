// ── SliceSwitcher ─────────────────────────────────────────────────────────────
// A horizontal tab strip that sits above the slice content.
// Rendered once inside SliceLayout — each tab is a pill showing
// the slice name, priority badge, and a live SLA status dot.

export type SliceKey = "vle" | "student_portal" | "admin" | "iot" | "general";

export interface SliceTab {
  key:      SliceKey;
  label:    string;
  priority: string;
  /** Pass the current live SLA status so the dot stays reactive */
  slaOk:    boolean;
}

interface SliceSwitcherProps {
  tabs:     SliceTab[];
  active:   SliceKey;
  onChange: (key: SliceKey) => void;
}

export function SliceSwitcher({ tabs, active, onChange }: SliceSwitcherProps) {
  return (
    <div style={{
      display:         "flex",
      alignItems:      "center",
      gap:             1,
      backgroundColor: "var(--border)",
      borderBottom:    "1px solid var(--border)",
      overflowX:       "auto",
    }}>
      {tabs.map((t) => {
        const isActive = t.key === active;
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            style={{
              display:        "flex",
              alignItems:     "center",
              gap:            6,
              padding:        "0 14px",
              height:         34,
              background:     isActive ? "var(--bg-elevated)" : "var(--bg-base)",
              border:         "none",
              borderBottom:   isActive
                ? "2px solid #2B7FFF"
                : "2px solid transparent",
              cursor:         "pointer",
              fontFamily:     "'JetBrains Mono', monospace",
              fontSize:       11,
              color:          isActive ? "var(--text-pri)" : "var(--text-ter)",
              whiteSpace:     "nowrap",
              transition:     "color 0.15s, border-color 0.15s",
            }}
          >
            {/* SLA status dot */}
            <span style={{
              width:        6,
              height:       6,
              borderRadius: "50%",
              background:   t.slaOk ? "#4ADE80" : "#FB2C36",
              flexShrink:   0,
            }} />

            {t.label}

            {/* Priority badge */}
            <span style={{
              fontSize:    9,
              fontFamily:  "'JetBrains Mono', monospace",
              color:       isActive ? "#2B7FFF" : "var(--text-ter)",
              background:  isActive ? "#2B7FFF18" : "transparent",
              border:      `1px solid ${isActive ? "#2B7FFF44" : "var(--border)"}`,
              borderRadius: 3,
              padding:     "1px 5px",
              letterSpacing: "0.05em",
            }}>
              {t.priority}
            </span>
          </button>
        );
      })}
    </div>
  );
}
