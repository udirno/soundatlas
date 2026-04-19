# Phase 7: Visual Polish - Research

**Researched:** 2026-04-18
**Domain:** TailwindCSS 3.4 UI polish, Recharts 3.8 pie label overlap, Mapbox GL JS 3.20 popup styling
**Confidence:** HIGH

---

## Summary

This phase is pure CSS/component refinement — no new libraries needed, no backend changes. Every
requirement maps to a known, bounded change in an existing component. The tech stack (TailwindCSS,
Recharts, Mapbox GL) is already installed and working; this phase exclusively tightens the visual
quality of that output.

The hardest single problem is the Recharts pie chart label overlap (UI-04). Recharts 3.8 provides
no built-in collision-avoidance for Pie labels. The correct solution is a threshold filter: suppress
the label render function when `percent < 0.05` (slices under 5%) and rely on the existing
`<Tooltip>` for those slices. This is a 2-line change.

The second significant problem is the top-tracks duplicate-display bug (UI-08). Inspecting
`CountryPanel.tsx` lines 239-252, `track.album_name` is rendered correctly with a guard
(`{track.album_name && ...}`). The bug is most likely in what the API returns — `album_name` may
equal `track.name` for some records. The fix is either a display-layer deduplication guard
(`album_name !== name`) or an API-layer fix. Research finding: handle it at the display layer with
a simple inequality check, which is safe regardless of the root cause.

**Primary recommendation:** Apply all changes directly to existing component files using TailwindCSS
utility classes. No new dependencies. For pie labels, use the percent-threshold approach with a
custom SVG `<text>` render function. For Mapbox tooltips, the dark theme override already exists in
`globals.css`; only the HTML structure passed to `popup.setHTML()` needs a visual hierarchy upgrade.

---

## Standard Stack

### Core (already installed — no new installs needed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| TailwindCSS | 3.4.13 | All layout, spacing, typography | Default config, no plugins |
| Recharts | 3.8.0 | PieChart, RadarChart | Custom label render prop is the API for label control |
| Mapbox GL JS | 3.20.0 | Map tooltips via `mapboxgl.Popup` | Popup HTML styled via `globals.css` overrides |
| Next.js | 14.2.15 | App shell | No changes needed |
| Lucide React | 1.6.0 | Icons (X, MessageSquare) | Already used |

**No new packages to install.** All work is configuration changes and component edits.

---

## Architecture Patterns

### Recommended Project Structure (unchanged)

```
frontend/src/
├── app/
│   └── globals.css        # Mapbox popup CSS overrides live here
├── components/
│   ├── StatsSidebar.tsx   # UI-02
│   ├── CountryPanel.tsx   # UI-01, UI-03, UI-08
│   ├── GenrePieChart.tsx  # UI-04
│   ├── AudioFeatureChart.tsx  # (minor label polish)
│   ├── SearchBar.tsx      # UI-05
│   ├── MapView.tsx        # UI-06
│   ├── AIChatPanel.tsx    # UI-07 consistency check
│   └── HomeClient.tsx     # UI-07 layout frame
└── lib/
    └── colors.ts          # No changes needed
```

### Pattern 1: TailwindCSS Utility-First Refinement

**What:** All spacing, typography hierarchy, and border consistency are achieved by adjusting
existing Tailwind class strings in JSX. No custom CSS is added for component layout.

**When to use:** Spacing, font weight, text color, border radius, shadow adjustments.

**Key class tokens already in use in this codebase:**
- Background: `bg-gray-950`, `bg-gray-900`, `bg-gray-800`
- Borders: `border border-gray-800`, `border border-gray-700`
- Text hierarchy: `text-gray-100` (primary), `text-gray-300` (secondary), `text-gray-400/500` (meta)
- Spacing: `p-5`, `px-4 py-2.5`, `space-y-3`, `gap-2`
- Typography: `text-xs uppercase tracking-wider` (section headers), `text-sm font-medium` (item names)

### Pattern 2: Recharts Custom Label Render Function

**What:** The `label` prop on `<Pie>` accepts `(props: PieLabelRenderProps) => ReactNode`. Return
`null` to suppress a label entirely.

**PieLabelRenderProps fields available** (verified from `recharts/types/polar/Pie.d.ts`):
- `cx`, `cy` — chart center coordinates
- `x`, `y` — computed label position (at `outerRadius + offsetRadius`, default offsetRadius=20)
- `midAngle` — angle in degrees of the slice midpoint
- `outerRadius` — outer edge of the slice
- `percent` — fraction (0 to 1) of the total
- `name` — the `nameKey` value
- `value` — the `dataKey` value
- `textAnchor` — Recharts-computed `"start" | "middle" | "end"` based on x vs cx

**The label overlap fix:**

```typescript
// Source: recharts/types/polar/Pie.d.ts + recharts/lib/polar/Pie.js
const RADIAN = Math.PI / 180;
const MIN_PERCENT_FOR_LABEL = 0.05; // suppress labels on slices < 5%

function renderPieLabel(props: PieLabelRenderProps) {
  const { cx, cy, midAngle, outerRadius, name, percent } = props;
  if ((percent as number) < MIN_PERCENT_FOR_LABEL) return null;

  const radius = (outerRadius as number) + 20;
  const x = (cx as number) + radius * Math.cos(-((midAngle as number) ?? 0) * RADIAN);
  const y = (cy as number) + radius * Math.sin(-((midAngle as number) ?? 0) * RADIAN);
  const anchor = x > (cx as number) ? 'start' : 'end';

  return (
    <text
      x={x}
      y={y}
      textAnchor={anchor}
      dominantBaseline="central"
      fill="#9ca3af"
      fontSize={11}
    >
      {name}
    </text>
  );
}
```

Apply as: `<Pie label={renderPieLabel} labelLine={false} ...>`

**Important:** The existing code passes a bare arrow function to `label` which returns a string —
Recharts renders that string as an SVG `<text>`. The new function returns a full `<text>` element
with explicit `fill` and `fontSize`, giving color and size control. `labelLine={false}` stays.

### Pattern 3: Mapbox Popup HTML Structure

**What:** `popup.setHTML(html)` sets raw HTML inside `.mapboxgl-popup-content`. The dark theme
override in `globals.css` already applies background and font. The only change is improving the
HTML string structure inside `MapView.tsx`.

**Current HTML string (line 120 of MapView.tsx):**
```javascript
const html = `<strong>${props.name}</strong><br/>${props.artist_count} artists &middot; ${topGenre}`;
```

**Improved pattern — use inline styles because Tailwind classes are not available inside setHTML:**
```javascript
const html = `
  <div style="font-weight:600;font-size:13px;margin-bottom:4px;color:#f1f5f9">${props.name}</div>
  <div style="font-size:12px;color:#94a3b8">
    ${props.artist_count} artists &middot; ${topGenre}
  </div>
`;
```

**Why inline styles here:** The Mapbox popup DOM is injected outside React's render tree. Tailwind
utility classes are not purged to include popup-specific selectors. Inline styles are the correct
mechanism for popup HTML content. CSS overrides in `globals.css` handle container-level styling
(background, padding, border-radius).

### Pattern 4: Top Tracks Deduplication Guard

**What:** UI-08 — album name should not display if it equals the track name.

**Current code (CountryPanel.tsx lines 244-248):**
```typescript
{track.album_name && (
  <span className="text-gray-400 text-xs mt-0.5">
    {track.album_name}
  </span>
)}
```

**Fix (display-layer guard):**
```typescript
{track.album_name && track.album_name !== track.name && (
  <span className="text-gray-400 text-xs mt-0.5">
    {track.album_name}
  </span>
)}
```

This is the correct place to fix it: the API may return `album_name === name` for single tracks or
EP releases. The display layer should always guard against this degeneracy.

### Anti-Patterns to Avoid

- **Adding new CSS files per component:** All visual changes belong in the component's JSX classes
  or in `globals.css` for third-party HTML injection. No new `.module.css` files.
- **Adding `!important` to component JSX:** Reserve `!important` for `globals.css` Mapbox overrides
  only, where it is necessary to beat Mapbox's own CSS specificity.
- **Using `outerRadius` strings vs numbers in Recharts label math:** The Pie label render function
  receives numeric values for `cx`, `cy`, `outerRadius`, and `midAngle` at runtime, but TypeScript
  types show them as `number | string | undefined`. Always cast: `(outerRadius as number)`.
- **Removing the percent-threshold and trying label repositioning instead:** Recharts has no
  built-in label repositioning to avoid collisions. Any attempt to reposition labels manually
  requires computing all label rects and detecting intersections — this is significantly more work
  and fragile. The threshold approach is correct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pie label collision detection | Custom rect-intersection math across all labels | Percent-threshold suppression | Recharts places all labels at fixed `outerRadius + offset`; collision math requires knowing all rendered rects, which are only available post-paint |
| Dark Mapbox popup theme | In-JS CSS injection per popup instance | Single `globals.css` override (already exists) | Mapbox adds `.mapboxgl-popup-content` class reliably; one CSS rule covers all instances |
| Text overflow in panels | Custom truncation JS | `truncate` (Tailwind) or `min-w-0` on flex children | CSS handles this natively; JS truncation creates hydration issues in Next.js |
| Typography scale | Custom `rem` values | Tailwind's `text-xs/sm/base/lg` scale | Keeps visual system consistent across all components |

---

## Common Pitfalls

### Pitfall 1: Flex Child Text Overflow

**What goes wrong:** A flex child with long text (artist name, genre string) expands its flex
container width and overflows the panel.

**Why it happens:** Flex items have `min-width: auto` by default, which prevents them from
shrinking below their content width.

**How to avoid:** Add `min-w-0` to the flex child that contains the text. This allows `truncate`
(which applies `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`) to take effect.

**Example in codebase:** `CountryPanel.tsx` `ArtistRow` correctly has `<div className="flex-1 min-w-0">`.
Verify all other text-in-flex contexts have this pattern.

**Warning signs:** Text running outside its container border, or parent container expanding wider
than expected.

### Pitfall 2: Recharts ResponsiveContainer Height Clipping SVG Labels

**What goes wrong:** Pie labels at the top/bottom edges of the SVG are clipped when the
`ResponsiveContainer` height is too small relative to the chart's `outerRadius + offsetRadius`.

**Why it happens:** The SVG viewBox does not expand to accommodate labels that fall outside the
`height` boundary.

**How to avoid:** Ensure `ResponsiveContainer height` > `outerRadius * 2 + offsetRadius * 2 + margin`.
With `outerRadius={80}` and default `offsetRadius=20`, the minimum safe height is `80*2 + 20*2 = 200`.
The current value of `height={220}` is correct but tight. If labels are being clipped vertically,
increase to `height={260}`.

**Warning signs:** Top and bottom labels disappearing or being cut off.

### Pitfall 3: Mapbox Popup Tip Arrow Color Mismatch

**What goes wrong:** The popup body background is dark but the triangular tip arrow remains white
(its default color).

**Why it happens:** The tip arrow is rendered via CSS `border` tricks on `.mapboxgl-popup-tip`.
The `border-top-color` (for `anchor-bottom`) must match the popup background color.

**How to avoid:** The existing `globals.css` already overrides `.mapboxgl-popup-tip` with
`border-top-color`. Verify the anchor direction matches: Mapbox chooses `anchor-bottom` when the
popup is in the upper half of the map (tip points down, so `border-top-color` on the tip is the
relevant property). The current override is correct for the default case.

**Warning signs:** A white arrow tip appearing below or above a dark popup body.

### Pitfall 4: Section Header Uppercase Tracking Class Collision

**What goes wrong:** `StatsSidebar.tsx` line 41 applies both `font-semibold text-base` and
`text-xs` to the same `<h2>`. The `text-base` (16px) and `text-xs` (12px) conflict; last-class
wins in Tailwind's generated CSS order, which is determined by Tailwind's alphabetical/specificity
output — not DOM order. This may render inconsistently.

**Why it happens:** Legacy class accumulation without audit.

**How to avoid:** Audit all section header elements for conflicting text-size classes. Pick one
definitive size. The existing `text-xs uppercase tracking-wider` pattern used on other headers
in the same file is the correct baseline.

### Pitfall 5: Top Tracks Data Bug vs Display Bug

**What goes wrong:** UI-08 describes tracks showing duplicate content. This could be:
(a) `album_name` field is identical to `track.name` in the database (data bug)
(b) Incorrect field being rendered (code bug)

**Why it matters:** If the guard `track.album_name !== track.name` is added and the root cause is
actually (b) — i.e., the wrong field is being interpolated — the guard might silently hide valid
album names that happen to match a track name.

**How to avoid:** Add the guard. Then visually verify with a country that has tracks with known
distinct album names. If album names still don't appear, investigate whether the API's `top_tracks`
endpoint populates `album_name` correctly. The `TrackListItem` type (api.ts line 28-33) includes
`album_name: string | null` — it's a valid field.

---

## Code Examples

Verified patterns from reading source files:

### GenrePieChart.tsx — Replace inline label function

```typescript
// Source: /frontend/src/components/GenrePieChart.tsx + recharts/types/polar/Pie.d.ts
const RADIAN = Math.PI / 180;
const MIN_LABEL_PERCENT = 0.05;

function renderLabel(props: PieLabelRenderProps) {
  const { cx, cy, midAngle, outerRadius, name, percent } = props;
  if ((percent as number) < MIN_LABEL_PERCENT) return null;

  const radius = (outerRadius as number) + 20;
  const angle = (midAngle as number) ?? 0;
  const x = (cx as number) + radius * Math.cos(-angle * RADIAN);
  const y = (cy as number) + radius * Math.sin(-angle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      textAnchor={x > (cx as number) ? 'start' : 'end'}
      dominantBaseline="central"
      fill="#9ca3af"
      fontSize={11}
    >
      {name as string}
    </text>
  );
}

// In JSX:
<Pie
  data={chartData}
  dataKey="value"
  nameKey="name"
  cx="50%"
  cy="50%"
  outerRadius={80}
  label={renderLabel}
  labelLine={false}
>
```

### MapView.tsx — Improved popup HTML

```typescript
// Source: /frontend/src/components/MapView.tsx lines 119-121
// Replace the `html` template literal with:
const html = `
  <div style="font-weight:600;font-size:13px;margin-bottom:3px;color:#f1f5f9">
    ${props.name}
  </div>
  <div style="font-size:11px;color:#94a3b8">
    ${props.artist_count} artists &middot; ${topGenre}
  </div>
`;
```

### globals.css — Existing popup override (already correct, shown for reference)

```css
/* Source: /frontend/src/app/globals.css */
.mapboxgl-popup-content {
  background: rgba(15, 23, 42, 0.95) !important;
  color: #f8fafc !important;
  padding: 8px 12px !important;
  border-radius: 6px !important;
  font-size: 13px !important;
  line-height: 1.4 !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
}
.mapboxgl-popup-tip {
  border-top-color: rgba(15, 23, 42, 0.95) !important;
}
```

### StatsSidebar.tsx — Fix conflicting text size classes on h2 (line 41)

```typescript
// Source: /frontend/src/components/StatsSidebar.tsx line 41
// Current (broken): applies both text-base and text-xs — text-base wins
<h2 className="text-white font-semibold text-base tracking-wide mb-5 uppercase text-xs letter-spacing-wider text-gray-400">

// Fixed: single text size, consistent with other section headers in the file
<h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">
```

### CountryPanel.tsx — Top tracks deduplication

```typescript
// Source: /frontend/src/components/CountryPanel.tsx lines 244-248
// Change guard condition:
{track.album_name && track.album_name !== track.name && (
  <span className="text-gray-400 text-xs mt-0.5">
    {track.album_name}
  </span>
)}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Recharts `label` as string | Recharts `label` as render function returning ReactNode | Recharts v2+ | Full control over SVG `<text>` attributes (fill, fontSize, suppression) |
| Mapbox popup styled inline per instance | Override `.mapboxgl-popup-content` in global CSS | Mapbox GL JS v2+ | Single place to control all popup appearance |
| Custom scroll shadows | TailwindCSS `overflow-y-auto` + `backdrop-blur-sm` | TailwindCSS v3 | Simpler, hardware-accelerated |

**Deprecated/outdated:**
- `letter-spacing-wider` (line 41 of StatsSidebar.tsx): this is not a valid Tailwind class. The
  correct class is `tracking-wider`. This class is silently ignored by Tailwind, meaning the
  intended letter spacing is not applied.

---

## Component-by-Component Findings

### StatsSidebar.tsx (UI-02)

Current state: largely good. Issues found:
1. Line 41: `text-base` and `text-xs` conflict + `letter-spacing-wider` is not a valid Tailwind
   class (should be `tracking-wider`). Fix: replace the entire `className` string with the
   canonical section header pattern.
2. Metrics cards (`bg-gray-900 rounded-lg p-3 text-center`) are consistent — no change needed.
3. Diversity score section uses inline `style={{ width: diversityBarWidth }}` — correct, since the
   width is dynamic.

### CountryPanel.tsx (UI-01, UI-03, UI-08)

Current state: solid structure. Issues found:
1. UI-08: Top tracks `album_name` guard is present but doesn't guard against `album_name === name`.
   Fix: add `&& track.album_name !== track.name`.
2. UI-03: Section headers use consistent `text-sm font-semibold text-gray-300 uppercase tracking-wider`.
   No changes needed for headers. Artist rows use `min-w-0` correctly.
3. UI-01: All text containers use `truncate` on flex children with `min-w-0` — correctly set up.
   Spot-check: the `ArtistRow` genre display at line 39 `<p className="text-gray-500 text-xs truncate">`
   has `min-w-0` on its parent at line 36. Correct.

### GenrePieChart.tsx (UI-04)

Current state: label overlap is the primary issue.
- `height={220}`, `outerRadius={80}` — adequate container height.
- `label={({ name, percent }) => ... }` returns a string — no fill/size control.
- `labelLine={false}` — already set correctly.
- Fix: replace with the custom render function that suppresses small slices.

### SearchBar.tsx (UI-05)

Current state: functional but the dropdown items lack dividers between sections, and the Artists/
Tracks section labels (`text-gray-400 text-xs font-semibold uppercase tracking-wider border-b border-gray-800`)
are consistent with the panel section header style. The input uses `bg-gray-900 border border-gray-700` —
consistent with panel borders.

Minor opportunities: add `focus:ring-1 focus:ring-gray-600` to the input for a subtle focus ring;
ensure the dropdown's `rounded-lg` matches CountryPanel's header radius `rounded-lg`.

### MapView.tsx (UI-06)

Current state: Popup uses `setHTML()` with a simple `<strong>` + `<br/>` structure. The dark theme
CSS override is already in place and correct. The improvement is solely the HTML structure — add a
flex column layout with separate styled divs for name vs metadata.

The `mapboxgl-popup-tip` override uses `border-top-color` which applies to `anchor-bottom` popups
(the tip points downward, so the top border of the tip element faces upward). Mapbox defaults to
`anchor-bottom` when the popup appears above a point, which is the common case for a map tooltip.
This is correct.

### AIChatPanel.tsx (UI-07)

Current state: uses `bg-gray-900`, `border border-gray-700` for the container — slightly lighter
borders than the panels (`border-gray-800`). This is intentional for the floating chat widget.
No change needed unless border unification is explicitly required.

The chat button (`bg-blue-600`) is the only blue accent in the app. This is fine as a CTA element.

### HomeClient.tsx (UI-07)

Current state: `<main className="w-full h-screen relative">` — bare frame, no visual styling.
The panels float over it. No visual changes needed here.

---

## Open Questions

1. **UI-08 data vs display root cause**
   - What we know: `CountryPanel.tsx` renders `track.album_name` correctly when not null.
   - What's unclear: Whether `album_name === name` comes from the Spotify API (single tracks often
     have their track name as the album name) or a data pipeline bug.
   - Recommendation: Fix at display layer with `track.album_name !== track.name` guard. This is
     safe regardless. If album names still look wrong after the fix, the planner should add a
     task to investigate the `/api/countries/{id}` `top_tracks` response payload.

2. **Pie chart label font weight**
   - What we know: the custom SVG `<text>` render function gives full control.
   - What's unclear: whether `fontSize={11}` at the current `outerRadius={80}` will render readably
     on the `w-96` panel (384px wide).
   - Recommendation: Use `fontSize={11}` with `fill="#9ca3af"` (gray-400). If legibility is poor
     at runtime, bump to `fontSize={12}`.

---

## Sources

### Primary (HIGH confidence)
- `/frontend/src/components/*.tsx` — direct source reading of all 8 components
- `/frontend/node_modules/recharts/types/polar/Pie.d.ts` — verified `PieLabelRenderProps` fields
- `/frontend/node_modules/recharts/lib/polar/Pie.js` — verified label render pipeline and `offsetRadius=20` default
- `/frontend/src/app/globals.css` — existing Mapbox popup override confirmed present and correct
- `/frontend/node_modules/mapbox-gl/dist/mapbox-gl.css` — confirmed `.mapboxgl-popup-content` and `.mapboxgl-popup-tip` class names and default styles
- `/frontend/package.json` — exact versions confirmed: recharts 3.8.0, mapbox-gl 3.20.0, tailwindcss 3.4.13

### Secondary (MEDIUM confidence)
- TailwindCSS `min-w-0` flex pattern — established CSS behavior, no source needed
- SVG `textAnchor` and `dominantBaseline` attributes — SVG 1.1 specification behavior

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions read directly from `package.json` and `node_modules`
- Architecture: HIGH — all component files read in full; findings based on actual code
- Pitfalls: HIGH — most pitfalls identified from reading the actual code (StatsSidebar class conflict,
  ArtistRow min-w-0, album_name guard); one (label font size legibility) is MEDIUM
- Recharts label API: HIGH — verified from TypeScript type definitions and compiled source

**Research date:** 2026-04-18
**Valid until:** 2026-06-01 (stable libraries; Recharts and Mapbox GL rarely have breaking label API changes in patch versions)
