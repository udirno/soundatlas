---
phase: 02-data-enrichment-pipeline
plan: "01"
subsystem: pipeline
tags: [seeding, spotify-api, artists, tracks, enrichment]
dependency_graph:
  requires:
    - "01-03: parse_library.py (parse_liked_tracks function)"
    - "01-02: PostgreSQL schema (artists, tracks, user_tracks tables)"
  provides:
    - "3,022 artist rows in artists table (spotify_id populated for 91.3%)"
    - "9,115 track rows in tracks table with artist_id FK"
    - "9,115 user_track rows"
    - "genres, popularity, image_url populated for 2,758 artists"
  affects:
    - "02-02: MusicBrainz resolution reads artists WHERE mb_resolution_status='pending'"
    - "Phase 4: genre and popularity data available for map visualization"
tech_stack:
  added: []
  patterns:
    - "psycopg2 sync with manual conn/cursor (no ORM) for pipeline scripts"
    - "ON CONFLICT (spotify_id) DO NOTHING for idempotent track inserts"
    - "Existence check (SELECT before INSERT) for artists (name not unique)"
    - "Per-row commit in ID resolution loop (checkpoint/resume pattern)"
    - "Per-batch commit in metadata fetch (batches of 50 via sp.artists())"
key_files:
  created:
    - pipeline/seed_library.py
    - pipeline/enrich_spotify.py
  modified: []
decisions:
  - "Artist name is NOT unique in the schema — idempotency uses SELECT-before-INSERT with local dict, not ON CONFLICT"
  - "spotify_id UNIQUE constraint causes UniqueViolation when two differently-named artists map to same Spotify artist — handled with try/except + rollback (Rule 1 bug fix)"
  - "264 artists with spotify_id NULL after enrichment — name mismatch or absent from Spotify; MusicBrainz step handles remaining resolution"
  - "enrich_spotify.py is resumable mid-run — ID resolution commits per-row, metadata fetch commits per-batch"
metrics:
  duration: "~30 minutes (mostly Spotify API calls)"
  completed: "2026-03-25"
---

# Phase 2 Plan 01: Library Seeder and Spotify Enrichment Summary

Seeds the full Spotify library into PostgreSQL and enriches artist rows with Spotify metadata: genres, popularity, and image_url for 2,758 of 3,022 artists (91.3%) using batched sp.artists() calls.

## What Was Built

### pipeline/seed_library.py

Parses YourLibrary.json via `parse_liked_tracks()` and seeds three tables in one pass:

- **artists**: 3,022 unique artists inserted with `name` only. `spotify_id` left NULL (resolved by `enrich_spotify.py`). Idempotent via SELECT-before-INSERT with local dict mapping artist_name -> artist_id.
- **tracks**: 9,115 tracks inserted with `ON CONFLICT (spotify_id) DO NOTHING`. Batched in groups of 500.
- **user_tracks**: 9,115 rows inserted with existence check against a local set (no unique constraint on the table).

CLI flags: `--env-file`, `--export-path`. Uses same `build_sync_db_url()` / psycopg2 pattern as `seed_countries.py`.

### pipeline/enrich_spotify.py

Two-phase artist enrichment:

1. **ID resolution**: For each artist with `spotify_id IS NULL`, calls `sp.search(q=name, type='artist', limit=1)`. Compares normalized names (NFKD, lowercase, stripped). Commits per-row so the script is resumable. Logs every 100 artists.

2. **Metadata batch fetch**: For each artist with `spotify_id IS NOT NULL AND genres IS NULL`, batches 50 spotify_ids per `sp.artists()` call. Extracts `genres` (list, psycopg2 passes Python list directly to PostgreSQL `text[]`), `popularity` (int), `image_url` (first image URL or NULL). Commits per-batch.

Reads `pipeline/.audio_features_available` flag at startup. Logs "Audio features unavailable" when `AUDIO_FEATURES_AVAILABLE=false` and skips all audio feature API calls.

## Results

| Metric | Value |
|--------|-------|
| Total artists | 3,022 |
| Artists with spotify_id | 2,758 (91.3%) |
| Artists with genres | 2,758 |
| Artists with image_url | 2,749 |
| Artists with empty genres list | 1,120 (valid — many artists have no genres on Spotify) |
| Artists where lookup skipped | 264 (name mismatch or absent from Spotify) |
| Total tracks | 9,115 |
| Total user_tracks | 9,115 |
| All artists mb_resolution_status | 'pending' (MusicBrainz is 02-02) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UniqueViolation when two artists map to the same Spotify artist ID**

- **Found during:** Task 2 (enrich_spotify.py) — first run at artist #800 approx
- **Issue:** Two differently-named artists in the library (e.g., variations/duplicates) both matched the same Spotify artist via `sp.search()`. The second UPDATE triggered `unique constraint "artists_spotify_id_key"` violation.
- **Fix:** Wrapped the UPDATE in try/except `psycopg2.errors.UniqueViolation`. On violation, rolls back the failed statement and counts the artist as skipped (spotify_id stays NULL). The script resumed from where it left off on next run.
- **Files modified:** `pipeline/enrich_spotify.py`
- **Commit:** 9baffe6

## Self-Check: PASSED

- pipeline/seed_library.py: FOUND
- pipeline/enrich_spotify.py: FOUND
- Commit 117c31d (feat(02-01): seed artists and tracks): FOUND
- Commit 9baffe6 (feat(02-01): enrich artists with Spotify API metadata): FOUND
