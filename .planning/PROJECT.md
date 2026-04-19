# SoundAtlas

## What This Is

A personal music intelligence platform that maps a Spotify library geographically. Visitors see an interactive world map showing where every artist in the library originates — each artist pinned to their country of origin, with circle markers sized by track count and colored by dominant genre. Clicking any country opens a detail panel with artist lists, genre pie charts, audio feature comparisons, and top tracks. A global analytics sidebar shows diversity score, top countries, and genre distribution. A search bar with fuzzy autocomplete navigates the map by artist or track name. A Claude-powered AI chat panel answers natural language questions about listening patterns using RAG context from PostgreSQL.

The app ships pre-loaded with data from a personal Spotify export (9,115 tracks, 3,022 artists, 3,022 origin countries resolved). No login required — visitors see the map immediately.

## Core Value

The interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country with meaningful visual encoding (size = track count, color = dominant genre).

## Requirements

### Validated

- [x] Interactive Mapbox world map with country markers sized by track count and colored by dominant genre — v1.0
- [x] Country detail panel with artist list, genre breakdown, audio feature comparison, and top tracks — v1.0
- [x] AI chat panel using Claude API with RAG context from PostgreSQL listening data — v1.0
- [x] Data pipeline seeding from Spotify data export + API enrichment (audio features, artist metadata, MusicBrainz origin countries) — v1.0
- [x] Fuzzy search across artists and tracks using pg_trgm — v1.0
- [x] Global analytics dashboard (diversity score, top countries, genre distribution) — v1.0
- [x] Docker Compose local development matching HealthMap patterns — v1.0

### Active

- [ ] Audio features section conditionally shown (visible when data exists, hidden when unavailable)
- [ ] Diversity score redesigned with meaningful context and friendlier presentation
- [ ] AI chat panel expandable/fullscreen mode for better readability
- [ ] Production deployment (frontend on Vercel, backend + DB on Railway)

### Deferred (v2.0+)

- [ ] Spotify OAuth login — let anyone connect and generate their own map
- [ ] Multi-user support with persistent accounts and per-user data isolation
- [ ] Manual re-sync capability to update with new liked songs

### Out of Scope

- Spotify OAuth login flow — app ships pre-loaded with personal data, no user authentication
- Live/automatic sync with Spotify — manual re-run only for now
- Real-time streaming history integration — library (liked songs) only
- Mobile app — web-first
- Lyric search tab (ChromaDB/LyricLens) — P2 priority, deferred unless time allows
- Multi-user support — deferred to v2.0, polish and deploy single-user first

## Context

### Codebase State (v1.0)

- **Backend:** `backend/app/` — FastAPI with async SQLAlchemy, 11 REST endpoints, AI service with Claude + Redis caching
- **Frontend:** `frontend/src/` — Next.js 14, Mapbox GL JS map, CountryPanel, StatsSidebar, SearchBar, AIChatPanel
- **Pipeline:** `pipeline/` — parse_library.py, seed_library.py, enrich_spotify.py, enrich_musicbrainz.py, run_pipeline.py
- **Database:** PostgreSQL with pg_trgm, tables: countries, artists, tracks, user_tracks, ai_query_log
- **Infrastructure:** Docker Compose (postgres, redis, backend, frontend), Alembic migrations

### Data Profile
- **Source:** Spotify data export at `~/Downloads/Spotify Account Data/`
- **Library:** 9,115 liked tracks, 3,022 unique artists
- **Track URIs:** Available in `YourLibrary.json`, contain Spotify IDs for API enrichment
- **Streaming history:** 104,585 plays available but out of scope for v1 (library-only for clean signal)

### Data Pipeline Strategy
- **Hybrid approach:** Use data export for track/artist lists, Spotify API only for audio features (energy, danceability, valence, tempo, acousticness, instrumentalness) and artist metadata (genres, popularity, images)
- **MusicBrainz:** Origin country lookup per unique artist, rate-limited at 1 req/sec (~50 minutes for 3,022 artists)
- **Unknown origins:** Artists without resolved countries shown in sidebar only, not on map
- **Genre bucketing:** Derive macro genre categories from actual Spotify genre tags in the dataset, not predefined

### Reference Codebase
- **HealthMap** at `~/Desktop/HealthMap` — follow its file structure, component patterns, FastAPI setup, async SQLAlchemy, Redis caching, Docker Compose, and React/Next.js patterns exactly
- Already mapped via `/gsd:map-codebase`

### Product Decisions
- App ships pre-loaded — no login, no onboarding, visitors see the map immediately
- Artist country = origin country from MusicBrainz (where artist is FROM, not current residence)
  - Rihanna = Barbados (note: MusicBrainz resolved to US — accepted as-is for v1), Drake = Canada, 21 Savage = UK
- Geographic diversity score uses Shannon entropy normalized to 0-10 scale

## Constraints

- **Tech stack:** Must match HealthMap exactly — FastAPI, async SQLAlchemy, PostgreSQL, Redis, Claude API, Next.js 14, Mapbox GL JS, TailwindCSS, Recharts, Docker Compose
- **Security:** No API keys or secrets in committed code — all secrets in `.env` (gitignored)
- **API rate limits:** MusicBrainz at 1 req/sec; Spotify audio features at 100 per batch
- **Data scale:** ~9K tracks, ~3K artists — must handle efficiently but not at massive scale
- **Deployment:** Frontend on Vercel, Backend + PostgreSQL + Redis on Railway; local dev via Docker Compose
- **Repository:** https://github.com/udirno/soundatlas.git
- **Clonability:** Repo must be easy for anyone to clone, configure `.env`, and run locally

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Library-only data (not streaming history) | Liked songs = deliberate curation, cleaner signal than 104K noisy play events | Good |
| Export + API hybrid pipeline | Data export provides track/artist lists; API only needed for audio features and metadata. Faster, fewer API calls | Good |
| Derive genre categories from data | Let Spotify's genre tags cluster naturally rather than imposing predefined buckets | Good |
| Unknown artists in sidebar only | Keeps map clean while preserving data visibility | Good |
| Manual re-sync (no live sync) | Simplest path; keeps auth complexity low; easy to add later | Good |
| MusicBrainz origin country (not residence) | Makes map more geographically interesting and accurate to cultural roots | Good |
| GeoJSON circle layer (not Mapbox Markers) | WebGL-rendered for performance at 3,022 marker scale | Good |
| Audio features graceful degradation | Endpoint restricted Nov 2024; nullable columns designed in from Phase 1 | Good |
| mb_resolution_status checkpoint/resume | Enables safe pipeline restarts without re-processing resolved artists | Good |
| AsyncAnthropic client | Backend fully async; sync client would block the event loop | Good |

---
## Current Milestone: v1.1 Polish & Deploy

**Goal:** Fix UX rough edges (audio features, diversity score, chat panel) and deploy to production so friends can view the map.

**Target features:**
- Conditional audio features display (show when available, hide when not)
- Redesigned diversity score with meaningful context
- Expandable AI chat panel
- Production deployment (Vercel + Railway)

---
*Last updated: 2026-04-18 after v1.1 milestone start*
