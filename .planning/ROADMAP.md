# Roadmap: SoundAtlas

## Overview

SoundAtlas ships as a data-first project: an offline pipeline seeds PostgreSQL with 9,115 tracks and 3,022 artist origin countries before any user-facing code is written. From that foundation, a FastAPI backend exposes read-only REST endpoints, a Next.js frontend renders an interactive Mapbox world map with country drill-down, and a Claude-powered AI chat panel completes the platform. The six phases follow the strict data dependency chain — pipeline before backend, backend before frontend, map before chat.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Infrastructure and Pipeline Foundation** - Docker Compose environment, database schema, and Spotify export parsing with audio features validation (completed 2026-03-24)
- [ ] **Phase 2: Data Enrichment Pipeline** - Spotify API enrichment, MusicBrainz origin country resolution with checkpoint/resume, and full PostgreSQL seeding
- [ ] **Phase 3: Backend API** - FastAPI REST endpoints for countries, artists, search, and analytics
- [ ] **Phase 4: Map View and Country Detail** - Mapbox GL JS world map with GeoJSON circle layer and country drill-down panel
- [ ] **Phase 5: Global Stats and Search** - Sidebar analytics dashboard, diversity score, and pg_trgm fuzzy search with map navigation
- [ ] **Phase 6: AI Chat** - Claude-powered natural language chat panel with RAG context, Redis caching, and query logging

## Phase Details

### Phase 1: Infrastructure and Pipeline Foundation
**Goal**: The development environment runs, the database schema exists with all tables and extensions, and the Spotify export is parsed into memory — with Spotify audio features endpoint access confirmed before any enrichment code is written.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, PIPE-01, PIPE-06
**Success Criteria** (what must be TRUE):
  1. `docker compose up` starts all four services (PostgreSQL, Redis, FastAPI, Next.js) without errors
  2. PostgreSQL contains the countries, artists, tracks, user_tracks, and ai_query_log tables with pg_trgm enabled and countries seeded with world data
  3. Running the parse script against YourLibrary.json produces a count of liked tracks with Spotify IDs extracted
  4. A live test call to the Spotify audio features endpoint with actual app credentials returns either data (endpoint available) or a documented 403 result (graceful degradation path chosen)
  5. All API keys load from `.env` and no secrets appear in any committed file
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Docker Compose environment, Dockerfiles, FastAPI skeleton with async SQLAlchemy and pydantic-settings
- [x] 01-02-PLAN.md — Database schema via Alembic async migration (all tables, pg_trgm, indexes) and countries seed script
- [x] 01-03-PLAN.md — Spotify export parser module and audio features endpoint validation script

### Phase 2: Data Enrichment Pipeline
**Goal**: All 3,022 artists have origin countries resolved (or explicitly marked unresolvable), all tracks have audio features (or nullable columns if endpoint unavailable), and the pipeline is safe to re-run without creating duplicates or losing progress after interruption.
**Depends on**: Phase 1
**Requirements**: PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-07
**Success Criteria** (what must be TRUE):
  1. Running the enrichment scripts populates artists with Spotify genre tags, popularity, and image URLs for all unique artists
  2. Running the MusicBrainz script resolves origin countries for the majority of artists, with each artist row carrying a `mb_resolution_status` value (resolved/not_found/skipped) and never overwriting a resolved row on re-run
  3. If the pipeline crashes mid-run and is restarted, it resumes from where it stopped — no artist is processed twice, no progress is lost
  4. All enriched data lands in PostgreSQL via upsert with no duplicate rows after multiple pipeline runs
  5. A stats log is printed after pipeline completion showing counts of resolved artists, unresolved artists, tracks processed, and total duration
**Plans**: TBD

Plans:
- [ ] 02-01: Spotify audio features batch fetch (batches of 100 tracks) and artist metadata fetch
- [ ] 02-02: MusicBrainz origin country resolution with rate limiting, disambiguation handling, and checkpoint/resume
- [ ] 02-03: PostgreSQL upsert seeding and pipeline stats logging

### Phase 3: Backend API
**Goal**: All REST endpoints return correct data from the seeded PostgreSQL database, fuzzy search works against artists and tracks, and the backend matches HealthMap's async patterns, CORS configuration, and startup behavior.
**Depends on**: Phase 1 (infrastructure); Phase 2 (for meaningful data, but fixture data unblocks parallel development)
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09, API-10, API-11
**Success Criteria** (what must be TRUE):
  1. `GET /api/countries` returns a list of countries with artist count, track count, and top genre for each
  2. `GET /api/countries/{id}` and `GET /api/countries/{id}/comparison` return full artist lists, genre breakdown, and audio feature averages vs global averages
  3. `GET /api/search?q=` returns fuzzy-matched artists and tracks using pg_trgm, including a "Not in your library" signal for missing items
  4. `GET /api/analytics/dashboard` returns global stats including diversity score, top countries, and genre distribution
  5. `POST /api/ai/ask` and `GET /api/ai/suggestions` routes exist and return structured responses (AI integration completed in Phase 6)
**Plans**: TBD

Plans:
- [ ] 03-01: SQLAlchemy ORM models, Pydantic schemas, and FastAPI app setup (lifespan, CORS, async sessions)
- [ ] 03-02: Country and artist endpoints (API-01 through API-05)
- [ ] 03-03: Search endpoint with pg_trgm fuzzy matching (API-06)
- [ ] 03-04: Analytics endpoints and AI route stubs (API-07 through API-11)

### Phase 4: Map View and Country Detail
**Goal**: Visiting the app shows an interactive world map with country markers sized by track count and colored by genre, clicking a country opens a detail panel with artist list, genre chart, audio feature comparison, and top tracks.
**Depends on**: Phase 3
**Requirements**: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06, CTRY-01, CTRY-02, CTRY-03, CTRY-04, CTRY-05
**Success Criteria** (what must be TRUE):
  1. The app loads to a dark Mapbox world map with circle markers at country centroids; marker size is proportional to track count and visually consistent regardless of country geographic size
  2. Hovering a country circle shows a tooltip with country name, artist count, and top genre
  3. Clicking a country circle flies the map to that country and opens a right-side detail panel
  4. The detail panel shows the country name, a sorted list of artists with images and genres, and a Recharts genre pie chart
  5. The detail panel shows an audio feature comparison chart (country average vs global average for energy, danceability, valence, tempo) and a top tracks list with audio feature highlights
**Plans**: TBD

Plans:
- [ ] 04-01: Next.js app shell, Mapbox GL JS integration with GeoJSON circle layer (data-driven radius and color)
- [ ] 04-02: Map interaction — hover tooltips and click-to-fly behavior using layer-scoped event handlers
- [ ] 04-03: Country detail panel — artist list, genre pie chart, audio feature comparison (Recharts RadarChart), top tracks

### Phase 5: Global Stats and Search
**Goal**: A sidebar shows global library analytics including the diversity score and top countries, and searching for an artist or track by name navigates the map to their origin country and opens the detail panel.
**Depends on**: Phase 4
**Requirements**: STAT-01, STAT-02, STAT-03, SRCH-01, SRCH-02, SRCH-03
**Success Criteria** (what must be TRUE):
  1. A sidebar panel displays total countries represented, total unique artists, total tracks, top genre, and a geographic diversity score on a 0-10 scale
  2. The sidebar shows the top 5 countries ranked by artist count
  3. Typing in the search bar shows autocomplete suggestions against artists and tracks using fuzzy matching
  4. Selecting a search result flies the map to that artist's origin country and opens the detail panel for that country
  5. Searching for an artist or track not in the library shows a "Not in your library" message instead of navigation
**Plans**: TBD

Plans:
- [ ] 05-01: Global stats sidebar component (diversity score, country counts, genre distribution, top 5 countries)
- [ ] 05-02: Search bar with pg_trgm autocomplete and map navigation on result selection

### Phase 6: AI Chat
**Goal**: Opening the AI chat panel lets a user ask natural language questions about their listening library and receive accurate, context-aware answers drawn from PostgreSQL data, with responses cached and all queries logged.
**Depends on**: Phases 3 and 4 (requires populated data and working frontend shell)
**Requirements**: AICHAT-01, AICHAT-02, AICHAT-03, AICHAT-04, AICHAT-05
**Success Criteria** (what must be TRUE):
  1. A chat button in the header opens and closes the AI chat panel without disrupting the map view
  2. When the chat first opens, example question chips are displayed and clicking one submits the question
  3. Asking a natural language question about the library returns an accurate answer grounded in actual listening data (top countries, genre distributions, audio feature patterns)
  4. Asking the same question twice returns a response from Redis cache (no second Claude API call)
  5. Every query and response is recorded in the ai_query_log table with model name, token count, and response time
**Plans**: TBD

Plans:
- [ ] 06-01: AI chat backend — RAG context builder, Claude API integration, Redis caching, and ai_query_log table writes (POST /api/ai/ask, GET /api/ai/suggestions)
- [ ] 06-02: AI chat frontend panel — toggle open/close, suggestion chips, conversation history, streaming or batch response display

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure and Pipeline Foundation | 3/3 | Complete | 2026-03-24 |
| 2. Data Enrichment Pipeline | 0/3 | Not started | - |
| 3. Backend API | 0/4 | Not started | - |
| 4. Map View and Country Detail | 0/3 | Not started | - |
| 5. Global Stats and Search | 0/2 | Not started | - |
| 6. AI Chat | 0/2 | Not started | - |
