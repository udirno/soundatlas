# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country
**Current focus:** Phase 1 - Infrastructure and Pipeline Foundation

## Current Position

Phase: 1 of 6 (Infrastructure and Pipeline Foundation)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-03-24 — Completed 01-02-PLAN.md (Alembic migrations + DB schema + countries seed)

Progress: [██░░░░░░░░] 12%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 19 min
- Total execution time: 0.6 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure | 2/3 | 37min | 19min |

**Recent Trend:**
- Last 5 plans: 01-01 (30min), 01-02 (7min)
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

### Pending Todos

None.

### Blockers/Concerns

- [Phase 1]: Spotify audio features endpoint availability is LOW confidence — must be tested live before Phase 2 enrichment code is written. If 403, audio feature charts in Phase 4 will be skipped or shown as empty with explanation.
- [Phase 2]: MusicBrainz disambiguation accuracy on actual 3,022 artist dataset is untested. Budget time in Phase 2 for a manual audit of the first 200 resolved artists before running the full pipeline.
- [Infrastructure]: Local PostgreSQL running on port 5432 conflicts with Docker-mapped port. All pipeline scripts connecting to the database must use Docker networking (`--network soundatlas_soundatlas_network`). This affects every plan in Phase 2 that runs pipeline scripts from host.

## Session Continuity

Last session: 2026-03-24
Stopped at: 01-02-PLAN.md complete — ready for 01-03 (pipeline scripts: Spotify library import)
Resume file: .planning/phases/01-infrastructure-and-pipeline-foundation/01-03-PLAN.md
