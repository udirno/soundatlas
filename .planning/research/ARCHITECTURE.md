# Architecture Patterns

**Domain:** Music data + geographic visualization platform (personal music intelligence)
**Project:** SoundAtlas — maps 9,115 liked Spotify tracks by artist origin country
**Researched:** 2026-03-24
**Confidence:** HIGH — derived from direct inspection of HealthMap codebase, the declared reference implementation

---

## Recommended Architecture

SoundAtlas is a four-layer system: an offline data pipeline seeds PostgreSQL, a FastAPI backend serves the data, a Next.js frontend visualizes it, and Docker Compose orchestrates all services. The architecture is a direct parallel of HealthMap with domain substitutions (countries/diseases → countries/tracks/artists).

```
┌─────────────────────────────────────────────────────┐
│  DATA PIPELINE (offline, run once + on-demand)      │
│  Python scripts → PostgreSQL seed                   │
│                                                     │
│  spotify_export.json                                │
│       ↓                                             │
│  01_parse_export.py     (extract track IDs)         │
│       ↓                                             │
│  02_enrich_spotify.py   (Spotify API: artist info)  │
│       ↓                                             │
│  03_lookup_musicbrainz.py (country of origin)       │
│       ↓                                             │
│  04_seed_db.py          (write to PostgreSQL)       │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  POSTGRESQL (primary data store)                    │
│  Tables: tracks, artists, countries                 │
│  Indexes on: country_code, artist_id, track_id      │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  FASTAPI BACKEND (port 8000)                        │
│  app/                                               │
│    main.py          (lifespan pattern, CORS)        │
│    database.py      (SQLAlchemy session factory)    │
│    models/          (ORM: Track, Artist, Country)   │
│    schemas/         (Pydantic: request/response)    │
│    api/routes/                                      │
│      countries.py   (GET /api/countries)            │
│      artists.py     (GET /api/artists)              │
│      search.py      (GET /api/search)               │
│      analytics.py   (GET /api/analytics/*)          │
│      chat.py        (POST /api/chat)                │
│    services/                                        │
│      country_service.py                             │
│      artist_service.py                              │
│      search_service.py                              │
│      ai_service.py  (Claude API + Redis cache)      │
└─────────────────────────────────────────────────────┘
         │                          │
         │                     REDIS (port 6379)
         │                     AI response cache
         ▼
┌─────────────────────────────────────────────────────┐
│  NEXT.JS 14 FRONTEND (port 3000)                    │
│  src/                                               │
│    app/                                             │
│      layout.tsx     (root layout)                   │
│      page.tsx       (main page, state root)         │
│    components/                                      │
│      map/                                           │
│        MapContainer.tsx  (Mapbox GL JS globe)       │
│      layout/                                        │
│        Sidebar.tsx       (country detail panel)     │
│        AIInsightPanel.tsx (chat UI)                 │
│        NavBar.tsx        (top bar)                  │
│      charts/                                        │
│        GenreChart.tsx    (Recharts)                 │
│    lib/                                             │
│      api-client.ts  (fetch wrapper → FastAPI)       │
│    types/           (TypeScript interfaces)         │
└─────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Does NOT Do |
|-----------|---------------|-------------------|-------------|
| **Data Pipeline** | One-time ETL: parse Spotify export, enrich via APIs, resolve countries, seed DB | Spotify API, MusicBrainz API, PostgreSQL | Serve HTTP; has no runtime role |
| **PostgreSQL** | Persist all track/artist/country data; answer SQL queries | Backend (SQLAlchemy), Pipeline (psycopg2) | Cache, serve HTTP |
| **Redis** | Cache AI chat responses; prevent redundant Claude API calls | Backend only | Store primary data |
| **FastAPI Backend** | Serve REST API; fetch DB context for AI; proxy Claude calls | PostgreSQL (read), Redis (read/write), Claude API | Serve frontend assets; run pipeline |
| **Next.js Frontend** | Render map, handle UI state, send user questions to backend | FastAPI only (via `api-client.ts`) | Query DB or Claude directly |
| **Docker Compose** | Orchestrate all services; manage healthchecks, networks, env | All services | Application logic |

---

## Data Flow

### Primary Read Flow (Map → Country Detail)

```
User clicks country on map
  → MapContainer.tsx fires onRegionSelect(countryCode)
  → page.tsx state updates: selectedCountry = "GBR"
  → Sidebar.tsx calls apiClient.getCountry("GBR")
  → GET /api/countries/GBR
  → country_service.py queries PostgreSQL
  → Returns: { country, track_count, artists[], top_genres[], top_tracks[] }
  → Sidebar renders detail panel
```

### Search Flow

```
User types in search box
  → Debounced call to apiClient.search(q)
  → GET /api/search?q=radiohead
  → search_service.py queries artists + tracks ILIKE
  → Returns ranked results
  → Dropdown renders, user selects → triggers country or artist focus
```

### AI Chat Flow

```
User submits question in AIInsightPanel
  → apiClient.sendChat({ question, country, conversation_history })
  → POST /api/chat
  → ai_service.py checks Redis cache (hash of question + country)
  → Cache MISS: query PostgreSQL for context
    - country stats, top artists, genre breakdown, track sample
  → Build system prompt + context string
  → Call Claude API (claude-sonnet-4-*) with messages[]
  → Store response in Redis (TTL: 1 hour)
  → Return { narrative, supporting_data }
  → AIInsightPanel appends assistant message to thread
```

### Data Pipeline Flow (offline)

```
Spotify "Liked Songs" export JSON
  → 01_parse_export.py: extract { track_id, track_name, artist_name, album }
  → 02_enrich_spotify.py: Spotify API batch → { artist_id, genres, popularity }
  → 03_lookup_musicbrainz.py: MusicBrainz API → { artist_country_code }
  → 04_seed_db.py: upsert into PostgreSQL
      countries table (ISO codes, names, lat/lon, track_count)
      artists table (id, name, country_code, genres)
      tracks table (id, name, artist_id, added_at)
```

---

## HealthMap Pattern Mapping to SoundAtlas

| HealthMap Component | SoundAtlas Equivalent | Key Differences |
|--------------------|-----------------------|-----------------|
| `ingest_covid_complete.py` | `02_enrich_spotify.py` + `03_lookup_musicbrainz.py` | Two-step enrichment vs single download; rate limiting required for both APIs |
| `Region` model | `Country` model | Country is lookup/dimension table, not a time-series fact table |
| `DiseaseRecord` model | `Track` model | Tracks are static facts, not daily time-series records |
| `Disease` model | `Artist` model | Artist is a dimension with country FK |
| `disease.py` route | `countries.py` + `artists.py` routes | Split by entity type |
| `insights.py` route (AI) | `chat.py` route | Same pattern: gather DB context → Claude → return narrative |
| `AIService.generate_insight()` | `AIService.generate_music_insight()` | Same structure; domain-specific prompt and context fields |
| `AIInsightPanel.tsx` | `AIInsightPanel.tsx` | Identical chat UI pattern; copy and adapt |
| `MapContainer.tsx` | `MapContainer.tsx` | Same Mapbox GL JS setup; color encoding changes to track-count choropleth |
| `Sidebar.tsx` | `Sidebar.tsx` | Replace disease/date filters with genre/decade filters |
| `TrendChart.tsx` | `GenreChart.tsx` | Recharts bar/pie for genre breakdown vs time-series line |
| `docker-compose.yml` | `docker-compose.yml` | Identical service topology; rename containers |

---

## Data Model

### Core Tables

```sql
-- Countries: dimension table, one row per country
countries (
  id           SERIAL PRIMARY KEY,
  iso_code     VARCHAR(3) UNIQUE NOT NULL,  -- "GBR", "USA"
  name         VARCHAR NOT NULL,
  latitude     FLOAT,
  longitude    FLOAT,
  track_count  INT DEFAULT 0               -- denormalized for map performance
)

-- Artists: dimension, linked to country
artists (
  id           VARCHAR PRIMARY KEY,         -- Spotify artist ID
  name         VARCHAR NOT NULL,
  country_code VARCHAR(3) REFERENCES countries(iso_code),
  genres       TEXT[],                      -- Postgres array
  popularity   INT
)

-- Tracks: fact table
tracks (
  id           VARCHAR PRIMARY KEY,         -- Spotify track ID
  name         VARCHAR NOT NULL,
  artist_id    VARCHAR REFERENCES artists(id),
  album_name   VARCHAR,
  added_at     TIMESTAMP,
  duration_ms  INT,
  popularity   INT
)
```

### Indexes Required

```sql
CREATE INDEX idx_artists_country ON artists(country_code);
CREATE INDEX idx_tracks_artist   ON tracks(artist_id);
CREATE INDEX idx_tracks_added_at ON tracks(added_at);
```

---

## Patterns to Follow

### Pattern 1: Lifespan Startup (FastAPI)

Matches HealthMap `main.py` exactly. On startup, import all models to ensure SQLAlchemy registers them before `Base.metadata.create_all()`.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.models  # noqa: register all ORM classes
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="SoundAtlas API", lifespan=lifespan)
```

### Pattern 2: AI Context Assembly

Matches HealthMap `insights.py`. The route handler assembles domain context from PostgreSQL, then hands it to `AIService`. Do not pass raw SQLAlchemy objects — serialize to dicts first.

```python
@router.post("/chat")
async def chat(query: ChatQuery, db: Session = Depends(get_db)):
    country = CountryService.get_with_stats(db, query.country_code)
    top_artists = ArtistService.get_top_by_country(db, query.country_code, limit=10)
    genre_breakdown = ArtistService.get_genre_breakdown(db, query.country_code)

    context = {
        "country": country,
        "top_artists": top_artists,
        "genre_breakdown": genre_breakdown
    }
    narrative = ai_service.generate_music_insight(
        question=query.question,
        context=context,
        conversation_history=query.conversation_history
    )
    return ChatResponse(narrative=narrative)
```

### Pattern 3: Choropleth Map via Mapbox Expression

Matches HealthMap `MapContainer.tsx`. Use a data-driven `fill-color` expression keyed on `iso_3166_1_alpha_3`. For SoundAtlas, encode track count as color intensity (green gradient instead of red).

```typescript
map.current.setPaintProperty('country-fills', 'fill-color', [
  'case',
  ['==', ['get', 'iso_3166_1_alpha_3'], selectedCountry],
  '#10b981',   // bright teal for selected
  // ... color scale by track count
  'rgba(16, 185, 129, 0.15)'  // faint for unselected
]);
```

### Pattern 4: Redis Cache for AI Responses

Cache key = hash of (question + country_code). TTL 3600s. Check before calling Claude; store after. This prevents identical questions from consuming API quota.

### Pattern 5: Pipeline as Standalone Scripts

Matches HealthMap `data-pipeline/scripts/`. Each script is independently runnable with direct psycopg2 (not SQLAlchemy). Scripts read from `.env` for `DATABASE_URL`. Run order is enforced by numbered filenames.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Async SQLAlchemy in Pipeline Scripts
**What:** Using `async_sessionmaker` in data pipeline scripts
**Why bad:** Pipeline runs once synchronously; async adds complexity with no benefit; HealthMap pipeline correctly uses synchronous psycopg2
**Instead:** Use synchronous `psycopg2` with `execute_values` for bulk inserts in pipeline; reserve async SQLAlchemy for the FastAPI backend

### Anti-Pattern 2: Calling Spotify/MusicBrainz APIs at Request Time
**What:** Enriching data on-demand in the FastAPI backend when a user loads a country
**Why bad:** MusicBrainz rate-limits to 1 req/sec; Spotify API has quota limits; adds latency; data never changes for a static liked-songs dataset
**Instead:** All enrichment happens offline in the pipeline. Backend serves only pre-seeded data.

### Anti-Pattern 3: Storing Genres as Separate Table
**What:** Normalizing genres into a join table (Track → TrackGenre → Genre)
**Why bad:** Over-engineered for read-only display; genres are a Spotify-provided array attribute of the artist; querying becomes complex
**Instead:** Store genres as a PostgreSQL `TEXT[]` array on the `artists` table. Use `unnest()` for aggregation queries.

### Anti-Pattern 4: Frontend Calling Claude Directly
**What:** Next.js making direct Claude API calls from the browser
**Why bad:** Exposes API key in client bundle; bypasses Redis cache; bypasses context assembly
**Instead:** All AI calls go through `POST /api/chat` on FastAPI, which assembles context and manages caching.

### Anti-Pattern 5: Choropleth Without Denormalized Count
**What:** Computing `COUNT(tracks) GROUP BY country` on every map render
**Why bad:** Fires on every page load; no caching; for 9,115 tracks across ~100+ countries this is fast now but patterns matter
**Instead:** Denormalize `track_count` onto the `countries` table, updated once at pipeline seed time. Map fetches `GET /api/countries` (cached in Redis) with counts pre-computed.

---

## Build Order and Phase Dependencies

```
Phase 1: Data Pipeline
  ↓ (PostgreSQL must be populated before backend can serve data)

Phase 2: Backend API (countries, artists, tracks endpoints)
  ↓ (API must exist before frontend can fetch data)

Phase 3: Frontend — Map + Country Detail Panel
  ↓ (core UI working before adding AI complexity)

Phase 4: AI Chat Panel
  ↓ (requires: PostgreSQL context, Claude API key, Redis cache)

Phase 5: Polish — search, filters, analytics charts
```

**Critical dependency:** Phase 1 (pipeline) must complete end-to-end — including MusicBrainz country resolution — before Phase 2 can be validated with real data. Build a small fixture dataset (50 tracks) first to unblock backend and frontend development.

**Redis is required from Phase 4 onward** but not before. Docker Compose should include Redis from the start (low cost to add early, painful to retrofit).

---

## Scalability Considerations

This is a personal analytics tool with a fixed dataset (9,115 tracks). Scalability is not a production concern. The relevant concern is **development convenience**:

| Concern | Approach |
|---------|----------|
| Map render performance | Denormalize `track_count` on `countries`; cache `/api/countries` list in Redis |
| AI response latency | Cache by (question, country) in Redis; Claude latency is 1-3s cold |
| Pipeline re-runs | Make all pipeline scripts idempotent (upsert, not insert) |
| MusicBrainz rate limit | Add `time.sleep(1.1)` between requests in `03_lookup_musicbrainz.py` |
| Missing country data | ~15-20% of artists may have no MusicBrainz country; pipeline must handle gracefully with `NULL` country_code and a fallback "Unknown" bucket in the UI |

---

## Sources

- HealthMap codebase: `/Users/udirno/Desktop/HealthMap/` (direct inspection, HIGH confidence)
  - `backend/app/main.py` — lifespan pattern
  - `backend/app/database.py` — SQLAlchemy session factory
  - `backend/app/services/ai_service.py` — Claude API integration
  - `backend/app/api/routes/insights.py` — AI context assembly pattern
  - `frontend/src/components/map/MapContainer.tsx` — Mapbox GL JS choropleth
  - `frontend/src/components/layout/AIInsightPanel.tsx` — chat UI pattern
  - `frontend/src/components/layout/Sidebar.tsx` — detail panel pattern
  - `docker-compose.yml` — service topology
- Project context: provided in research brief (SoundAtlas description, component list, data flow)
