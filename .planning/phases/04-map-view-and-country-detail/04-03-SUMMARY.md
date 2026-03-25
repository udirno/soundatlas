---
phase: 04-map-view-and-country-detail
plan: 03
subsystem: frontend-ui
tags: [recharts, pie-chart, radar-chart, mapbox-popup, country-panel, tailwind]
requires:
  - phase: 04-01
    provides: MapView with GeoJSON circles, api.ts types, colors.ts palette
  - phase: 04-02
    provides: CountryPanel shell with placeholders, HomeClient state management
provides:
  - GenrePieChart with shared genre color palette
  - AudioFeatureChart radar with null-data empty state
  - Complete CountryPanel with artist list, genre chart, audio features, top tracks
  - Dark-styled Mapbox hover tooltip
  - Fuzzy genre color matching for map circles
  - Docker .dockerignore preventing host node_modules overwrite
  - Server-side API URL routing for Docker containers
affects:
  - frontend/src/components/CountryPanel.tsx (fully populated)
  - frontend/src/lib/colors.ts (expanded genre palette)
  - frontend/src/components/MapView.tsx (fuzzy genre colors)
  - frontend/src/lib/api.ts (server/client URL split)
  - docker-compose.yml (API_URL env var)
tech-stack:
  added: []
  patterns:
    - Recharts PieChart with getGenreColor for palette consistency
    - Recharts RadarChart with null-data empty state pattern
    - Pre-computed genre_color in GeoJSON properties (fuzzy match via includes)
    - Server/client API URL split using typeof window check
key-files:
  created:
    - frontend/src/components/GenrePieChart.tsx
    - frontend/src/components/AudioFeatureChart.tsx
    - frontend/.dockerignore
  modified:
    - frontend/src/components/CountryPanel.tsx
    - frontend/src/components/MapView.tsx
    - frontend/src/lib/colors.ts
    - frontend/src/lib/api.ts
    - frontend/src/app/globals.css
    - docker-compose.yml
key-decisions:
  - "Pre-compute genre_color in GeoJSON properties using getGenreColor() (fuzzy includes match) instead of Mapbox exact match expression"
  - "Exclude tempo from radar chart — BPM scale (60-200) distorts vs 0-1 normalized features"
  - "API_URL env var (non-NEXT_PUBLIC) for server-side Docker routing; NEXT_PUBLIC_API_URL for client-side"
  - "frontend/.dockerignore excludes node_modules, .next, .env.local — prevents host node_modules overwriting container npm install"
  - "Tooltip CSS uses !important to override Tailwind base reset and Mapbox defaults"
duration: ~15min
completed: 2026-03-25
---

# Phase 04 Plan 03: CountryPanel Content Summary

**Genre pie chart, audio radar with null-data handling, artist list sorted by track count, top tracks, and four infrastructure fixes (Docker, API routing, tooltip styling, genre colors)**

## Performance

- **Duration:** ~15 min (including checkpoint verification and 4 fixes)
- **Tasks:** 2 auto + 1 checkpoint (approved)
- **Files modified:** 9

## Accomplishments
- GenrePieChart renders Recharts pie with genre-colored slices matching map palette
- AudioFeatureChart renders radar or "unavailable" empty state (current default due to Spotify restriction)
- CountryPanel fully populated: artist list sorted by track_count with images/genres/badges, genre pie, audio radar, top tracks with album names
- Expanded GENRE_COLORS with 18 additional sub-genres (afrobeats, reggaeton, edm, trap, grime, etc.)
- Fixed Docker build: added .dockerignore to prevent host node_modules overwrite
- Fixed server-side API routing: getBaseUrl() uses API_URL for Docker internal, NEXT_PUBLIC_API_URL for browser
- Fixed tooltip styling: !important overrides Tailwind base reset

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | GenrePieChart and AudioFeatureChart components | 39bd049 |
| 2 | Populate CountryPanel with artist list, charts, top tracks | 0813bfd |
| fix | .dockerignore to prevent host node_modules overwrite | cddc609 |
| fix | Server-side API URL routing for Docker containers | b733c6d |
| fix | Expand genre palette and fuzzy color matching | f706bf2 |
| fix | Tooltip CSS !important for Tailwind override | 741558f |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing .dockerignore caused recharts resolution failure**
- **Found during:** Checkpoint verification
- **Issue:** No .dockerignore → COPY . . copied host node_modules into container, overwriting npm install
- **Fix:** Created frontend/.dockerignore excluding node_modules, .next, .env.local
- **Committed in:** cddc609

**2. [Rule 3 - Blocking] Server-side fetch failed inside Docker (ECONNREFUSED)**
- **Found during:** Checkpoint verification
- **Issue:** api.ts used localhost:8000 for all fetches; inside Docker, backend is at http://backend:8000
- **Fix:** getBaseUrl() checks typeof window; server uses API_URL env, client uses NEXT_PUBLIC_API_URL
- **Committed in:** b733c6d

**3. [Rule 1 - Bug] Most map circles showed fallback gray color**
- **Found during:** Checkpoint verification
- **Issue:** Mapbox match expression required exact genre match; data has sub-genres (afrobeats, dark r&b)
- **Fix:** Pre-compute genre_color via getGenreColor() (includes-based fuzzy match); expanded palette
- **Committed in:** f706bf2

**4. [Rule 1 - Bug] Tooltip showed as white rectangle**
- **Found during:** Checkpoint verification
- **Issue:** Tailwind @tailwind base resets background-color to white, overriding Mapbox popup styles
- **Fix:** Added !important to all .mapboxgl-popup-content CSS rules
- **Committed in:** 741558f

---

**Total deviations:** 4 (2 blocking, 2 bugs)
**Impact:** All fixes necessary for correct Docker deployment and visual quality. No scope creep.

## Issues Encountered
None beyond the deviations above.

## Next Phase Readiness
- Phase 4 complete — all 3 plans executed, all MAP and CTRY requirements verified
- Ready for Phase 5 (Global Stats and Search)

---
*Phase: 04-map-view-and-country-detail*
*Completed: 2026-03-25*
