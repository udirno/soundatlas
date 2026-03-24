# Requirements: SoundAtlas

**Defined:** 2026-03-24
**Core Value:** Interactive world map that instantly reveals the geographic diversity of a music library — every artist mapped to their origin country

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: Docker Compose configuration with PostgreSQL, Redis, FastAPI backend, and Next.js frontend services matching HealthMap patterns
- [ ] **INFRA-02**: PostgreSQL database with pg_trgm extension enabled and all tables created (countries, artists, tracks, user_tracks, ai_query_log)
- [ ] **INFRA-03**: Countries table seeded with world country data (name, ISO alpha-2 code, latitude, longitude centroids)
- [ ] **INFRA-04**: Environment variable configuration via .env file (gitignored) for all API keys and service URLs
- [ ] **INFRA-05**: FastAPI backend with lifespan pattern, async SQLAlchemy session management, Redis connection, and CORS configuration matching HealthMap

### Data Pipeline

- [ ] **PIPE-01**: Parse Spotify data export (YourLibrary.json) to extract all liked tracks with Spotify track IDs and artist names
- [ ] **PIPE-02**: Fetch audio features from Spotify API for all tracks in batches of 100 (energy, danceability, valence, tempo, acousticness, instrumentalness)
- [ ] **PIPE-03**: Fetch artist metadata from Spotify API (genres, popularity, image URL) for all unique artists
- [ ] **PIPE-04**: Resolve artist origin country via MusicBrainz API with rate limiting (1 req/sec), disambiguation handling, and checkpoint/resume capability
- [ ] **PIPE-05**: Insert all enriched data into PostgreSQL with upsert logic (no duplicates on re-run)
- [ ] **PIPE-06**: Validate Spotify audio features endpoint access with test call before full pipeline run; gracefully handle unavailability
- [ ] **PIPE-07**: Log enrichment stats after pipeline completes (artists resolved, unknown countries, tracks processed, duration)

### Map View

- [ ] **MAP-01**: Mapbox GL JS world map with dark style as the landing page
- [ ] **MAP-02**: GeoJSON circle layer with country markers at centroids, sized proportionally by track count
- [ ] **MAP-03**: Circle markers colored by dominant genre using data-derived genre categories
- [ ] **MAP-04**: Hover tooltip on country circles showing country name, artist count, and top genre
- [ ] **MAP-05**: Click on country circle flies map to that country and opens the country detail panel
- [ ] **MAP-06**: Circle sizing is proportional and visually consistent regardless of country geographic size on the map

### Global Stats

- [ ] **STAT-01**: Sidebar panel showing total countries represented, total unique artists, and total tracks
- [ ] **STAT-02**: Display top genre overall and geographic diversity score (Shannon entropy normalized to 0-10)
- [ ] **STAT-03**: Top 5 countries ranked by artist count in the sidebar

### Search

- [ ] **SRCH-01**: Search bar in header with autocomplete against artists and tracks using pg_trgm fuzzy search
- [ ] **SRCH-02**: Selecting a search result flies the map to that artist's origin country and opens the detail panel
- [ ] **SRCH-03**: If an artist/track is not in the user's library, display "Not in your library"

### Country Detail

- [ ] **CTRY-01**: Right panel opens on country click showing country name and region label
- [ ] **CTRY-02**: List of all artists from the country sorted by track count, showing artist image and genres
- [ ] **CTRY-03**: Genre breakdown pie chart using Recharts
- [ ] **CTRY-04**: Audio feature comparison chart — country average vs global average for energy, danceability, valence, tempo (Recharts bar or radar chart)
- [ ] **CTRY-05**: Top tracks list from this country with track name, album, and audio feature highlights

### AI Chat

- [ ] **AICHAT-01**: Toggle-open chat panel from header button matching HealthMap's AIChatPanel component pattern
- [ ] **AICHAT-02**: Backend RAG — fetch user's listening stats, country breakdowns, and audio feature data from PostgreSQL, inject as structured context into Claude API prompt
- [ ] **AICHAT-03**: Suggestion chips shown when chat is first opened with example questions
- [ ] **AICHAT-04**: AI responses cached in Redis with same caching pattern as HealthMap
- [ ] **AICHAT-05**: All queries logged to ai_query_log table (query text, response, model, tokens, response time)

### Backend API

- [ ] **API-01**: GET /api/countries — list all countries with artist count, track count, top genre
- [ ] **API-02**: GET /api/countries/{id} — country detail with artists, genres, audio feature averages
- [ ] **API-03**: GET /api/countries/{id}/comparison — country audio features vs global averages
- [ ] **API-04**: GET /api/artists — list all artists, supports search via ?q= parameter
- [ ] **API-05**: GET /api/artists/{id} — artist detail with tracks and audio features
- [ ] **API-06**: GET /api/search?q= — fuzzy search across artists and tracks using pg_trgm
- [ ] **API-07**: GET /api/analytics/dashboard — global stats (country count, track count, diversity score, top genres, top countries)
- [ ] **API-08**: GET /api/analytics/genres — genre distribution globally and per country
- [ ] **API-09**: GET /api/analytics/features — audio feature averages globally and per country
- [ ] **API-10**: POST /api/ai/ask — natural language question with RAG context from PostgreSQL
- [ ] **API-11**: GET /api/ai/suggestions — pre-built question suggestions

## v2 Requirements

### Data Pipeline Enhancements

- **PIPE-V2-01**: Re-sync capability to pick up newly liked songs without duplicating existing data
- **PIPE-V2-02**: Streaming history integration for play count weighting on the map

### Lyric Search

- **LYRIC-01**: Search bar querying ChromaDB embeddings from existing LyricLens dataset (3,400 songs)
- **LYRIC-02**: Return top 5 semantically similar songs with similarity scores

### Analytics Enhancements

- **ANLYT-01**: Language distribution per country
- **ANLYT-02**: Timeline view showing when tracks from each country were added to library
- **ANLYT-03**: Continent-level aggregation and comparison

### Social

- **SOCL-01**: Shareable diversity score card (image export)
- **SOCL-02**: Compare your map with another user's

## Out of Scope

| Feature | Reason |
|---------|--------|
| Spotify OAuth login flow | App ships pre-loaded with personal data, no user authentication needed |
| Live/automatic Spotify sync | Manual re-run only; keeps complexity low |
| Multi-user support | Single-user personal tool |
| Mobile app | Web-first |
| Real-time streaming history | Library (liked songs) only — cleaner signal |
| Recommendation engine | AI chat can suggest, but no algorithmic recommendation system |
| Audio playback | Would require Spotify Premium SDK and adds complexity |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |
| INFRA-05 | Phase 1 | Pending |
| PIPE-01 | Phase 1 | Pending |
| PIPE-06 | Phase 1 | Pending |
| PIPE-02 | Phase 2 | Pending |
| PIPE-03 | Phase 2 | Pending |
| PIPE-04 | Phase 2 | Pending |
| PIPE-05 | Phase 2 | Pending |
| PIPE-07 | Phase 2 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 3 | Pending |
| API-05 | Phase 3 | Pending |
| API-06 | Phase 3 | Pending |
| API-07 | Phase 3 | Pending |
| API-08 | Phase 3 | Pending |
| API-09 | Phase 3 | Pending |
| API-10 | Phase 3 | Pending |
| API-11 | Phase 3 | Pending |
| MAP-01 | Phase 4 | Pending |
| MAP-02 | Phase 4 | Pending |
| MAP-03 | Phase 4 | Pending |
| MAP-04 | Phase 4 | Pending |
| MAP-05 | Phase 4 | Pending |
| MAP-06 | Phase 4 | Pending |
| CTRY-01 | Phase 4 | Pending |
| CTRY-02 | Phase 4 | Pending |
| CTRY-03 | Phase 4 | Pending |
| CTRY-04 | Phase 4 | Pending |
| CTRY-05 | Phase 4 | Pending |
| STAT-01 | Phase 5 | Pending |
| STAT-02 | Phase 5 | Pending |
| STAT-03 | Phase 5 | Pending |
| SRCH-01 | Phase 5 | Pending |
| SRCH-02 | Phase 5 | Pending |
| SRCH-03 | Phase 5 | Pending |
| AICHAT-01 | Phase 6 | Pending |
| AICHAT-02 | Phase 6 | Pending |
| AICHAT-03 | Phase 6 | Pending |
| AICHAT-04 | Phase 6 | Pending |
| AICHAT-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after roadmap creation*
