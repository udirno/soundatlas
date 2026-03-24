# Technology Stack

**Project:** SoundAtlas
**Researched:** 2026-03-24
**Confidence:** HIGH (all versions verified from PyPI/reference codebase)

## Context

Stack is **constrained to match HealthMap**. This file documents the canonical versions and explains
the domain-specific library choices (Spotify API, MusicBrainz, Mapbox GL JS patterns) that HealthMap
doesn't cover.

---

## Recommended Stack

### Core Framework (Backend)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11 | Backend runtime | Matches HealthMap `runtime.txt`; 3.12 not used to avoid dependency breakage |
| FastAPI | 0.115.x | HTTP API layer | Matches HealthMap pattern; async-native; pydantic v2 integration |
| Uvicorn[standard] | 0.34.x | ASGI server | Matches HealthMap; `[standard]` adds websocket support for future streaming |
| Pydantic v2 | 2.11.x | Data validation / settings | HealthMap runs 2.11.10; v2 is required (v1 is EOL) |
| pydantic-settings | 2.10.x | Config from `.env` | Matches HealthMap `config.py` pattern |
| python-dotenv | 1.1.x | `.env` file loading | HealthMap pattern; version 1.1.x on PyPI |

**Confidence:** HIGH — sourced from HealthMap `requirements.txt` and verified against PyPI latest.

### Data Pipeline (Python Scripts)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| spotipy | 2.26.0 | Spotify Web API client | Latest stable on PyPI (verified 2026-03-24); wraps auth + all endpoints |
| musicbrainzngs | 0.7.1 | MusicBrainz API client | Latest stable on PyPI; only maintained Python client; handles XML parsing |
| httpx | 0.27.x | Async HTTP fallback | Matches HealthMap; use for direct MusicBrainz calls if musicbrainzngs is too slow |
| tenacity | 9.1.4 | Retry with backoff | Latest stable on PyPI; handles 429 / 503 from both Spotify and MusicBrainz |
| pandas | 2.3.x | JSON parsing, deduplication | Matches HealthMap pipeline pattern; read `YourLibrary.json`, deduplicate artists |
| numpy | 2.2.x | Shannon entropy calculation | Matches HealthMap; diversity score computation |
| tqdm | 4.67.x | Progress bars for pipeline | Long-running enrichment scripts (50-minute MusicBrainz run) need visibility |
| pyyaml | 6.0.x | Config/cache YAML files | Matches HealthMap |

**Confidence:**
- spotipy 2.26.0: HIGH — verified PyPI
- musicbrainzngs 0.7.1: HIGH — verified PyPI (only version series, last release 2019, still functional)
- tenacity 9.1.4: HIGH — verified PyPI

### Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 15 | Primary data store | Matches HealthMap; `postgis/postgis:15-3.3` Docker image |
| PostGIS | 3.3 | Geospatial data support | Matches HealthMap; country coordinates for PostGIS geometry |
| SQLAlchemy | 2.0.48 | ORM | Latest 2.0.x on PyPI; HealthMap uses 2.0.23 — pin to `>=2.0.23,<2.1` for safety |
| asyncpg | 0.29.x | Async PostgreSQL driver | Required for `async_sessionmaker` pattern; SQLAlchemy async mode |
| alembic | 1.16.x | DB migrations | Matches HealthMap; latest stable on PyPI |

**Confidence:** HIGH — all versions verified PyPI.

### Caching

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Redis | 7-alpine | In-memory cache | Matches HealthMap Docker image exactly |
| redis (Python) | 7.x | Python Redis client | Latest stable on PyPI (HealthMap uses 5.0.1 — upgrade to 7.x for async support) |

**Note:** HealthMap has Redis configured but unused. SoundAtlas should actually use it for caching
audio feature lookups and MusicBrainz country results since the pipeline is long-running and
resumable.

**Confidence:** MEDIUM — redis 7.x client API differs from 5.x in minor ways; test `aioredis`
compatibility if using async caching.

### AI Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| anthropic | 0.86.0 | Claude API client | Latest stable on PyPI; HealthMap uses 0.80.0 — upgrade for latest model access |

**Model:** `claude-sonnet-4-20250514` — same as HealthMap; do NOT hardcode, use env var
`CLAUDE_MODEL` per HealthMap CONCERNS.md advice.

**Confidence:** HIGH — verified PyPI.

### Frontend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js | 16.2.0 | React framework | Exact HealthMap version; App Router is the pattern used |
| React | 19.2.0 | UI library | Exact HealthMap version |
| TypeScript | 5.x | Type safety | Exact HealthMap pattern; strict mode enabled |
| TailwindCSS | 4.x | Styling | Exact HealthMap version; dark theme with slate/blue palette |
| Tailwind Typography | 0.5.x | Rich text | Exact HealthMap version |
| mapbox-gl | 3.16.0 | Map rendering | Exact HealthMap version — critically important, do not upgrade |
| @types/mapbox-gl | 3.4.x | TypeScript types | Exact HealthMap version |
| recharts | 3.4.1 | Audio feature charts | Exact HealthMap version; radar/bar charts for feature analytics |
| lucide-react | 0.553.0 | Icons | Exact HealthMap version |
| axios | 1.13.2 | HTTP client | Exact HealthMap version; centralized `api-client.ts` pattern |

**Confidence:** HIGH — sourced directly from HealthMap `package.json`.

### Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker Compose | 3.8 | Local dev orchestration | Exact HealthMap `docker-compose.yml` format |
| Docker | latest | Container runtime | HealthMap pattern |
| Vercel | — | Frontend deployment | Exact HealthMap deployment target; `vercel.json` config |
| Railway | — | Backend + DB + Redis | Replaces HealthMap's Render (Railway recommended for Railway's better PostgreSQL addons) |

**Note on deployment platform:** HealthMap uses Render. PROJECT.md specifies Railway for backend.
Railway and Render are functionally equivalent for this stack. Railway's PostgreSQL addon has better
free-tier reliability in 2025. Follow Railway's env var injection pattern instead of Render's
blueprint format.

**Confidence:** HIGH for Docker/Vercel. MEDIUM for Railway (project decision, not research-verified).

---

## Domain-Specific Library Guidance

### Spotify Web API Authentication

**Use Client Credentials Flow, not Authorization Code Flow.**

SoundAtlas ships pre-loaded with personal data. There is no user login. The data pipeline runs
offline to enrich the Spotify data export. Client Credentials grants access to:
- `GET /audio-features/{id}` — energy, danceability, valence, tempo, acousticness, instrumentalness
- `GET /artists/{id}` — genres, popularity, images
- `GET /artists` (batch) — up to 50 artists per call

Client Credentials does NOT require user authorization for these read-only endpoints. It's simpler,
doesn't involve OAuth redirects, and the token auto-refreshes with spotipy's `SpotifyClientCredentials`.

**Confidence:** HIGH — documented Spotify API behavior (Client Credentials covers catalog endpoints).

**Implementation pattern:**
```python
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

sp = Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET
    )
)
```

### Spotify Audio Features — Deprecation Warning

**The `/audio-features` endpoint was deprecated by Spotify in November 2024.**

Spotify announced deprecation of several analysis endpoints including `audio-features` and
`audio-analysis` for new apps and apps that hadn't called them before a cutoff date. Apps that had
previously used these endpoints may retain access, but this is in flux.

**Practical implications for SoundAtlas:**
- If your Spotify developer app previously called `audio-features`, it likely retains access
- If it's a new app created after November 2024, access may be blocked (403 response)
- Build the pipeline to handle graceful degradation: store `null` for audio features if endpoint
  returns 403, and display "audio features unavailable" in the UI rather than failing
- Test endpoint access early in Phase 1 before building the full enrichment pipeline

**Workaround if deprecated for your app:** Audio features (energy, valence, etc.) can be
approximated from playlist/genre data or dropped from v1 scope. The geographic mapping works
without audio features. Prioritize country resolution over audio features.

**Confidence:** MEDIUM — based on training knowledge (Spotify Nov 2024 announcement). Cannot
verify current status without live API call. Flag for validation in Phase 1.

**Batch endpoint:**
```python
# Audio features — batch 100 at a time (max per call)
def get_audio_features_batch(sp: Spotify, track_ids: list[str]) -> list[dict]:
    results = []
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i+100]
        features = sp.audio_features(batch)  # Returns list, None for missing
        results.extend([f for f in features if f is not None])
    return results
```

### MusicBrainz API Integration

**Use `musicbrainzngs` 0.7.1, not raw HTTP.**

musicbrainzngs is the standard Python client. It handles:
- XML parsing (MusicBrainz returns XML by default)
- User-agent header setting (required by MusicBrainz TOS)
- Search and lookup API methods

**Critical: Set User-Agent before any calls:**
```python
import musicbrainzngs

musicbrainzngs.set_useragent(
    "SoundAtlas",
    "1.0",
    "your-email@example.com"  # Required, or requests will be rejected
)
```

**Rate Limiting Strategy:**

MusicBrainz enforces 1 request/second for anonymous clients. Exceeding this results in 503 responses
and potential IP bans. For 3,022 artists this means approximately 50+ minutes of runtime.

```python
import time
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type

@retry(
    wait=wait_fixed(1.1),          # Slightly over 1s to account for clock drift
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(musicbrainzngs.NetworkError),
)
def get_artist_country(artist_name: str) -> str | None:
    results = musicbrainzngs.search_artists(artist=artist_name, limit=1)
    artists = results.get("artist-list", [])
    if not artists:
        return None
    artist = artists[0]
    return artist.get("country")  # ISO 3166-1 alpha-2 code
```

**Checkpointing pattern (critical for 50-minute run):**
- Store resolved countries in PostgreSQL as they are resolved
- Track `enrichment_status` field: `pending | resolved | not_found | error`
- Pipeline is re-runnable: skip artists where `enrichment_status != 'pending'`
- On 503, log and continue to next artist rather than aborting entire run

**Lookup vs Search:**
- Prefer `search_artists` (fuzzy match) over `get_artist_by_id` for initial discovery
- If Spotify artist name is exact, search returns correct result with high score
- For artists with low match scores (<75), flag as `needs_review` rather than storing wrong country

**Confidence:** HIGH — musicbrainzngs behavior is well-documented and stable.

### Mapbox GL JS Data-Driven Circle Markers

**Pattern: GeoJSON source + circle layer with data-driven properties.**

This is the standard Mapbox GL JS approach for the SoundAtlas map. Each country becomes a point
feature with properties like `track_count`, `dominant_genre`, `country_name`.

```typescript
// Add source
map.addSource('countries', {
  type: 'geojson',
  data: {
    type: 'FeatureCollection',
    features: countries.map(c => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [c.longitude, c.latitude]
      },
      properties: {
        country_code: c.iso_alpha2,
        country_name: c.name,
        track_count: c.track_count,
        dominant_genre: c.dominant_genre,
        artist_count: c.artist_count,
      }
    }))
  }
});

// Add circle layer with data-driven radius and color
map.addLayer({
  id: 'country-circles',
  type: 'circle',
  source: 'countries',
  paint: {
    // Size proportional to track count — use interpolate for smooth scaling
    'circle-radius': [
      'interpolate', ['linear'],
      ['get', 'track_count'],
      1, 6,       // 1 track  → 6px radius
      50, 14,     // 50 tracks → 14px radius
      500, 28,    // 500 tracks → 28px radius
      1000, 40    // 1000+ tracks → 40px radius
    ],
    // Color by dominant genre — use match expression
    'circle-color': [
      'match',
      ['get', 'dominant_genre'],
      'hip-hop',   '#8B5CF6',
      'pop',       '#EC4899',
      'rock',      '#F59E0B',
      'electronic','#06B6D4',
      'r-n-b',     '#10B981',
      'latin',     '#F97316',
      'classical', '#6366F1',
      '#64748B'  // default (slate)
    ],
    'circle-opacity': 0.85,
    'circle-stroke-width': 1.5,
    'circle-stroke-color': '#1E293B',
  }
});
```

**Click handler for country detail panel:**
```typescript
map.on('click', 'country-circles', (e) => {
  if (!e.features?.length) return;
  const properties = e.features[0].properties;
  onCountrySelect(properties.country_code);
});

// Change cursor on hover
map.on('mouseenter', 'country-circles', () => {
  map.getCanvas().style.cursor = 'pointer';
});
map.on('mouseleave', 'country-circles', () => {
  map.getCanvas().style.cursor = '';
});
```

**ISO code consistency (critical):** Mapbox GL JS uses ISO 3166-1 alpha-2 codes (2-letter: `US`,
`GB`, `FR`). MusicBrainz also returns ISO 3166-1 alpha-2. The database `country_code` column should
store alpha-2 codes. Do NOT mix alpha-2 and alpha-3 codes — HealthMap's CONCERNS.md documents
exactly this as a fragile area.

**Confidence:** HIGH — mapbox-gl 3.16.0 data-driven styling API is stable and well-documented.

### Audio Feature Radar Chart with Recharts

For the country detail panel's audio feature comparison, use a `RadarChart` from Recharts 3.4.1:

```typescript
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts';

const features = [
  { subject: 'Energy', value: country.avg_energy * 100 },
  { subject: 'Danceability', value: country.avg_danceability * 100 },
  { subject: 'Valence', value: country.avg_valence * 100 },
  { subject: 'Acousticness', value: country.avg_acousticness * 100 },
  { subject: 'Instrumentalness', value: country.avg_instrumentalness * 100 },
];

<ResponsiveContainer width="100%" height={200}>
  <RadarChart data={features}>
    <PolarGrid />
    <PolarAngleAxis dataKey="subject" />
    <Radar dataKey="value" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.4} />
  </RadarChart>
</ResponsiveContainer>
```

**Confidence:** HIGH — Recharts 3.4.1 RadarChart API is stable and matches HealthMap import patterns.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Spotify client | spotipy 2.26.0 | Direct httpx calls | spotipy handles token refresh, retries, batch endpoints; no reason to reinvent |
| MusicBrainz client | musicbrainzngs 0.7.1 | Direct httpx calls | musicbrainzngs handles XML parsing and rate limit headers; same reason |
| MusicBrainz client | musicbrainzngs | brainz (newer library) | `brainz` is not on PyPI; musicbrainzngs is the established standard |
| Auth flow | Client Credentials | Authorization Code | No user login needed; Authorization Code adds OAuth complexity for no benefit |
| Map rendering | mapbox-gl | deck.gl / Leaflet | Must match HealthMap; also Mapbox GL 3.x has better data-driven styling than Leaflet |
| Audio features | Spotify API | Acousticbrainz | Acousticbrainz is **shut down** (closed 2022); Spotify is the only viable source |
| Genre bucketing | Derive from Spotify tags | Last.fm API | Spotify artist metadata already contains genre tags; Last.fm adds complexity |
| Retry logic | tenacity | manual time.sleep loop | tenacity provides exponential backoff, jitter, configurable stop conditions cleanly |

---

## Installation

### Backend (data pipeline)
```bash
pip install \
  spotipy==2.26.0 \
  musicbrainzngs==0.7.1 \
  tenacity==9.1.4 \
  pandas==2.3.2 \
  numpy==2.2.6 \
  tqdm==4.67.3 \
  httpx==0.27.2

# Core backend (match HealthMap)
pip install \
  fastapi==0.115.14 \
  uvicorn[standard]==0.34.3 \
  sqlalchemy==2.0.48 \
  asyncpg==0.29.0 \
  alembic==1.16.5 \
  pydantic==2.11.10 \
  pydantic-settings==2.10.1 \
  python-dotenv==1.1.1 \
  redis==7.4.0 \
  anthropic==0.86.0 \
  python-multipart==0.0.6
```

### Frontend (match HealthMap exactly)
```bash
npx create-next-app@16.2.0 soundatlas-frontend
# Then add domain-specific packages:
npm install mapbox-gl@3.16.0 @types/mapbox-gl@3.4.1
npm install recharts@3.4.1
npm install axios@1.13.2
npm install lucide-react@0.553.0
npm install tailwindcss@4 @tailwindcss/typography@0.5
```

---

## Environment Variables

```bash
# Spotify (required for data pipeline)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# MusicBrainz (no key needed — just set useragent in code)
# MUSICBRAINZ_USERAGENT_EMAIL=your@email.com  # Hardcode in pipeline script

# Database
DATABASE_URL=postgresql+asyncpg://soundatlas_user:soundatlas_password@db:5432/soundatlas_db
POSTGRES_USER=soundatlas_user
POSTGRES_PASSWORD=soundatlas_password
POSTGRES_DB=soundatlas_db

# Redis
REDIS_URL=redis://redis:6379

# Mapbox
NEXT_PUBLIC_MAPBOX_TOKEN=

# Claude API
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-20250514

# App
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
DEBUG=true
```

---

## What NOT to Use

| Library | Why Not |
|---------|---------|
| Acousticbrainz | Shut down by MetaBrainz in 2022. Not accessible. |
| Last.fm API | Adds API key dependency for genre data that Spotify already provides |
| spotipy `Authorization Code Flow` | Requires browser redirect + callback server; unnecessary for offline pipeline |
| `time.sleep()` loops for rate limiting | Use `tenacity` instead; handles retries, backoff, logging cleanly |
| axios in backend (Python) | Use httpx; axios is JavaScript-only |
| `requests` for MusicBrainz | musicbrainzngs wraps requests; using both creates confusion |
| Zustand / Redux | Not in HealthMap; use `useState` + props drilling pattern like HealthMap |
| React Query / SWR | Not in HealthMap; consistency > optimization for personal tool |

---

## Sources

| Source | Confidence | Notes |
|--------|------------|-------|
| HealthMap `requirements.txt` + `package.json` | HIGH | Direct version inspection via codebase map |
| PyPI `pip index versions` | HIGH | All Python versions verified live 2026-03-24 |
| Spotify Developer Docs (training data) | MEDIUM | Audio features deprecation Nov 2024 — verify with live API call in Phase 1 |
| MusicBrainz API docs (training data) | HIGH | 1 req/sec rate limit is well-established |
| musicbrainzngs PyPI metadata | HIGH | Version 0.7.1 confirmed live |
| Mapbox GL JS 3.x docs (training data) | HIGH | Data-driven circle layer API is stable and version-matched to HealthMap |
