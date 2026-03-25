# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country
**Current focus:** Phase 4 COMPLETE — ready for Phase 5

## Current Position

Phase: 4 of 6 (Map View and Country Detail) — COMPLETE
Plan: 3 of 3 in phase 4 — COMPLETE
Status: Phase 4 complete — all 3 plans executed, human-verified. Ready for Phase 5 (Global Stats and Search)
Last activity: 2026-03-25 — Completed 04-03 (GenrePieChart, AudioFeatureChart, CountryPanel content, Docker/tooltip fixes)

Progress: [███████░░░] 71% (10/14 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: ~15 min
- Total execution time: ~1 hour 58 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure | 3/3 | ~60min | 20min |
| 02-data-enrichment | 3/3 | ~103min | 34min |
| 03-backend-api | 4/4 | ~26min | ~6min |
| 04-map-view | 3/3 | ~36min | ~12min |

**Recent Trend:**
- Last 5 plans: 03-04 (2min), 04-01 (~18min), 04-02 (~3min), 04-03 (~15min)
- Trend: on track

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [01-01]: DATABASE_URL overridden in docker-compose environment section to use Docker service name `postgres` not `localhost` — backend container needs container networking, .env DATABASE_URL remains localhost for host-side scripts
- [01-01]: `next.config.mjs` not `.ts` — Next.js 14 does not support TypeScript config files (added in v15)
- [01-01]: Removed docker-compose `version:` attribute (obsolete in current Docker Compose)
- [01-01]: `DeclarativeBase` (SQLAlchemy 2.x new-style) not legacy `declarative_base()` — established for all future models
- [01-01]: `expire_on_commit=False` on async_sessionmaker — required for async SQLAlchemy to prevent detached instance errors
- [01-02]: Local PostgreSQL on port 5432 shadows Docker instance — alembic migrations and pipeline seed scripts MUST run inside Docker using `--network soundatlas_soundatlas_network` with `POSTGRES_HOST=postgres`; use `docker run --rm --network soundatlas_soundatlas_network -e POSTGRES_HOST=postgres` pattern for all host-side database scripts
- [01-02]: `seed_countries.py` uses POSTGRES_HOST env var (default: localhost) — override to 'postgres' when running inside Docker network
- [Phase 1]: Verify Spotify audio features endpoint access with live API call BEFORE writing any enrichment code — endpoint was restricted Nov 2024 for new app registrations; design pipeline with nullable audio feature columns regardless of result
- [Phase 2]: Use `mb_resolution_status` column (pending/resolved/not_found/skipped) on artists table — pipeline always queries `WHERE mb_resolution_status = 'pending'`; commit each artist row individually to enable checkpoint/resume
- [Phase 4]: Use GeoJSON source + circle layer (WebGL-rendered) for map markers — never use `new mapboxgl.Marker()` for dataset-scale points (kills performance at 3,022 artists)
- [01-03]: YourLibrary.json uses flat field names `artist`, `album`, `track`, `uri` — not the `artistName`/`trackName` variants noted in pre-plan research
- [01-03]: Audio features endpoint validation writes flag file at `pipeline/.audio_features_available` — Phase 2 reads this before attempting batch fetch; 403 is handled as a valid/expected outcome
- [02-01]: Artist name is NOT unique in artists table — seed_library.py uses SELECT-before-INSERT with local dict (not ON CONFLICT) for idempotency
- [02-01]: spotify_id UNIQUE constraint: two differently-named artists can map to same Spotify ID — enrich_spotify.py handles UniqueViolation with rollback+skip, leaving second artist's spotify_id NULL
- [02-01]: 264 artists (8.7%) left with spotify_id=NULL after Spotify search — name mismatch or not on Spotify; MusicBrainz resolution (02-02) handles remaining
- [02-02]: Score threshold 80 chosen as conservative v1 default — ambiguous single-name artists (Prince, The Police) may resolve incorrectly, auditable post-launch; tightening to 90+ would significantly increase not_found count
- [02-02]: Rihanna resolved to US not Barbados — upstream MusicBrainz data issue (she is US-based in their data), not a script bug; accepted as-is for v1
- [02-02]: Do NOT derive country from MusicBrainz area field — areas can be cities/regions, not countries; only top-level country ISO alpha-2 field is used
- [02-03]: run_pipeline.py calls each sub-script via subprocess.run with check=True — orchestrator halts on first non-zero exit; re-run resumes because all sub-scripts are idempotent
- [02-03]: --stats-only mode duration reflects only the stats query time, not pipeline step time — by design (stats-only is not a pipeline run)
- [02-02]: musicbrainzngs built-in 1 req/sec rate limiting used — no manual time.sleep() added to avoid double-throttling
- [03-01]: Pydantic v2 ConfigDict(from_attributes=True) used on all ORM-backed response schemas — enables .model_validate(orm_object) without manual field mapping
- [03-01]: ArtistListItem defined in artist.py, imported by country.py for CountryDetail.artists — import order in __init__.py: artist before country
- [03-01]: Stub routers registered in main.py after CORS middleware with no endpoints — prefix stored on APIRouter not include_router(); endpoints added per-plan in Phase 3
- [03-03]: Use @router.get("") (empty string) not "/" for root endpoints on prefixed routers — "/" causes FastAPI 307 trailing-slash redirect; consistent with artists.py convention
- [03-03]: SIMILARITY_THRESHOLD = 0.15 (not pg_trgm default 0.3) — lower threshold needed for music names which are short/unusual; GIN trigram indexes on artists.name and tracks.name already created in Phase 1
- [03-02]: Use empty string "" (not "/") on @router.get() when APIRouter has a prefix — @router.get("/") causes FastAPI 307 redirect from /api/countries to /api/countries/; "" resolves correctly
- [03-02]: Two-query pattern in get_country_list — SQL aggregate for counts, second selectinload query for genre computation; cannot use Counter on aggregate result rows
- [03-02]: Artist and country service functions both live in country_service.py — shared data domain, simpler than separate files at this scale
- [03-04]: calculate_diversity_score returns 0.0 for n<=1 — avoids math.log(1)=0 division; single-country library has zero diversity by definition
- [03-04]: Genre distribution uses raw SQL text() unnest — no SQLAlchemy ORM equivalent for PostgreSQL ARRAY unnest; text().bindparams() used for safe parameterization
- [03-04]: Audio feature averages return None fields gracefully — tracks table has no audio data (Spotify endpoint restricted Nov 2024); frontend must handle null feature values
- [03-04]: AI routes have no db dependency in Phase 3 — Phase 6 will add RAG logic; schema contract established now so frontend can code against it
- [04-01]: GeoJSON circle layer used for all map markers — no mapboxgl.Marker() anywhere in source code; WebGL-rendered for performance at dataset scale
- [04-01]: Map instance stored in useRef, never useState — prevents re-render loops in React
- [04-01]: buildCircleColorExpression() built programmatically from GENRE_COLORS — adding a genre to colors.ts automatically updates the Mapbox layer
- [04-01]: page.tsx wraps fetchCountries in try/catch — map renders with empty array on build-time or backend-offline scenarios
- [04-01]: seed_countries.py uses ON CONFLICT DO UPDATE SET region=EXCLUDED.region — re-runs populate region for existing rows
- [04-01]: Alembic migration 002 must be run inside Docker: `docker compose exec backend alembic upgrade head`
- [04-02]: Access Mapbox GeoJSONFeature.properties via direct `as CountryFeatureProperties` cast — direct Feature<Point, T> cast fails TypeScript due to GeoJsonProperties type; properties-only cast is the idiomatic workaround
- [04-02]: dynamic(..., { ssr: false }) must be in a client component — moved from page.tsx (server) to HomeClient.tsx (client)
- [04-02]: CountryPanel fetches its own data (decoupled) — MapView only emits countryId via onCountrySelect; panel runs useEffect on countryId dep
- [04-03]: Pre-compute genre_color in GeoJSON properties using getGenreColor() fuzzy includes match — Mapbox match expression requires exact string equality which fails on sub-genres like "dark r&b"
- [04-03]: Exclude tempo from AudioFeatureChart radar — BPM scale (60-200) distorts vs 0-1 normalized features (energy, danceability, valence, acousticness)
- [04-03]: API_URL (non-NEXT_PUBLIC) env var for server-side Docker routing via typeof window check — NEXT_PUBLIC_API_URL is for client-side browser requests
- [04-03]: frontend/.dockerignore must exclude node_modules — without it, COPY . . overwrites container's npm install with host's (potentially stale) node_modules
- [04-03]: Tooltip CSS needs !important to override Tailwind @tailwind base reset which sets background-color: white on all elements

### Pending Todos

None.

### Blockers/Concerns

- [Phase 4]: Audio feature charts will show null/empty data — Spotify audio features endpoint was restricted for new app registrations. Frontend should handle gracefully with "data unavailable" state.
- [Phase 4]: Alembic migration 002 and seed_countries re-run must happen before region data is available in the database. Map will still render without region data (it's nullable/optional).
- [Phase 2]: MusicBrainz disambiguation accuracy on actual 3,022 artist dataset is untested. Budget time in Phase 2 for a manual audit of the first 200 resolved artists before running the full pipeline.
- [Infrastructure]: Local PostgreSQL running on port 5432 conflicts with Docker-mapped port. All pipeline scripts connecting to the database must use Docker networking (`--network soundatlas_soundatlas_network`). This affects every plan in Phase 2 that runs pipeline scripts from host.

## Session Continuity

Last session: 2026-03-25
Stopped at: Phase 4 COMPLETE — all 3 plans done, human-verified. Ready for Phase 5 (Global Stats and Search)
Resume file: .planning/phases/05-global-stats-and-search/ (when created)
