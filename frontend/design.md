# Better Auth — Design System Reference

Source: better-auth.com/brand — pulled live from the same variables used across product and docs.

---

## 01 · Foundations

### Color

| Token | Variable | Hex |
|---|---|---|
| Background | `--background` | `#000000` |
| Foreground | `--foreground` | `#FAFAF9` |
| Primary | `--primary` | `#FAFAF9` |
| Primary FG | `--primary-foreground` | `#1C1917` |
| Secondary | `--secondary` | `#292524` |
| Secondary FG | `--secondary-foreground` | `#FAFAF9` |
| Muted | `--muted` | `#292524` |
| Muted FG | `--muted-foreground` | `#A6A09B` |
| Accent | `--accent` | `#292524` |
| Accent FG | `--accent-foreground` | `#FAFAF9` |
| Border | `--border` | `#292524` |
| Input | `--input` | `#292524` |
| Ring | `--ring` | `#797168` |
| Destructive | `--destructive` | `#82181A` |

**Callout accents**

| Accent | Hex |
|---|---|
| Info | `#2B7FFF` |
| Warn | `#FF6900` |
| Error | `#FB2C36` |
| Success | `#00C950` |

### Typography

Geist for UI, Geist Mono for code and metadata.

| Style | Classes | Example |
|---|---|---|
| Geist Sans · H1 | `text-4xl tracking-tight` | "Authentication, better." |
| Geist Sans · H2 | `text-xl tracking-tight` | "Drop-in, framework-agnostic." |
| Geist Sans · Body | `text-sm` | "The quick brown fox jumps over the lazy dog. 0123456789." |
| Geist Mono · Label | `text-[11px] font-mono uppercase tracking-wider` | "API / BETTER-AUTH / V1.4.0" |
| Geist Mono · Code | `font-mono text-sm` | `const auth = betterAuth({ secret, baseURL });` |

### Radius

Base is `0.2rem` — deliberately tight. Code blocks and inline callouts break to 0 for a sharper, more editorial feel.

| Token | Value |
|---|---|
| sharp (code) | `0` |
| sm | `calc(var(--radius) - 2px)` |
| md | `calc(var(--radius) - 1px)` |
| lg (default) | `var(--radius)` |
| xl | `calc(var(--radius) + 4px)` |

### Shadow

Shadows are used sparingly — only to lift interactive affordances. Code blocks and cards stay flat.

Scale: `shadow-xs`, `shadow-sm`, `shadow-md`, `shadow-lg`, `shadow-xl`

---

## 02 · Motifs

Background textures, used sparingly as section/page dressing — not on interactive surfaces.

| Motif | Class | Spec |
|---|---|---|
| Grid | `.bg-grid` | 32px |
| Grid (small) | `.bg-grid-small` | 8px |
| Dot | `.bg-dot` | 16px |

---

## 03 · Components

### Buttons

Six variants, four sizes.

**Variants:** Default, Secondary, Outline, Ghost, Link, Destructive
**Sizes:** Small, Default, Large, Icon (`+`)

- Default: filled, foreground-colored bg, dark text (`--primary` / `--primary-foreground`)
- Secondary: filled, `--secondary` bg
- Outline: bordered, transparent bg
- Ghost: no border, no bg, text-only until hover
- Link: text-only, underline affordance
- Destructive: `--destructive` bg (`#82181A`), white text

### Inputs

Sharp, minimal affordances. Sharp corners (radius 0 or near-0), thin border (`--input`), uppercase mono micro-labels above each field (e.g. `EMAIL`, `PASSWORD`).

### Card

Flat border, no shadow. Uses dashed footer rules for meta.

Structure: title, 1–2 line description, dashed horizontal rule, meta row (e.g. version tag, count) below the rule.

Example instances: "Session" card ("The canonical unit of auth state on every request." / meta: `v1.4.0`), "Plugin" card ("Opt-in capability — organizations, 2FA, magic links." / meta: `30+ plugins`).

### Callouts

Dashed left stripe, sized/colored to the accent type. Bold title line + supporting description line.

| Type | Icon color | Example title | Example body |
|---|---|---|---|
| Info | Blue `#2B7FFF` | Heads up | Callouts use a dashed left stripe sized to the accent type. |
| Warn | Orange `#FF6900` | Careful | This action rotates signing keys and invalidates every active session. |
| Error | Red `#FB2C36` | Broken | The database adapter returned an unexpected shape. |
| Success | Green `#00C950` | Nice | Your provider connected and synced successfully. |

### Tabs

Segmented control style, sharp corners, active tab has filled/contrasting background (secondary token), inactive tabs are muted text on transparent bg. Used to switch code-sample language (e.g. TypeScript / JavaScript / Shell) above a code block.

### Badges

Small, sharp-cornered, uppercase-or-lowercase label pills matching button variant styling.

Variants: `default`, `secondary`, `destructive`, `outline`

### Alerts

Flat block, no icon required. Bold title line + description line. Neutral (foreground-colored title) for informational, red/destructive-colored title+body for failure states.

Examples: "Auth secret updated" (neutral) / "Sign-in failed" (destructive — red title and body).

---

## 04 · Logo

*(not yet captured — add when available)*

---

## 05 · Voice

How Better Auth communicates — across docs, product copy, and marketing.

- **Clear over clever** — name things what they are. Session, key, secret — not `SessionManagerV2Provider`.
- **Terse, but warm** — short sentences, no marketing fluff. Sound like a thoughtful engineer, not a billboard.
- **Show the code** — a well-named snippet does more than a paragraph. Prose sets context; code proves it.
- **Sharp, not loud** — minimal radii, dashed dividers, mono for metadata. The design should feel precise, never decorative.

---

## Application Notes for This Project

When restyling the SDN dashboard toward this system:

- Swap current ad-hoc Tailwind classes (`bg-muted`, `text-foreground`) for these exact token values via `components.json`'s `cssVariables` — the aliases already match (`--background`, `--foreground`, `--muted`, etc.), so this is largely a value-substitution job, not a rewrite.
- SLA violation states → use the Alert/Callout destructive pattern (red title + dashed left stripe), not a generic red box.
- Metrics cards (per-slice throughput/latency/loss) → adopt the flat-border, dashed-footer-rule Card pattern; put slice name as title, live values as body, dashed rule + timestamp/sync-label as meta footer — this maps directly onto the existing `syncLabel` you already compute in `Home`.
- Scenario switcher → shadcn RadioGroup (already decided) styled with these tokens.
- Agent Start/Stop button → Default variant when stopped (call to action), Destructive or Outline when running (stop action).
- Numeric/metric values and anything code-like (S-NSSAI, VLAN IDs, IPs) → Geist Mono, per "Show the code" voice principle.
- Radius should stay tight (`0.2rem` base) throughout — do not introduce large rounded corners anywhere, including charts/cards.
