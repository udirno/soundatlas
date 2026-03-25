---
phase: 04-map-view-and-country-detail
plan: 02
subsystem: ui
tags: [mapbox, react, nextjs, typescript, tailwind]

# Dependency graph
requires:
  - phase: 04-01
    provides: MapView component with GeoJSON circle layer, onCountrySelect prop interface, CountryListItem type, fetchCountryDetail/fetchCountryComparison in api.ts

provides:
  - Hover tooltip on country circles (dark-styled mapboxgl.Popup)
  - Click-to-fly map animation (flyTo with zoom >= 4, 1200ms)
  - CountryPanel component with country name, region label, iso_alpha2 badge, loading/error states, placeholder sections
  - HomeClient wrapper managing selectedCountryId state
  - Dynamic import of MapView with ssr:false moved to HomeClient (client component context)
  - page.tsx simplified to server component fetching countries and rendering HomeClient

affects: [04-03, 05-search-and-recommendations, 06-ai-insights]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CountryPanel fetches its own data via useEffect — MapView only emits countryId (decoupled pattern from research anti-pattern guidance)"
    - "HomeClient as client wrapper: selectedCountryId state lives here, dynamic imports with ssr:false belong in client components"
    - "Mapbox feature properties accessed via `e.features[0].properties as TypeName` cast (double-cast via unknown not needed, direct cast works)"

key-files:
  created:
    - frontend/src/components/CountryPanel.tsx
    - frontend/src/components/HomeClient.tsx
  modified:
    - frontend/src/components/MapView.tsx
    - frontend/src/app/page.tsx
    - frontend/src/app/globals.css

key-decisions:
  - "Access Mapbox GeoJSONFeature.properties via direct `as CountryFeatureProperties` cast — TypeScript does not allow direct Feature<Point, T> cast due to GeoJsonProperties type, but properties field cast alone works"
  - "comparison state stored in CountryPanel for Plan 03 use even though not rendered in Plan 02 — avoids refetch pattern later"
  - "Dynamic import of MapView (ssr:false) moved from page.tsx to HomeClient.tsx — ssr:false requires client component context"

patterns-established:
  - "Panel owns its own data fetching: CountryPanel useEffect fetches detail + comparison in parallel, not MapView's concern"
  - "selectedCountryId state in HomeClient: null = panel closed, number = panel open with that id"

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 4 Plan 02: Map Interactions and Country Detail Panel Summary

**Hover tooltips via mapboxgl.Popup, click-to-fly animation, and CountryPanel with region label wired through HomeClient selectedCountryId state**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-25T05:09:50Z
- **Completed:** 2026-03-25T05:12:40Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Hover over a country circle shows dark-styled tooltip with name, artist count, and top genre; mouse leave removes it
- Click on circle triggers flyTo animation (zoom clamped to max(current, 4), 1200ms) and calls onCountrySelect
- CountryPanel component fetches countryDetail + comparison in parallel, shows country name, region label (CTRY-01), iso_alpha2 badge, loading/error states, and placeholder sections ready for Plan 03
- HomeClient wrapper manages selectedCountryId state; panel opens on click, closes via X button
- page.tsx simplified to pure server component; dynamic MapView import (ssr:false) moved to HomeClient

## Task Commits

Each task was committed atomically:

1. **Task 1: Add hover tooltip and click-to-fly interactions to MapView** - `6649de1` (feat)
2. **Task 2: Create CountryPanel with region label and wire selectedCountryId state via HomeClient** - `b4f3064` (feat)

## Files Created/Modified

- `frontend/src/components/MapView.tsx` - Added mousemove/mouseleave tooltip handlers, click-to-fly + onCountrySelect call
- `frontend/src/app/globals.css` - Dark tooltip popup styling for mapboxgl-popup-content and mapboxgl-popup-tip
- `frontend/src/components/CountryPanel.tsx` - New: right-side panel, fetches detail + comparison, shows name/region/iso/loading/error/sections
- `frontend/src/components/HomeClient.tsx` - New: client wrapper with selectedCountryId state, dynamic MapView import
- `frontend/src/app/page.tsx` - Simplified to fetch countries + render HomeClient

## Decisions Made

- Mapbox `e.features[0].properties` accessed via direct `as CountryFeatureProperties` cast — direct `Feature<Point, T>` cast fails due to `GeoJsonProperties` type incompatibility with TypeScript's type checker; properties-only cast is the idiomatic workaround
- `comparison` state stored in CountryPanel even though not yet rendered — avoids an extra refetch in Plan 03 when audio feature charts need it
- `dynamic(..., { ssr: false })` moved from `page.tsx` to `HomeClient.tsx` — Next.js requires ssr:false dynamic imports to be inside a client component; page.tsx is a server component

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript cast for Mapbox GeoJSONFeature properties**
- **Found during:** Task 1 (hover tooltip implementation)
- **Issue:** `e.features[0] as GeoJSON.Feature<GeoJSON.Point, CountryFeatureProperties>` fails type check — `GeoJsonProperties` (`{ [name: string]: any }`) is not assignable to `CountryFeatureProperties` (specific required fields)
- **Fix:** Cast `e.features[0].properties as CountryFeatureProperties` and `e.features[0].geometry as GeoJSON.Point` separately
- **Files modified:** `frontend/src/components/MapView.tsx`
- **Verification:** `npx tsc --noEmit` passes with no errors
- **Committed in:** `6649de1` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Type-only fix, no behavior change. Required for TypeScript to compile.

## Issues Encountered

- Build-time "Failed to fetch countries" log is expected behavior — backend not running at build time, try/catch in page.tsx handles this gracefully; countries defaults to `[]` and map renders empty.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CountryPanel shell ready: placeholder sections (`<section>` + `<h3>`) for artists, genre breakdown, audio features, top tracks are in place for Plan 03 to replace with real components
- `comparison` state already stored in panel, ready for audio feature comparison charts
- Build passes; all type checks clean

## Self-Check: PASSED

- FOUND: frontend/src/components/MapView.tsx
- FOUND: frontend/src/components/CountryPanel.tsx
- FOUND: frontend/src/components/HomeClient.tsx
- FOUND: frontend/src/app/page.tsx
- FOUND: frontend/src/app/globals.css
- FOUND commit: 6649de1
- FOUND commit: b4f3064

---
*Phase: 04-map-view-and-country-detail*
*Completed: 2026-03-25*
