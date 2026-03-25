---
phase: 04-map-view-and-country-detail
plan: 01
subsystem: frontend-map + backend-schemas
tags: [mapbox, geojson, circle-layer, next.js, typescript, pydantic, alembic]
requires:
  - 03-01 (Pydantic schemas for CountryListItem, ArtistListItem)
  - 03-02 (country_service.py with get_country_list and get_country_detail)
provides:
  - Full-screen Mapbox map with GeoJSON circle layer rendering country markers
  - Backend CountryDetail with region, track_count per artist, top_tracks
  - Typed TypeScript API client mirroring all backend schemas
  - Shared genre color palette used by map and future chart components
affects:
  - frontend/src/app/page.tsx (rewritten as async server component)
  - backend/app/schemas/country.py (region, top_tracks added)
  - backend/app/schemas/artist.py (track_count added)
  - backend/app/services/country_service.py (region in query, track_count computed)
tech-stack:
  added:
    - mapbox-gl@3.20.0
    - recharts@3.8.0
    - @types/mapbox-gl
  patterns:
    - GeoJSON source + circle layer (WebGL-rendered, never mapboxgl.Marker)
    - useRef for Mapbox map instance (never useState)
    - Next.js dynamic import with ssr:false for client-only map component
    - Async server component for server-side data fetch passed to client component
key-files:
  created:
    - frontend/src/components/MapView.tsx
    - frontend/src/lib/api.ts
    - frontend/src/lib/colors.ts
    - backend/alembic/versions/002_add_region_and_top_tracks.py
    - USER-SETUP.md
  modified:
    - frontend/src/app/page.tsx
    - backend/app/models/country.py
    - backend/app/schemas/country.py
    - backend/app/schemas/artist.py
    - backend/app/services/country_service.py
    - pipeline/seed_countries.py
key-decisions:
  - GeoJSON circle layer used for all map markers — no mapboxgl.Marker() anywhere in source
  - Map instance stored in useRef, never useState — prevents re-render loops
  - buildCircleColorExpression() built programmatically from GENRE_COLORS — adding a genre to colors.ts auto-updates the map layer
  - page.tsx uses try/catch around fetchCountries — map renders with empty array rather than crashing during build or when backend is offline
  - seed_countries.py uses ON CONFLICT DO UPDATE SET region=EXCLUDED.region — re-running seed populates region for existing country rows
  - Alembic migration 002 must be run inside Docker: docker compose exec backend alembic upgrade head
duration: ~18 minutes
completed: 2026-03-24
---

# Phase 04 Plan 01: Map View and Country Detail Foundation Summary

**One-liner:** Mapbox dark map with sqrt-scaled, genre-colored GeoJSON circles backed by a typed Next.js API client, plus backend region/track_count/top_tracks schema extensions.

## Accomplishments

- Backend Country model and Alembic migration 002 add `region` column (nullable String(50))
- `seed_countries.py` extended with `COUNTRY_REGIONS` dict covering all UN member states — uses `DO UPDATE SET region=EXCLUDED.region` so re-runs populate region for existing rows
- `ArtistListItem` schema now includes `track_count: int = 0` (computed in service layer)
- `CountryDetail` schema now includes `region` and `top_tracks: list[TrackListItem]`
- `CountryListItem` schema now includes `region`
- `get_country_list` SQL query includes `Country.region` in SELECT and GROUP BY
- `get_country_detail` computes `artist.track_count = len(artist.tracks)` and collects top 10 tracks sorted by artist track count
- `frontend/src/lib/api.ts` exports fully typed interfaces + fetch helpers for all 3 country endpoints
- `frontend/src/lib/colors.ts` exports `GENRE_COLORS`, `getGenreColor`, and `buildMapboxColorExpression`
- `MapView.tsx` renders full-screen dark Mapbox map with GeoJSON circle layer: radius via sqrt interpolation, color via genre match expression
- `page.tsx` rewritten as async server component — fetches countries server-side, renders MapView via `dynamic(..., { ssr: false })`
- `npm run build` passes — page marked as Dynamic (`ƒ`) as expected

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Backend: region column, track_count, top_tracks | db49aa9 |
| 2 | Frontend: install deps, create api.ts and colors.ts | edffa9c |
| 3 | Frontend: MapView component and page.tsx | 18f044a |

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/MapView.tsx` | 'use client' Mapbox map, GeoJSON source, circle layer |
| `frontend/src/lib/api.ts` | Typed fetch helpers and TypeScript interfaces |
| `frontend/src/lib/colors.ts` | Shared genre color palette, buildMapboxColorExpression |
| `frontend/src/app/page.tsx` | Async server component, dynamic MapView import |
| `backend/alembic/versions/002_add_region_and_top_tracks.py` | Alembic migration: adds region column |
| `pipeline/seed_countries.py` | COUNTRY_REGIONS dict, DO UPDATE on region |

## Deviations from Plan

None — plan executed exactly as written.

## Issues / Blockers

- **Alembic migration 002 not yet applied to database** — must be run inside Docker: `docker compose exec backend alembic upgrade head`. This is expected (database operations always run inside Docker per project decision [01-02]).
- **Mapbox token not set** — USER-SETUP.md generated with instructions. Map will not render until `NEXT_PUBLIC_MAPBOX_TOKEN` is set in `frontend/.env.local`.
- **Backend offline during `npm run build`** — expected; try/catch in page.tsx ensures graceful fallback (empty array passed to MapView).

## Next Phase Readiness

- Phase 4 Plan 02 (Country Detail panel) can now import `CountryDetail` and `fetchCountryDetail` from `@/lib/api`
- `top_tracks` and `region` are available on `CountryDetail` for CTRY-01, CTRY-02, CTRY-05
- `getGenreColor` from `colors.ts` is available for chart components in Plan 02+
- MapView's `onCountrySelect` prop is wired and ready to receive a handler from a parent layout

## Self-Check

## Self-Check: PASSED

All 7 key files found. All 3 task commits found (db49aa9, edffa9c, 18f044a).
