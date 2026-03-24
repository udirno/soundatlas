---
phase: 01-infrastructure-and-pipeline-foundation
plan: 02
subsystem: database
tags: [alembic, sqlalchemy, postgresql, migrations, seed-data, pycountry]
dependency_graph:
  requires: ["01-01"]
  provides: ["database-schema", "countries-seed-data"]
  affects: ["01-03", "02-01", "02-02", "03-01"]
tech_stack:
  added: ["alembic==1.13.3", "pycountry==24.6.1", "psycopg2-binary==2.9.9"]
  patterns: ["SQLAlchemy 2.x Mapped types", "Alembic async migration", "pg_trgm GIN indexes"]
key_files:
  created:
    - backend/app/models/country.py
    - backend/app/models/artist.py
    - backend/app/models/track.py
    - backend/app/models/user_track.py
    - backend/app/models/ai_query_log.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/versions/001_initial_schema.py
    - pipeline/requirements.txt
    - pipeline/seed_countries.py
  modified:
    - backend/app/models/__init__.py
decisions:
  - "[01-02] Alembic must run inside Docker container to avoid local PostgreSQL on port 5432 shadowing the Dockerized instance — use `docker run --network soundatlas_soundatlas_network` with `POSTGRES_HOST=postgres` for all host-side migration and seed scripts"
  - "[01-02] seed_countries.py uses POSTGRES_HOST env var override (defaulting to localhost) — set to 'postgres' when running inside Docker network"
metrics:
  duration: "7 minutes"
  completed: "2026-03-24"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 1 Plan 02: Database Schema and Seed Data Summary

**One-liner:** Alembic async migration creates all 5 PostgreSQL tables with pg_trgm GIN indexes, and pycountry seeds 249 countries with ISO alpha-2 codes and centroid coordinates.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | SQLAlchemy ORM models and Alembic async migration | 2e60425 | Complete |
| 2 | Seed countries table with pycountry data and centroid coordinates | 14e07e4 | Complete |

## What Was Built

### ORM Models (SQLAlchemy 2.x)

Five models using `Mapped` / `mapped_column` typed annotations, all importing `Base` from `app.database`:

- **Country** — `id`, `name`, `iso_alpha2` (unique), `latitude`, `longitude`, `created_at`. Relationship: `artists`.
- **Artist** — `id`, `name`, `spotify_id`, `country_id` (FK → countries), `genres` (PostgreSQL `text[]`), `popularity`, `image_url`, `mb_resolution_status` (default `'pending'`), `mb_id`, timestamps. Relationships: `country`, `tracks`.
- **Track** — `id`, `name`, `spotify_id` (unique, not null), `artist_id` (FK → artists), `album_name`, 8 nullable audio feature floats (`energy`, `danceability`, `valence`, `tempo`, `acousticness`, `instrumentalness`, `speechiness`, `liveness`), `duration_ms`, `created_at`. Relationship: `artist`.
- **UserTrack** — `id`, `track_id` (FK → tracks), `artist_id` (FK → artists), `added_at`, `created_at`.
- **AIQueryLog** — `id`, `query`, `response`, `model_name`, `token_count`, `response_time_ms`, `created_at`.

### Alembic Async Migration

- `backend/alembic/env.py` imports `Base` from `app.database` and `import app.models` to register all models. DATABASE_URL read from `settings.DATABASE_URL` (pydantic-settings) which picks up the `DATABASE_URL` environment variable.
- Manual migration `001_initial_schema.py` (not autogenerate) ensures `pg_trgm` extension is created before any indexes.
- GIN indexes: `ix_artists_name_trgm`, `ix_tracks_name_trgm` for fuzzy name search.
- Additional indexes: `ix_artists_genres_gin` (GIN on genres array), `ix_artists_mb_resolution_status` (btree for pipeline queue queries).

### Countries Seed Script

- `pipeline/seed_countries.py` iterates all 249 `pycountry.countries` entries.
- Hardcoded centroid dict covers all 193 UN member states plus common territories (Puerto Rico, Hong Kong, Aruba, etc.).
- `INSERT ... ON CONFLICT (iso_alpha2) DO NOTHING` — fully idempotent.
- Connects via `psycopg2` (sync) using `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_DB` env vars with sensible defaults.

## Verification Results

```
Tables: countries, artists, tracks, user_tracks, ai_query_log — all present
pg_trgm: enabled
Trgm indexes: ix_artists_name_trgm, ix_tracks_name_trgm — both present
Countries: 249 rows
Artists.mb_resolution_status: not null, default 'pending'
Audio feature columns: energy, danceability, valence, tempo, acousticness, instrumentalness, speechiness, liveness — all nullable float
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Local PostgreSQL on port 5432 shadows Docker instance**

- **Found during:** Task 1 (alembic upgrade head) and Task 2 (seed_countries.py)
- **Issue:** macOS host has a local PostgreSQL running on port 5432 with user `udirno` and `episcope_user`. The Docker postgres port mapping (0.0.0.0:5432 -> 5432/tcp) is shadowed — `localhost:5432` connects to the local postgres, not Docker.
- **Fix:** Ran both `alembic upgrade head` and `seed_countries.py` inside temporary Docker containers connected to `soundatlas_soundatlas_network` with `POSTGRES_HOST=postgres`. Both complete successfully.
- **Impact on future plans:** All pipeline scripts that connect to the database from host must either: (a) run inside Docker with `--network soundatlas_soundatlas_network`, or (b) use a non-conflicting port. Documented in seed_countries.py docstring.
- **Commits:** 2e60425, 14e07e4

**2. [Rule 3 - Blocking] alembic not installed in host Python environment**

- **Found during:** Task 1 setup
- **Issue:** `python3 -m alembic` failed on host miniconda Python — alembic not installed.
- **Fix:** `pip3 install alembic asyncpg sqlalchemy` on host. Then pivoted to Docker execution to avoid the port conflict.
- **Files modified:** None (host environment change only)

## Self-Check: PASSED

Files verified present:
- `/Users/udirno/Desktop/SoundAtlas/backend/app/models/country.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/backend/app/models/artist.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/backend/app/models/track.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/backend/app/models/user_track.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/backend/app/models/ai_query_log.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/backend/alembic/versions/001_initial_schema.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/pipeline/seed_countries.py` — FOUND
- `/Users/udirno/Desktop/SoundAtlas/pipeline/requirements.txt` — FOUND

Commits verified:
- `2e60425` feat(01-02): SQLAlchemy ORM models and Alembic async migration — FOUND
- `14e07e4` feat(01-02): pipeline requirements and seed_countries script — FOUND

Database verified:
- 5 application tables present (+ alembic_version)
- pg_trgm extension enabled
- 2 trgm GIN indexes present
- 249 countries seeded
