---
phase: 05-global-stats-and-search
plan: 02
subsystem: ui
tags: [react, mapbox, typescript, tailwind, debounce, search]

requires:
  - phase: 05-global-stats-and-search
    provides: fetchSearch() API client, SearchArtistHit/SearchTrackHit types with country_id
  - phase: 04-map-view
    provides: MapView component, HomeClient, CountryPanel with onCountrySelect pattern

provides:
  - SearchBar component with debounced autocomplete (300ms) for artists and tracks
  - MapView flyToTarget prop for programmatic map navigation
  - Full search-to-map-navigation flow (search → select → fly → open panel)

affects:
  - 06-ai-chat (may need similar map navigation from chat responses)

tech-stack:
  added: []
  patterns:
    - "SearchBar uses 300ms debounce via setTimeout in useEffect with cleanup"
    - "MapView flyToTarget prop pattern: parent sets target, map.once('moveend') clears via onFlyToComplete callback"
    - "useCallback for stable function references passed to child components (handleSearchSelect, handleFlyToComplete)"
    - "Click-outside detection via useRef + document mousedown listener"

key-files:
  created:
    - frontend/src/components/SearchBar.tsx
  modified:
    - frontend/src/components/MapView.tsx
    - frontend/src/components/HomeClient.tsx

key-decisions:
  - "flyToTarget prop pattern instead of forwardRef — simpler with next/dynamic SSR-disabled components"
  - "map.once('moveend') to clear flyToTarget after animation completes — prevents race condition with synchronous state clear"
  - "useCallback for handleSearchSelect and onFlyToComplete — inline functions caused useEffect re-fires from changing deps"
  - "Tracks not in library shown disabled with 'Not in your library' badge, not clickable"
  - "Null country_id shows inline 'Country not mapped' message instead of breaking navigation"

patterns-established:
  - "Programmatic map navigation: set flyToTarget state → MapView flies → moveend clears target"

duration: 5m
completed: 2026-03-25
---

# Phase 5 Plan 02: Search Bar with Map Navigation Summary

**Debounced search autocomplete (300ms) with artist/track fuzzy matching, map fly-to on selection, and CountryPanel auto-open — completing the full search-to-discovery flow**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-25T07:32:00Z
- **Completed:** 2026-03-25T07:50:42Z
- **Tasks:** 2 auto + 1 checkpoint + 1 bug fix
- **Files modified:** 3

## Accomplishments

- SearchBar (162 lines) with debounced autocomplete showing artist thumbnails/genres and track albums, "Not in your library" badge for non-library tracks, "Country not mapped" for null country_id
- MapView accepts `flyToTarget` prop for programmatic fly-to navigation, clearing after animation via `moveend` event
- Full end-to-end flow: type search → see suggestions → click result → map flies to country → CountryPanel opens with country details

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SearchBar component and add flyToTarget prop to MapView** - `701dd6a` (feat)
2. **Task 2: Wire SearchBar into HomeClient with map navigation** - `ab45207` (feat)
3. **Bug fix: Stabilize flyToTarget with useCallback and moveend** - `32962aa` (fix)

## Files Created/Modified

- `frontend/src/components/SearchBar.tsx` - Debounced search with autocomplete dropdown, artist/track sections, click-outside close, "Not in your library" and "Country not mapped" handling
- `frontend/src/components/MapView.tsx` - Added flyToTarget/onFlyToComplete props, moveend-based cleanup
- `frontend/src/components/HomeClient.tsx` - handleSearchSelect with useCallback, flyToTarget state, SearchBar + updated MapView props

## Decisions Made

- Used `flyToTarget` prop pattern instead of `forwardRef` to avoid complexity with `next/dynamic` SSR-disabled imports
- `map.once('moveend')` for clearing flyToTarget — synchronous clear caused race condition where `setFlyToTarget(null)` and `setSelectedCountryId` batched unpredictably
- `useCallback` for `handleSearchSelect` and `handleFlyToComplete` — inline functions caused MapView's useEffect to re-fire every render due to changing dependency references

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CountryPanel not opening after search selection**
- **Found during:** Checkpoint verification (human-verify)
- **Issue:** Inline `onFlyToComplete` function created new reference every render, causing MapView useEffect to re-fire unpredictably. Synchronous `onFlyToComplete?.()` call triggered state clear during same render cycle as `setSelectedCountryId`, creating race condition.
- **Fix:** Wrapped callbacks in `useCallback`, used `map.once('moveend')` to defer flyToTarget clear until animation completes
- **Files modified:** HomeClient.tsx, MapView.tsx
- **Verification:** Human verified — search → fly → panel opens reliably
- **Committed in:** `32962aa`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for core search-to-navigation flow. No scope creep.

## Issues Encountered

None beyond the deviation above.

## Next Phase Readiness

- Phase 5 complete — all STAT and SRCH requirements delivered
- Ready for Phase 6 (AI Chat) — may reuse flyToTarget pattern for chat-driven map navigation

---
*Phase: 05-global-stats-and-search*
*Completed: 2026-03-25*
