---
phase: 02-data-enrichment-pipeline
plan: 03
subsystem: pipeline
tags: [psycopg2, subprocess, python, cli, stats, orchestrator]

# Dependency graph
requires:
  - phase: 02-data-enrichment-pipeline
    plan: 01
    provides: seed_library.py and enrich_spotify.py with --env-file args
  - phase: 02-data-enrichment-pipeline
    plan: 02
    provides: enrich_musicbrainz.py with --env-file arg and mb_resolution_status column
provides:
  - run_pipeline.py: single-command pipeline orchestrator with stats logging
  - --stats-only mode: query current DB state without running pipeline steps
  - --skip-musicbrainz flag: fast run skipping 50-min MusicBrainz step
affects: [03-backend-api, Phase 2 verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [subprocess.run with check=True for step orchestration, build_sync_db_url from seed_countries.py reused for stats queries]

key-files:
  created:
    - pipeline/run_pipeline.py
  modified: []

key-decisions:
  - "run_pipeline.py calls each sub-script via subprocess.run([sys.executable, script_path, '--env-file', env_file], check=True) — each step handles its own DB connection and resume logic; orchestrator just stops on non-zero exit"
  - "--stats-only mode queries all 9 metrics from PostgreSQL and prints formatted table without running any pipeline steps — enables fast Phase 2 verification"
  - "Duration tracked with time.time() at process start — in --stats-only mode duration reflects only the stats query time, not pipeline steps"

patterns-established:
  - "Orchestrator pattern: each step runs via subprocess with env-file passthrough; halts on first failure; re-run resumes because sub-scripts are idempotent"
  - "Stats table format: fixed-width columns with percentage in parentheses, consistent with Unix tool output conventions"

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 2 Plan 3: Pipeline Orchestrator Summary

**Single-command pipeline orchestrator (run_pipeline.py) that sequences seed_countries, seed_library, enrich_spotify, and enrich_musicbrainz, then prints a formatted stats table queried from PostgreSQL**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T02:49:59Z
- **Completed:** 2026-03-25T02:52:28Z
- **Tasks:** 1
- **Files modified:** 1 (pipeline/run_pipeline.py created)

## Accomplishments
- Pipeline orchestrator runs all 4 enrichment steps in correct dependency order via subprocess
- Comprehensive stats queried from PostgreSQL after completion: total artists/tracks/user_tracks, Spotify resolution rate, genres/images coverage, MusicBrainz resolution breakdown by status, countries represented
- --stats-only flag enables fast Phase 2 verification with no API calls
- --skip-musicbrainz flag enables quick testing without the ~50-minute MusicBrainz run
- --export-path arg passed through to seed_library.py only (other scripts don't need it)

## Task Commits

Each task was committed atomically:

1. **Task 1: Pipeline orchestrator with stats logging** - `d206793` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified
- `pipeline/run_pipeline.py` - Pipeline orchestrator: runs 4 steps in sequence, halts on failure, queries DB for stats, prints formatted table

## Decisions Made
- subprocess.run with check=True used for each step — consistent with plan specification; each sub-script handles its own resume logic so orchestrator is simple
- Duration in --stats-only mode reflects only query time (not pipeline steps), which is correct — stats-only is not a pipeline run
- mb_breakdown uses .get() with defaults to safely handle any missing status values in the GROUP BY result

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 complete — all 3,022 artists seeded with Spotify metadata and MusicBrainz country resolution
- run_pipeline.py --stats-only can be used to verify final DB state at any time
- Phase 3 (Backend API) can proceed — PostgreSQL contains: 3,022 artists, 9,115 tracks, 9,115 user_tracks, 2,174 artists with country_id, 45+ countries represented
- No blockers for Phase 3

---
*Phase: 02-data-enrichment-pipeline*
*Completed: 2026-03-25*
