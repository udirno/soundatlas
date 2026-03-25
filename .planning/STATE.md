# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country
**Current focus:** Phase 1 - Infrastructure and Pipeline Foundation

## Current Position

Phase: 2 of 6 (Data Enrichment Pipeline) — In progress
Plan: 1 of 3 in phase 2
Status: In progress — Plan 02-01 complete, ready for 02-02 (MusicBrainz country resolution)
Last activity: 2026-03-25 — Completed 02-01-PLAN.md (library seeder + Spotify metadata enrichment)

Progress: [████░░░░░░] 24%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 20 min
- Total execution time: ~1 hour

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure | 3/3 | ~60min | 20min |
| 02-data-enrichment | 1/3 | ~30min | 30min |

**Recent Trend:**
- Last 5 plans: 01-01 (30min), 01-02 (7min), 01-03 (25min), 02-01 (30min)
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

### Pending Todos

None.

### Blockers/Concerns

- [Phase 1]: Spotify audio features endpoint availability is LOW confidence — must be tested live before Phase 2 enrichment code is written. If 403, audio feature charts in Phase 4 will be skipped or shown as empty with explanation.
- [Phase 2]: MusicBrainz disambiguation accuracy on actual 3,022 artist dataset is untested. Budget time in Phase 2 for a manual audit of the first 200 resolved artists before running the full pipeline.
- [Infrastructure]: Local PostgreSQL running on port 5432 conflicts with Docker-mapped port. All pipeline scripts connecting to the database must use Docker networking (`--network soundatlas_soundatlas_network`). This affects every plan in Phase 2 that runs pipeline scripts from host.

## Session Continuity

Last session: 2026-03-25
Stopped at: Phase 2, Plan 1 complete — ready for 02-02 (MusicBrainz country resolution)
Resume file: .planning/phases/02-data-enrichment-pipeline/02-02-PLAN.md
