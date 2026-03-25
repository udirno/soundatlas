---
phase: 03-backend-api
verified: 2026-03-25T04:10:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "GET /api/search?q= returns fuzzy-matched artists and tracks using pg_trgm, including a 'Not in your library' signal for missing items"
    status: partial
    reason: "The in_library signal is correctly wired in code (EXISTS subquery against user_tracks), but every track in the tracks table (9115 rows) is also present in user_tracks (9115 rows). As a result in_library=False can never be returned at runtime. The 'Not in your library' outcome — the core signal value — is structurally unreachable with the current seeded data and no mechanism exists to surface tracks not owned by the user."
    artifacts:
      - path: "backend/app/services/search_service.py"
        issue: "Code is correct but in_library=False is never observable because tracks and user_tracks are 1:1 identical"
    missing:
      - "Clarify whether user_tracks should be a strict subset of tracks (only imported tracks, not all tracks). If so, the pipeline or seed step must be corrected so user_tracks only contains tracks actually 'saved' by the user, not every track scraped."
      - "Alternatively, document this as a known data state (all tracks belong to the user's Spotify export) and update the success criterion to reflect that in_library is always true for this dataset."
---

# Phase 3: Backend API Verification Report

**Phase Goal:** All REST endpoints return correct data from the seeded PostgreSQL database, fuzzy search works against artists and tracks, and the backend matches HealthMap's async patterns, CORS configuration, and startup behavior.
**Verified:** 2026-03-25T04:10:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/countries returns countries with artist count, track count, and top genre | VERIFIED | 249 countries returned; US shows artist_count=1114, track_count=4203, top_genre="r&b" |
| 2 | GET /api/countries/{id} and /comparison return full artist lists, genre breakdown, and audio feature averages vs global averages | VERIFIED | /countries/235 returns 1114 artists, 5-key genre_breakdown, 5-key audio_feature_averages (all null — known Spotify restriction); /comparison returns country_averages and global_averages with all 5 features |
| 3 | GET /api/search?q= returns fuzzy-matched artists and tracks using pg_trgm, including a "Not in your library" signal for missing items | PARTIAL | pg_trgm fuzzy search works ("radioheed" returns Radiohead at score=0.54); in_library field present on all track hits; however in_library=False is never returned because all 9115 tracks are in user_tracks — the "missing items" signal cannot be observed at runtime |
| 4 | GET /api/analytics/dashboard returns global stats including diversity score, top countries, and genre distribution | VERIFIED | Returns country_count=249, artist_count=2174, track_count=7513, diversity_score=0.5044, top_genres (10 items), top_countries (10 items) |
| 5 | POST /api/ai/ask and GET /api/ai/suggestions routes exist and return structured responses | VERIFIED | POST /ask returns AIAskResponse with answer, sources, query fields; GET /suggestions returns 5 AISuggestion items |

**Score:** 4/5 truths verified (1 partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/main.py` | FastAPI app with routers + CORS + lifespan | VERIFIED | All 5 routers registered; CORSMiddleware with cors_origins_list; async lifespan pattern used |
| `backend/app/api/routes/countries.py` | 3 country endpoints | VERIFIED | GET /api/countries, /{id}, /{id}/comparison all present and wired to country_service |
| `backend/app/api/routes/search.py` | Fuzzy search endpoint | VERIFIED | GET /api/search with q param; delegates to search_service.fuzzy_search |
| `backend/app/api/routes/analytics.py` | 3 analytics endpoints | VERIFIED | /dashboard, /genres, /features all present; wired to analytics_service |
| `backend/app/api/routes/ai.py` | AI stub endpoints | VERIFIED | POST /ask (stub) and GET /suggestions both present and return correct schema |
| `backend/app/api/routes/artists.py` | Artist endpoints | VERIFIED | GET /api/artists (3022 results) and /{id} both present |
| `backend/app/services/country_service.py` | Country + artist service functions | VERIFIED | get_country_list, get_country_detail, get_country_comparison, get_artist_list, get_artist_detail all present; substantive queries with selectinload |
| `backend/app/services/search_service.py` | pg_trgm fuzzy search | VERIFIED | fuzzy_search uses func.similarity() with threshold 0.15; EXISTS subquery for in_library signal |
| `backend/app/services/analytics_service.py` | Analytics + diversity score | VERIFIED | calculate_diversity_score (Shannon entropy), get_dashboard_stats, get_genre_distribution (raw SQL unnest), get_feature_averages all present |
| `backend/app/schemas/country.py` | CountryListItem, CountryDetail, CountryComparison | VERIFIED | All 3 schemas present with correct fields and from_attributes=True |
| `backend/app/schemas/search.py` | SearchResult, SearchArtistHit, SearchTrackHit | VERIFIED | All schemas present; SearchTrackHit includes in_library: bool |
| `backend/app/schemas/analytics.py` | DashboardStats, GenreResponse, FeatureResponse | VERIFIED | All 3 response schemas present with correct structure |
| `backend/app/schemas/ai.py` | AIAskRequest, AIAskResponse, AISuggestion | VERIFIED | All 3 schemas present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| countries.py router | country_service.get_country_list | Depends(get_db) | WIRED | Live call returns 249 rows |
| countries.py router | country_service.get_country_comparison | Depends(get_db) | WIRED | Live call returns both averages dicts |
| search.py router | search_service.fuzzy_search | Depends(get_db) | WIRED | Live call with "radiohead" returns 5 artists, 20 tracks |
| search_service | pg_trgm func.similarity() | func.similarity(col, q) | WIRED | pg_trgm extension confirmed; GIN indexes on artists.name and tracks.name confirmed; similarity query visible in backend logs |
| search_service | user_tracks (in_library signal) | EXISTS subquery | WIRED (code) | Subquery correct; in_library=True for all current data; in_library=False unreachable due to seeding state |
| analytics.py router | analytics_service.get_dashboard_stats | Depends(get_db) | WIRED | Returns live data: diversity_score=0.5044 |
| analytics_service | Shannon entropy | calculate_diversity_score() | WIRED | Math verified; normalized to [0,1]; edge case n<=1 handled |
| analytics_service | PostgreSQL unnest via text() | raw SQL with bindparams | WIRED | genres endpoint returns 20 global genres |
| ai.py | AIAskRequest/AIAskResponse schemas | Pydantic models | WIRED | POST /ask returns correct JSON structure |
| main.py | CORS | CORSMiddleware with cors_origins_list | WIRED | OPTIONS preflight returns access-control-allow-origin: http://localhost:3000 |
| main.py | async lifespan | @asynccontextmanager lifespan | WIRED | engine.dispose() on shutdown; no deprecated on_event |
| database.py | AsyncSession | create_async_engine + async_sessionmaker | WIRED | expire_on_commit=False; pool_pre_ping=True |

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| API-01: GET /api/countries | SATISFIED | 249 countries with artist_count, track_count, top_genre |
| API-02: GET /api/countries/{id} | SATISFIED | Artists list, genre_breakdown (dict), audio_feature_averages (all null — Spotify restriction) |
| API-03: GET /api/countries/{id}/comparison | SATISFIED | country_averages and global_averages with 5 audio features each |
| API-04: GET /api/artists | SATISFIED | 3022 artists returned with optional ?q= filter |
| API-05: GET /api/artists/{id} | SATISFIED | Returns artist with tracks list |
| API-06: GET /api/search?q= | PARTIAL | pg_trgm fuzzy search works; in_library field present; in_library=False unreachable in current data state |
| API-07: GET /api/analytics/dashboard | SATISFIED | diversity_score, top_countries, top_genres, counts all present |
| API-08: GET /api/analytics/genres | SATISFIED | global_genres and country_genres (when country_id supplied) |
| API-09: GET /api/analytics/features | SATISFIED | global_averages and optional country_averages (all null due to Spotify restriction) |
| API-10: POST /api/ai/ask | SATISFIED (stub) | Route exists, returns AIAskResponse; RAG deferred to Phase 6 per ROADMAP |
| API-11: GET /api/ai/suggestions | SATISFIED | Returns 5 pre-built AISuggestion items |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/api/routes/ai.py` | 13 | Stub implementation — static response, no DB access | Info | Expected per ROADMAP (Phase 6 delivers AI); success criterion 5 explicitly allows this |

### Human Verification Required

None — all checks completed programmatically via live endpoint calls and DB queries.

## Gaps Summary

### Gap 1: in_library=False is Structurally Unreachable

The search service correctly implements the "Not in your library" signal using a correlated EXISTS subquery against the user_tracks table. The code is not a stub — the query is genuinely wired. However, the current database state has all 9115 tracks in user_tracks (a 1:1 match with the tracks table). This means in_library will always be True for every search result, making the intended signal ("this track exists in the system but you haven't saved it") unobservable.

The root cause appears to be in how the data pipeline was seeded: every scraped track was inserted into both tracks and user_tracks simultaneously, rather than user_tracks containing only the user's saved/exported tracks.

This is a partial failure of success criterion 3: fuzzy search works and returns the field, but the observable behavior ("Not in your library" appearing for unsaved items) cannot be demonstrated.

**Options for resolution:**
1. Correct the data model: user_tracks should be a strict subset of tracks (only explicitly saved tracks). The pipeline seed step or Spotify import should write to user_tracks only for tracks the user actually saved.
2. Accept as-is with documentation: If all 9115 tracks represent the user's actual Spotify export (i.e., everything is intentionally "in library"), update the success criterion to remove the "missing items" framing. The in_library field becomes a future-use signal for Phase 5/6 when external track discovery is added.

---

_Verified: 2026-03-25T04:10:00Z_
_Verifier: Claude (gsd-verifier)_
