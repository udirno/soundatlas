# Project Research Summary

**Project:** SoundAtlas
**Domain:** Personal music intelligence platform with geographic visualization
**Researched:** 2026-03-24
**Confidence:** HIGH (stack and architecture); MEDIUM (features and pitfall edge cases)

## Executive Summary

SoundAtlas is a personal music intelligence platform that maps 9,115 liked Spotify tracks to artist origin countries, enabling geographic exploration of musical taste. The product occupies an uncontested niche: no existing tool (Spotify Wrapped, Last.fm, Stats for Spotify) answers "where in the world does my music come from?" using artist cultural roots rather than streaming location. The recommended approach is a four-layer system — an offline data pipeline seeding PostgreSQL, a FastAPI backend, a Next.js frontend with Mapbox GL JS, and a Claude-powered AI chat panel — modeled directly on the HealthMap reference codebase to minimize architectural decisions and maximize pattern reuse.

The recommended build order is pipeline-first, then backend API, then frontend map, then AI chat. This order is forced by data dependencies: the MusicBrainz enrichment pipeline (50+ minutes at 1 req/sec for 3,022 artists) must complete before the backend can serve meaningful data, and the backend must exist before the frontend is testable with real content. A small fixture dataset (50 tracks) should be seeded early to unblock parallel development. The two highest-value differentiators — geographic origin mapping and AI natural language exploration — require the most infrastructure investment but face no direct competition.

The single highest-risk external dependency is Spotify's `GET /v1/audio-features` endpoint, which was restricted for new app registrations in November 2024. This must be verified against live API credentials before any enrichment code is written. The second major risk is MusicBrainz artist disambiguation: naive name matching silently assigns wrong countries to artists. Both risks have clear mitigations documented in PITFALLS.md and should be addressed in Phase 1 before the full pipeline runs.

---

## Key Findings

### Recommended Stack

The stack is constrained to match HealthMap (the reference codebase), which provides high confidence in version compatibility. Backend uses Python 3.11, FastAPI 0.115.x, SQLAlchemy 2.0.x with async PostgreSQL via asyncpg, and pydantic v2. The data pipeline adds spotipy 2.26.0 for Spotify API access, musicbrainzngs 0.7.1 for MusicBrainz lookups, and tenacity 9.1.4 for retry logic. Frontend uses Next.js 16.2.0 with App Router, mapbox-gl 3.16.0 (do not upgrade — exact HealthMap version), and recharts 3.4.1 for audio feature charts. Deployment targets Vercel (frontend) and Railway (backend + PostgreSQL + Redis).

**Core technologies:**
- Python 3.11 + FastAPI 0.115.x: HTTP API layer — matches HealthMap exactly; async-native with pydantic v2
- PostgreSQL 15 + PostGIS 3.3: primary data store — country coordinates, track/artist/genre data
- spotipy 2.26.0: Spotify Web API client — handles Client Credentials auth, batch audio features, artist enrichment
- musicbrainzngs 0.7.1: MusicBrainz artist origin lookup — only maintained Python client; handles XML + rate limiting
- tenacity 9.1.4: retry with exponential backoff — critical for MusicBrainz 1 req/sec limit and 503 errors
- mapbox-gl 3.16.0: map rendering — GeoJSON circle layer with data-driven radius/color by track count and genre
- recharts 3.4.1: audio feature radar/bar charts — exact HealthMap version; RadarChart for per-country comparisons
- anthropic 0.86.0: Claude API client — RAG chat panel; Redis-cached AI responses

**Critical version note:** mapbox-gl must stay at 3.16.0 to match HealthMap. Audio features require Spotify endpoint access verification — test before building the pipeline.

### Expected Features

No competitor provides geographic artist-origin mapping. SoundAtlas must ship the core map + AI chat to claim its niche. Audio features are valuable but secondary and may be unavailable depending on Spotify app registration date.

**Must have (table stakes):**
- Interactive Mapbox world map with sized + colored country markers — core screen; its absence makes the product nonfunctional
- Country click to detail panel (artist list, genre chart, top tracks, audio feature charts) — users expect drilldown from any map interaction
- Global stats sidebar (diversity score, top countries, genre distribution, total artist/track counts) — orientation before drilling down
- Fuzzy search by artist name (pg_trgm) — users look for specific artists; no search creates frustration
- Data pipeline seeding ~3,022 artists with origin countries — upstream dependency for everything else

**Should have (differentiators):**
- AI chat panel with RAG (Claude API) — the feature no competitor has; elevates platform from "pretty map" to "music intelligence"
- Geographic diversity score (Shannon entropy, displayed prominently) — single most quotable output; uniquely SoundAtlas
- Audio feature comparison by country (energy/danceability/valence/tempo) — genuinely novel per-country insight if endpoint is available

**Defer to v2+:**
- Continent-level aggregate view — medium complexity, doesn't change core data model
- Cross-country audio feature comparison mode — extend detail panel; can add without rearchitecting
- Decade-of-release breakdown per country — requires additional release year enrichment pass
- Shareable image exports — vanity feature, no discovery value in v1
- Lyric search (ChromaDB) — already scoped as P2 in project decisions

### Architecture Approach

SoundAtlas is a direct domain translation of HealthMap: offline ETL pipeline → PostgreSQL → FastAPI REST API → Next.js frontend. The key structural insight from research is that pipeline data flows strictly downstream and never at request time — MusicBrainz and Spotify APIs are called only during pipeline runs, never by the backend at user request. The FastAPI backend is read-only against pre-seeded data, with the sole exception of the AI chat route which queries PostgreSQL for context then calls the Claude API (with Redis caching).

**Major components:**
1. Data Pipeline (Python scripts, offline) — parse Spotify export, enrich via Spotify API, resolve countries via MusicBrainz, seed PostgreSQL; 4 sequential scripts numbered for run order
2. FastAPI Backend (port 8000) — REST API serving countries, artists, search, analytics, and AI chat; reads PostgreSQL + writes/reads Redis cache
3. Next.js Frontend (port 3000) — Mapbox GL JS globe with data-driven circle layer, country detail sidebar, AI chat panel, fuzzy search; fetches from FastAPI only
4. PostgreSQL 15 — primary store; countries/artists/tracks tables with denormalized `track_count` on countries for map performance
5. Redis — AI response cache only (keyed on question + country_code hash, TTL 1 hour); also caches `/api/countries` list

### Critical Pitfalls

1. **MusicBrainz artist disambiguation** — searching by name alone selects wrong entities for common artist names (e.g., "Phoenix" returns French indie band AND 1980s disco act). Prevention: cross-reference MusicBrainz disambiguation field against Spotify genres; store `resolution_method` column; build manual override table before pipeline runs.

2. **Pipeline non-idempotency on 50-minute MusicBrainz run** — any crash at minute 43 requires a full restart without checkpointing. Prevention: add `mb_resolution_status` column (`pending/resolved/not_found/skipped`); pipeline always queries `WHERE mb_resolution_status = 'pending'`; commit each artist row individually.

3. **Spotify audio features endpoint deprecation** — endpoint restricted for new apps since November 2024; 403 responses leave audio feature charts empty with no clear error. Prevention: test endpoint access with actual app credentials before writing any enrichment code; design nullable columns with graceful degradation.

4. **Mapbox HTML markers at 3,022 artists kills performance** — `new mapboxgl.Marker()` per artist creates 3,022 DOM elements; map becomes unusable at <20fps. Prevention: use GeoJSON source + `circle` layer (WebGL-rendered); aggregate to country level (~200 countries); never use HTML markers for dataset-scale points.

5. **Genre classification against Spotify's 2,000+ hyper-specific tags** — displaying raw tags (e.g., "vapor twitch", "post-teen pop") makes genre UI meaningless. Prevention: two-pass data-driven bucketing — collect all unique tags from actual dataset, derive macro categories from frequency, store both raw and macro genres.

---

## Implications for Roadmap

Based on combined research findings, the architecture's strict data dependency order maps cleanly to 5 phases. Each phase has well-defined prerequisites from the one before it.

### Phase 1: Data Pipeline and Database Foundation

**Rationale:** Everything downstream depends on PostgreSQL being populated with origin-resolved artists. The MusicBrainz pipeline takes 50+ minutes and has the most risk (disambiguation errors, rate limits, endpoint deprecation). This must be proven end-to-end first. Build a 50-track fixture dataset early to unblock backend and frontend development in parallel.

**Delivers:** Populated PostgreSQL with tracks, artists, country origin codes, genres, and audio features (if available). Idempotent pipeline scripts runnable for re-enrichment. Manual override table for disambiguation corrections.

**Addresses:** Core data that all features depend on (map markers, artist lists, genre charts, diversity score, AI chat context).

**Avoids:**
- Pitfall 1 (disambiguation): build resolution_method column and override table before running full pipeline
- Pitfall 2 (non-idempotency): mb_resolution_status column + upsert pattern
- Pitfall 3 (audio features deprecation): verify endpoint access before writing enrichment code
- Pitfall 6 (genre bucketing): data-driven macro genre derivation in pipeline, not hardcoded constants
- Pitfall 13 (origin vs current country ambiguity): encode definition in schema DDL (begin_area, not area)

**Research flag:** Needs live API verification before implementation — Spotify audio features endpoint access is LOW confidence.

### Phase 2: FastAPI Backend API

**Rationale:** Backend can be built in parallel with Phase 1 using fixture data. The HealthMap reference codebase provides direct patterns for every route and service needed. No novel architectural decisions required.

**Delivers:** REST endpoints for `/api/countries`, `/api/artists`, `/api/search`, `/api/analytics/*`. SQLAlchemy ORM models, Pydantic schemas, lifespan startup pattern, CORS configuration. pg_trgm fuzzy search on artists and tracks.

**Uses:** FastAPI 0.115.x, SQLAlchemy 2.0.x async, asyncpg, Pydantic v2, alembic migrations — all from STACK.md.

**Implements:** Backend component from architecture; populates the data layer that all frontend components query.

**Avoids:**
- Pitfall 4 (markers at scale): denormalize track_count on countries table so map endpoint returns pre-computed counts
- Pitfall 11 (JSONB index): GIN index on genres array at schema creation; use correct `@>` operator in queries
- Pitfall 9 (pg_trgm short queries): document 3-character minimum, add ILIKE fallback for 1-2 char searches
- Anti-Pattern 2 (calling APIs at request time): backend is read-only against pre-seeded data only

**Research flag:** Standard patterns, skip research-phase. Direct HealthMap port with domain substitutions.

### Phase 3: Frontend Map and Country Detail Panel

**Rationale:** The core product screen. Must come after backend API exists to fetch real data. Mapbox GL JS patterns from STACK.md are well-specified and directly reusable from HealthMap.

**Delivers:** Interactive Mapbox world map with GeoJSON circle layer (sized by track count, colored by dominant genre). Country detail sidebar (artist list, genre pie chart, audio feature radar chart, top tracks). Global stats sidebar (diversity score, top countries, genre distribution, total counts). Fuzzy search with pg_trgm. Loading and error states.

**Uses:** mapbox-gl 3.16.0 (data-driven circle layer from STACK.md), recharts 3.4.1 (RadarChart for audio features), Next.js 16.2.0 App Router, TailwindCSS 4.x dark theme.

**Avoids:**
- Pitfall 4 (HTML markers): GeoJSON source + circle layer only
- Pitfall 5 (click/hover conflicts): layer-scoped event handlers; ref-based hover state, not React useState
- Pitfall 12 (Mapbox token exposure): URL-restrict token in Mapbox dashboard before deployment
- Pitfall 14 (unresolved artists disappearing): explicit UI design for artists without country_code
- Pitfall 15 (diversity score instability): minimum 3-track threshold in Shannon entropy calculation

**Research flag:** Standard patterns, skip research-phase. Mapbox data-driven circle layer API is HIGH confidence and fully specified in STACK.md.

### Phase 4: AI Chat Panel

**Rationale:** Requires PostgreSQL context assembly, Claude API, and Redis cache — all dependent on Phases 1-3. The chat panel is the highest-value differentiator but has the most integration complexity. Keep it isolated until the core map experience works.

**Delivers:** AI chat panel with natural language music queries, conversation history, per-country and global context. Redis-cached responses (TTL 1 hour). RAG context builder with pre-aggregated stats (not raw track data).

**Uses:** anthropic 0.86.0, Claude model via `CLAUDE_MODEL` env var, Redis 7-alpine. Pattern from HealthMap `ai_service.py` and `insights.py` route.

**Avoids:**
- Pitfall 10 (context window overflow): never send raw track rows to Claude; send pre-aggregated stats (top 20 countries, top 30 genre buckets, summary distributions); RAG retrieves 5-20 rows for specific queries
- Anti-Pattern 4 (frontend calling Claude directly): all AI calls through `POST /api/chat`; context assembly and caching happen in `ai_service.py`

**Research flag:** Standard patterns for Claude API integration (HealthMap is the reference). RAG context design is the only non-trivial decision — follow the fetch-aggregate-then-prompt pattern.

### Phase 5: Polish, Search, and Analytics

**Rationale:** Refinement pass after core features are validated. Includes search UX improvements, additional analytics charts, performance tuning, and deployment configuration.

**Delivers:** Polished search experience with result navigation to country/artist focus. Additional analytics views (genre evolution, top tracks per country). Deployment configuration for Vercel + Railway. Mapbox token URL restriction. Performance validation.

**Avoids:**
- Pitfall 9 (pg_trgm short queries): validate search edge cases with 1-2 character inputs
- Pitfall 12 (token exposure): confirm URL restriction is applied pre-launch

**Research flag:** Standard patterns. Skip research-phase unless new features are added to scope.

### Phase Ordering Rationale

- Data pipeline must precede backend because PostgreSQL must be populated before API routes return real data. Fixture dataset (50 tracks) unblocks parallel development of Phases 2 and 3.
- Backend must precede frontend because Next.js components call FastAPI endpoints — without the API, frontend development requires extensive mocking.
- Map and detail panel (Phase 3) must precede AI chat (Phase 4) because the map provides the user interaction context (selected country) that the AI chat leverages, and the AI panel is additive complexity on top of a working core.
- Search and polish (Phase 5) is deferred because it adds no new data model requirements — it refines the existing system.

This ordering directly mirrors the architecture's data flow: pipeline → database → API → UI → AI.

### Research Flags

Phases needing deeper research or live verification during planning:
- **Phase 1 (pipeline):** Spotify audio features endpoint access requires live API verification before implementation. LOW confidence on current availability for new app registrations (Spotify Nov 2024 deprecation). Also verify MusicBrainz `begin_area` traversal cost — may require additional API calls per artist.
- **Phase 1 (pipeline):** MusicBrainz disambiguation strategy needs testing with actual artist names from the dataset before full pipeline runs. Cross-reference approach is specified but not tested.

Phases with standard patterns (skip research-phase):
- **Phase 2 (backend):** Direct HealthMap port. FastAPI + SQLAlchemy + asyncpg patterns are HIGH confidence.
- **Phase 3 (frontend):** Mapbox data-driven circle layer and Recharts RadarChart are fully specified in STACK.md with working code patterns.
- **Phase 4 (AI chat):** HealthMap `ai_service.py` is the direct reference. No novel patterns required.
- **Phase 5 (polish):** Standard deployment and search refinement work.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified from HealthMap reference codebase and PyPI. Mapbox/Recharts/FastAPI patterns directly portable. Redis client API minor version difference is the only flag. |
| Features | MEDIUM | Competitor feature set from training data (August 2025 cutoff); verify current Stats for Spotify and Obscurify features before finalizing. Core value proposition analysis is HIGH confidence. |
| Architecture | HIGH | Derived from direct HealthMap codebase inspection. All component boundaries, data flows, and anti-patterns are grounded in a working reference implementation. |
| Pitfalls | HIGH (12/15) / LOW (3/15) | Most pitfalls are well-documented API/library behaviors. Three LOW confidence items: Spotify audio features current status (verify live), MusicBrainz begin_area traversal behavior in edge cases, competitor feature currency. |

**Overall confidence:** HIGH for implementation decisions. Spotify audio features is the one hard unknown that must be validated before Phase 1 enrichment code is written.

### Gaps to Address

- **Spotify audio features endpoint access:** Cannot determine availability without a live API call using actual SoundAtlas app credentials. Test immediately in Phase 1 before writing any features enrichment code. Design the pipeline to gracefully skip audio features if 403 is returned — the core map works without them.
- **MusicBrainz disambiguation accuracy on actual dataset:** The disambiguation strategy (cross-reference Spotify genres + score threshold) is specified but untested on the actual 3,022 artist names. Budget time in Phase 1 for a manual audit of the first 200 resolved artists to calibrate confidence thresholds.
- **MusicBrainz begin_area vs area traversal cost:** Using `begin_area` for more accurate origin data may require traversing MusicBrainz's area hierarchy (area → parent area → country). This could add significant latency per artist. Evaluate in Phase 1 whether the accuracy improvement justifies the extra API calls, or whether `area` (simpler) is sufficient for v1.
- **Competitor current feature state:** FEATURES.md based on training data (August 2025 cutoff). Verify that Stats for Spotify still operates as described and that no major new competitor has entered the geographic music analytics space.
- **Redis client 5.x to 7.x upgrade:** HealthMap uses redis 5.0.1; SoundAtlas upgrades to 7.x for async support. Test aioredis compatibility and async client API differences before writing caching code.

---

## Sources

### Primary (HIGH confidence)
- HealthMap codebase (`/Users/udirno/Desktop/HealthMap/`) — direct inspection of backend, frontend, Docker Compose; all HealthMap-matched patterns
- PyPI package registry — all Python versions verified live 2026-03-24 (spotipy 2.26.0, musicbrainzngs 0.7.1, tenacity 9.1.4, FastAPI 0.115.x, SQLAlchemy 2.0.48, anthropic 0.86.0)
- HealthMap `requirements.txt` + `package.json` — authoritative version source for all shared dependencies
- MusicBrainz API documentation (training data) — 1 req/sec rate limit, artist entity fields, search API behavior
- Mapbox GL JS 3.x documentation (training data) — data-driven circle layer, event handler patterns, performance guide
- PostgreSQL JSONB + pg_trgm documentation (training data) — GIN index behavior, operator requirements

### Secondary (MEDIUM confidence)
- Spotify Developer documentation (training data, August 2025 cutoff) — audio features endpoint, Client Credentials flow, batch endpoint limits
- Competitor platform feature sets (Spotify Wrapped, Last.fm, Stats for Spotify, Obscurify, Receiptify) — training data; verify current state

### Tertiary (LOW confidence)
- Spotify audio features deprecation status (November 2024 announcement) — must verify with live API call; current restriction policy unclear for apps in different registration cohorts

---

*Research completed: 2026-03-24*
*Ready for roadmap: yes*
