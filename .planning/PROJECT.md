# SoundAtlas

## What This Is

A personal music intelligence platform that maps Spotify listening data geographically. Users visit the site and immediately see an interactive world map showing where the music in the library originates — every artist pinned to their country of origin, with rich analytics, audio feature breakdowns, and an AI chat interface for natural language exploration of listening patterns.

## Core Value

The interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country with meaningful visual encoding (size = track count, color = dominant genre).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Interactive Mapbox world map with country markers sized by track count and colored by dominant genre
- [ ] Country detail panel with artist list, genre breakdown, audio feature comparison, and top tracks
- [ ] AI chat panel using Claude API with RAG context from PostgreSQL listening data
- [ ] Data pipeline seeding from Spotify data export + API enrichment (audio features, artist metadata, MusicBrainz origin countries)
- [ ] Fuzzy search across artists and tracks using pg_trgm
- [ ] Global analytics dashboard (diversity score, top countries, genre distribution)
- [ ] Manual re-sync capability to update with new liked songs
- [ ] Docker Compose local development matching HealthMap patterns

### Out of Scope

- Spotify OAuth login flow — app ships pre-loaded with personal data, no user authentication
- Live/automatic sync with Spotify — manual re-run only for now
- Real-time streaming history integration — library (liked songs) only
- Mobile app — web-first
- Lyric search tab (ChromaDB/LyricLens) — P2 priority, deferred unless time allows
- Multi-user support — single-user personal tool

## Context

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
  - Rihanna = Barbados, Drake = Canada, 21 Savage = UK
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
| Library-only data (not streaming history) | Liked songs = deliberate curation, cleaner signal than 104K noisy play events | — Pending |
| Export + API hybrid pipeline | Data export provides track/artist lists; API only needed for audio features and metadata. Faster, fewer API calls | — Pending |
| Derive genre categories from data | Let Spotify's genre tags cluster naturally rather than imposing predefined buckets | — Pending |
| Unknown artists in sidebar only | Keeps map clean while preserving data visibility | — Pending |
| Manual re-sync (no live sync) | Simplest path; keeps auth complexity low; easy to add later | — Pending |
| MusicBrainz origin country (not residence) | Makes map more geographically interesting and accurate to cultural roots | — Pending |

---
*Last updated: 2026-03-24 after initialization*
