---
phase: 05-global-stats-and-search
plan: 01
subsystem: ui, api
tags: [react, fastapi, sqlalchemy, pydantic, tailwind, typescript]

requires:
  - phase: 04-map-view
    provides: HomeClient.tsx, CountryPanel, onCountrySelect pattern
  - phase: 03-backend-api
    provides: /api/analytics/dashboard endpoint, /api/search endpoint, search_service.py

provides:
  - StatsSidebar component with live global analytics (country/artist/track counts, diversity score, top genre, top 5 countries)
  - DashboardStats, SearchResult, SearchArtistHit, SearchTrackHit types in api.ts
  - fetchDashboard() and fetchSearch() API client functions
  - country_id in backend search results (both artist and track hits)

affects:
  - 05-02-search-navigation (needs country_id from search hits to fly map to country)

tech-stack:
  added: []
  patterns:
    - "StatsSidebar uses useEffect + fetchDashboard() on mount (same pattern as CountryPanel)"
    - "Diversity score displayed as (raw_score * 10).toFixed(1) out of 10"
    - "Track search query LEFT JOINs Artist to get country_id (isouter=True for nullable artist_id)"

key-files:
  created:
    - frontend/src/components/StatsSidebar.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/HomeClient.tsx
    - backend/app/schemas/search.py
    - backend/app/services/search_service.py

key-decisions:
  - "Track search query uses LEFT JOIN from Track to Artist (isouter=True) to get country_id — artist_id on tracks could theoretically be null"
  - "Diversity score displayed as (diversity_score * 10).toFixed(1) — backend returns 0-1 float, sidebar shows 0-10 scale"
  - "StatsSidebar is always visible (not toggled) — fixed left panel, z-40 to stay above map"
  - "Colored progress bar for diversity: green >= 7, yellow >= 4, red < 4"

patterns-established:
  - "Phase 5 API types pattern: DashboardStats and SearchResult defined in api.ts alongside fetch functions"

duration: 2m
completed: 2026-03-25
---

# Phase 5 Plan 01: Global Stats Sidebar and Search Schema Summary

**Fixed-position stats sidebar with live library analytics (249 countries, 3,022 artists, diversity 4.9/10) plus backend search extended to return country_id on both artist and track hits**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T07:28:17Z
- **Completed:** 2026-03-25T07:30:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- StatsSidebar renders on the left side with total countries (249), artists (3,022), tracks (9,115), top genre (afrobeats), diversity score (4.9/10 with color-coded progress bar), and top 5 countries ranked by artist count — all loaded live from `/api/analytics/dashboard`
- Top 5 countries are clickable and call `onCountrySelect` prop which opens CountryPanel on the right (same selection flow as clicking map markers)
- Backend search endpoint now returns `country_id` on both artist hits (directly from `Artist.country_id`) and track hits (via `LEFT JOIN` to Artist table), unblocking Plan 05-02's map navigation on search selection
- `api.ts` exports all Phase 5 types (`DashboardStats`, `SearchResult`, `SearchArtistHit`, `SearchTrackHit`) and client functions (`fetchDashboard`, `fetchSearch`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend backend search schema and service to include country_id** - `a3d97dc` (feat)
2. **Task 2: Add frontend API types/functions and build StatsSidebar with HomeClient wiring** - `1354f78` (feat)

## Files Created/Modified

- `frontend/src/components/StatsSidebar.tsx` - Fixed left panel (143 lines): live analytics sidebar with country/artist/track counts, top genre, diversity score with colored progress bar, top 5 clickable countries
- `frontend/src/lib/api.ts` - Added DashboardStats, SearchArtistHit, SearchTrackHit, SearchResult types + fetchDashboard() and fetchSearch() functions
- `frontend/src/components/HomeClient.tsx` - Added StatsSidebar import and renders `<StatsSidebar onCountrySelect={setSelectedCountryId} />` before MapView
- `backend/app/schemas/search.py` - Added `country_id: Optional[int] = None` to SearchArtistHit (after image_url) and SearchTrackHit (after album_name)
- `backend/app/services/search_service.py` - Added `Artist.country_id` to artist_stmt select; added LEFT JOIN from Track to Artist and `Artist.country_id` to track_stmt

## Decisions Made

- Track search query uses `isouter=True` for the Artist join — defensive programming for nullable `artist_id` on tracks
- Diversity score UI: `(diversity_score * 10).toFixed(1)` converts backend's 0-1 float to 0-10 display scale; color thresholds green >= 7, yellow >= 4, red < 4
- StatsSidebar is always visible (fixed position, not toggled) per plan spec — z-40 keeps it above Mapbox canvas layer

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- STAT-01, STAT-02, STAT-03 are fully delivered
- Backend search `country_id` is ready — Plan 05-02 (search UI + map navigation) can use `country_id` from search hits to fly the map to the selected country
- `fetchSearch()` is exported and ready for the search input component in 05-02

---
*Phase: 05-global-stats-and-search*
*Completed: 2026-03-25*

## Self-Check: PASSED

- FOUND: frontend/src/components/StatsSidebar.tsx
- FOUND: frontend/src/lib/api.ts
- FOUND: backend/app/schemas/search.py
- FOUND: backend/app/services/search_service.py
- FOUND: frontend/src/components/HomeClient.tsx
- Commits found: a3d97dc (feat(05-01): extend backend search schema), 1354f78 (feat(05-01): add StatsSidebar)
