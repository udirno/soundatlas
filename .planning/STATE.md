# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country
**Current focus:** Phase 1 - Infrastructure and Pipeline Foundation

## Current Position

Phase: 3 of 6 (Backend API) — In progress
Plan: 3 of 6 in phase 3 complete
Status: In progress — 03-03-PLAN.md complete (fuzzy search endpoint with pg_trgm)
Last activity: 2026-03-25 — Completed 03-03-PLAN.md (GET /api/search with similarity-ranked results and in_library signal)

Progress: [████████░░] 43%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 20 min
- Total execution time: ~1 hour

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure | 3/3 | ~60min | 20min |
| 02-data-enrichment | 3/3 | ~103min | 34min |

**Recent Trend:**
- Last 5 plans: 01-02 (7min), 01-03 (25min), 02-01 (30min), 02-02 (70min), 02-03 (3min)
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
- [03-02]: Use empty string "" (not "/") on @router.get() when APIRouter has a prefix — @router.get("/") causes FastAPI 307 redirect from /api/countries to /api/countries/; "" resolves correctly
- [03-02]: Two-query pattern in get_country_list — SQL aggregate for counts, second selectinload query for genre computation; cannot use Counter on aggregate result rows
- [03-02]: Artist and country service functions both live in country_service.py — shared data domain, simpler than separate files at this scale

### Pending Todos

None.

### Blockers/Concerns

- [Phase 1]: Spotify audio features endpoint availability is LOW confidence — must be tested live before Phase 2 enrichment code is written. If 403, audio feature charts in Phase 4 will be skipped or shown as empty with explanation.
- [Phase 2]: MusicBrainz disambiguation accuracy on actual 3,022 artist dataset is untested. Budget time in Phase 2 for a manual audit of the first 200 resolved artists before running the full pipeline.
- [Infrastructure]: Local PostgreSQL running on port 5432 conflicts with Docker-mapped port. All pipeline scripts connecting to the database must use Docker networking (`--network soundatlas_soundatlas_network`). This affects every plan in Phase 2 that runs pipeline scripts from host.

## Session Continuity

Last session: 2026-03-25
Stopped at: Phase 3, Plan 2 complete — country + artist endpoints fully functional
Resume file: .planning/phases/03-backend-api/03-03-PLAN.md
