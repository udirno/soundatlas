# Phase 3: Backend API - Research

**Researched:** 2026-03-24
**Domain:** FastAPI async REST API / SQLAlchemy 2.0 async ORM / PostgreSQL pg_trgm fuzzy search / Pydantic v2 schemas
**Confidence:** HIGH (stack already established; patterns verified against official docs and Context7)

---

## Summary

The core FastAPI + SQLAlchemy 2.0 async infrastructure was built in Phase 1 and is already in place: `main.py` has the lifespan pattern, `database.py` has `async_sessionmaker` with `expire_on_commit=False`, and `config.py` has `pydantic-settings`. All five ORM models exist (`Country`, `Artist`, `Track`, `UserTrack`, `AIQueryLog`). The pg_trgm extension is created and GIN trigram indexes are already on `artists.name` and `tracks.name`. Phase 3 has no infrastructure to build — it is purely additive: wire Pydantic v2 schemas, add APIRouter modules per domain, write service-layer query functions, and register routers in `main.py`.

The key technical challenges are: (1) structuring SQLAlchemy 2.0 async aggregate queries correctly for country stats (artist count, track count, top genre, audio feature averages); (2) wiring pg_trgm fuzzy search via `func.similarity()` in async SQLAlchemy; (3) calculating the diversity score in Python using a Shannon entropy approach over country distribution; and (4) building the "Not in your library" signal by joining search results against the `user_tracks` table.

The `user_tracks` table is the source of truth for "library membership." A track ID present in `user_tracks` is in the library; absent means it surfaced from a search result but was never imported. The search endpoint must LEFT JOIN (or subquery) against `user_tracks` to attach this boolean signal.

**Primary recommendation:** Use flat service functions per domain (not repository classes), `selectinload()` for all relationship loading, `func.similarity()` + the `%` operator for pg_trgm queries, and Pydantic v2 `model_config = ConfigDict(from_attributes=True)` on all response schemas.

---

## Standard Stack

### Core (already installed — `requirements.txt` in repo)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | Async web framework | Lifespan, DI, Pydantic-native, already present |
| SQLAlchemy | 2.0.35 | ORM + async engine | `create_async_engine`, `AsyncSession`, already present |
| asyncpg | 0.29.0 | PostgreSQL async driver | Only production-grade async PG driver, already present |
| Pydantic | 2.9.0 | Request/response validation | v2 API with `model_config`, `ConfigDict`, already present |
| pydantic-settings | 2.5.0 | Config from .env | Already present |
| uvicorn | 0.30.0 | ASGI server | Already present |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.27.0 | Async HTTP client | AI route stubs that call external APIs in Phase 6 |
| redis | 5.1.0 | Caching | Response caching for expensive aggregations (optional in this phase) |

### No New Dependencies Needed

All required libraries are in `requirements.txt`. Phase 3 adds zero new Python packages. The only additions are Python source files.

**Installation:** Not needed — all packages already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── main.py                    # Already exists — add include_router() calls
├── config.py                  # Already exists
├── database.py                # Already exists
├── models/                    # Already exists (all 5 models)
│   ├── __init__.py
│   ├── country.py
│   ├── artist.py
│   ├── track.py
│   ├── user_track.py
│   └── ai_query_log.py
├── schemas/                   # Currently empty — build out here
│   ├── __init__.py
│   ├── country.py             # CountryListItem, CountryDetail, CountryComparison
│   ├── artist.py              # ArtistListItem, ArtistDetail
│   ├── search.py              # SearchResult, SearchHit
│   ├── analytics.py           # DashboardStats, GenreDistribution, FeatureAverages
│   └── ai.py                  # AIAskRequest, AIAskResponse, AISuggestion
├── api/
│   └── routes/
│       ├── __init__.py        # Already exists
│       ├── countries.py       # GET /api/countries, /api/countries/{id}, /comparison
│       ├── artists.py         # GET /api/artists, /api/artists/{id}
│       ├── search.py          # GET /api/search?q=
│       ├── analytics.py       # GET /api/analytics/dashboard|genres|features
│       └── ai.py              # POST /api/ai/ask, GET /api/ai/suggestions
└── services/                  # Currently empty — business logic lives here
    ├── __init__.py
    ├── country_service.py     # Query functions for country endpoints
    ├── search_service.py      # pg_trgm fuzzy search logic
    └── analytics_service.py   # Aggregation queries, diversity score
```

### Pattern 1: APIRouter per domain, registered in main.py

**What:** Each domain (countries, artists, search, analytics, ai) gets its own `APIRouter` with a prefix and tags. All routers are registered in `main.py` via `include_router()`.

**When to use:** Always for any multi-endpoint FastAPI app. Keeps route files focused and OpenAPI docs organized.

```python
# Source: https://fastapi.tiangolo.com/tutorial/bigger-applications/
# app/api/routes/countries.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app import schemas, services

router = APIRouter(prefix="/api/countries", tags=["countries"])

@router.get("/", response_model=list[schemas.country.CountryListItem])
async def list_countries(db: AsyncSession = Depends(get_db)):
    return await services.country_service.get_country_list(db)

@router.get("/{country_id}", response_model=schemas.country.CountryDetail)
async def get_country(country_id: int, db: AsyncSession = Depends(get_db)):
    return await services.country_service.get_country_detail(db, country_id)
```

```python
# app/main.py — add after middleware setup
from app.api.routes import countries, artists, search, analytics, ai

app.include_router(countries.router)
app.include_router(artists.router)
app.include_router(search.router)
app.include_router(analytics.router)
app.include_router(ai.router)
```

### Pattern 2: Pydantic v2 ORM Schemas with `from_attributes=True`

**What:** All response schemas use `model_config = ConfigDict(from_attributes=True)` so they can be initialized directly from SQLAlchemy ORM objects.

**When to use:** Any schema returned from a route that receives ORM model instances from the database.

```python
# Source: https://docs.pydantic.dev/latest/concepts/models/
# app/schemas/country.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

class CountryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iso_alpha2: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    artist_count: int = 0
    track_count: int = 0
    top_genre: Optional[str] = None

class CountryDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iso_alpha2: str
    artists: list["ArtistListItem"] = []
    genre_breakdown: dict[str, int] = {}
    audio_feature_averages: dict[str, Optional[float]] = {}
```

**Note:** When returning dicts from service functions (for aggregated data), Pydantic v2 accepts dicts natively without `from_attributes`. Use dict returns for aggregated queries; ORM object returns for simple entity fetches.

### Pattern 3: Service Functions (flat, not repository classes)

**What:** `services/country_service.py` contains plain async functions that take `AsyncSession` as a parameter and return dicts or ORM objects. Routes call these functions via dependency injection.

**When to use:** All business logic, all database queries — keep routes as thin HTTP adapters.

```python
# app/services/country_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models import Country, Artist, Track

async def get_country_list(db: AsyncSession) -> list[dict]:
    """Returns all countries with artist count, track count, top genre."""
    stmt = (
        select(
            Country.id,
            Country.name,
            Country.iso_alpha2,
            Country.latitude,
            Country.longitude,
            func.count(Artist.id.distinct()).label("artist_count"),
            func.count(Track.id.distinct()).label("track_count"),
        )
        .outerjoin(Artist, Artist.country_id == Country.id)
        .outerjoin(Track, Track.artist_id == Artist.id)
        .group_by(Country.id)
        .order_by(func.count(Artist.id.distinct()).desc())
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()
    # Top genre requires a separate subquery or Python-side computation
    return [dict(row) for row in rows]
```

### Pattern 4: SQLAlchemy 2.0 Async Aggregate Queries

**What:** Use `select()` with `func.count()`, `func.avg()`, `func.coalesce()`, `group_by()`, and `.label()` for named columns. Execute with `await db.execute(stmt)` and extract with `.mappings().all()` for dict rows.

**When to use:** Any endpoint returning computed stats (country list, analytics dashboard).

```python
# Source: https://docs.sqlalchemy.org/en/20/tutorial/data_select.html
from sqlalchemy import select, func, desc

# Aggregate: artist count and avg audio features per country
stmt = (
    select(
        Country.id,
        Country.name,
        func.count(Artist.id.distinct()).label("artist_count"),
        func.avg(Track.energy).label("avg_energy"),
        func.avg(Track.danceability).label("avg_danceability"),
        func.avg(Track.valence).label("avg_valence"),
    )
    .outerjoin(Artist, Artist.country_id == Country.id)
    .outerjoin(Track, Track.artist_id == Artist.id)
    .where(Country.id == country_id)
    .group_by(Country.id)
)
result = await db.execute(stmt)
row = result.mappings().first()
```

### Pattern 5: selectinload() for Relationship Fetching

**What:** Use `selectinload()` in the options chain when you need to access relationship attributes (e.g., `country.artists` or `artist.tracks`). Never rely on lazy loading in async context — it raises `MissingGreenlet`.

**When to use:** Any query where the route needs to serialize nested objects (e.g., country detail with full artist list).

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.models import Country, Artist

stmt = (
    select(Country)
    .where(Country.id == country_id)
    .options(
        selectinload(Country.artists).selectinload(Artist.tracks)
    )
)
result = await db.execute(stmt)
country = result.scalar_one_or_none()
if country is None:
    raise HTTPException(status_code=404, detail="Country not found")
```

### Pattern 6: pg_trgm Fuzzy Search via func.similarity()

**What:** Use `func.similarity(column, query_string)` from `sqlalchemy.sql.expression.func` to call the PostgreSQL `similarity()` function. Filter with `func.similarity(...) > threshold` and order by descending similarity score.

**When to use:** The `/api/search?q=` endpoint. The GIN trigram indexes on `artists.name` and `tracks.name` (created in Phase 1 migration) make this fast.

```python
# Source: https://www.postgresql.org/docs/current/pgtrgm.html
# + https://github.com/sqlalchemy/sqlalchemy/discussions/7641
from sqlalchemy import select, func, union_all, literal
from app.models import Artist, Track, UserTrack

SIMILARITY_THRESHOLD = 0.2  # Lower than default 0.3 for music names

async def fuzzy_search(db: AsyncSession, q: str, limit: int = 20) -> list[dict]:
    # Artist search
    artist_stmt = (
        select(
            Artist.id,
            Artist.name,
            Artist.spotify_id,
            literal("artist").label("type"),
            func.similarity(Artist.name, q).label("score"),
        )
        .where(func.similarity(Artist.name, q) > SIMILARITY_THRESHOLD)
        .order_by(func.similarity(Artist.name, q).desc())
        .limit(limit)
    )

    # Track search — include "in_library" signal via subquery
    in_library_subq = (
        select(UserTrack.track_id)
        .scalar_subquery()
    )
    track_stmt = (
        select(
            Track.id,
            Track.name,
            Track.spotify_id,
            literal("track").label("type"),
            func.similarity(Track.name, q).label("score"),
            Track.id.in_(in_library_subq).label("in_library"),
        )
        .where(func.similarity(Track.name, q) > SIMILARITY_THRESHOLD)
        .order_by(func.similarity(Track.name, q).desc())
        .limit(limit)
    )

    artist_results = (await db.execute(artist_stmt)).mappings().all()
    track_results = (await db.execute(track_stmt)).mappings().all()
    return [dict(r) for r in artist_results] + [dict(r) for r in track_results]
```

**Note on the `%` operator:** The `%` operator uses the GIN index but returns boolean. `func.similarity() > threshold` also uses the index (GIN optimizes WHERE filters on similarity). Use `func.similarity()` for explicit score control and ordering.

### Pattern 7: Diversity Score Calculation (Python, not SQL)

**What:** The diversity score is the Shannon entropy of the country distribution: how many countries are represented and how evenly spread artists are across them. Compute in Python after fetching country-level artist counts.

**When to use:** `GET /api/analytics/dashboard` response.

```python
# Source: Shannon Diversity Index — https://en.wikipedia.org/wiki/Diversity_index
import math

def calculate_diversity_score(country_artist_counts: list[int]) -> float:
    """
    Shannon entropy-based diversity score.
    Returns 0.0 (all artists same country) to ln(N) (perfectly even distribution).
    Normalized to [0, 1] by dividing by ln(N) where N = number of countries with artists.
    """
    total = sum(country_artist_counts)
    if total == 0:
        return 0.0
    counts = [c for c in country_artist_counts if c > 0]
    n = len(counts)
    if n <= 1:
        return 0.0
    entropy = -sum((c / total) * math.log(c / total) for c in counts)
    max_entropy = math.log(n)  # Perfect evenness
    return round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0
```

### Pattern 8: AI Route Stubs (Phase 3 wires structure, Phase 6 fills logic)

**What:** `POST /api/ai/ask` and `GET /api/ai/suggestions` exist and return valid structured responses. The AI integration (RAG, Anthropic calls) is implemented in Phase 6. Phase 3 stubs return placeholder data with correct schema.

**When to use:** Immediately in Phase 3 — frontend can code against the schema now.

```python
# app/api/routes/ai.py
from fastapi import APIRouter
from app.schemas.ai import AIAskRequest, AIAskResponse, AISuggestion

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/ask", response_model=AIAskResponse)
async def ask_question(request: AIAskRequest):
    # Phase 6 implements actual RAG logic
    return AIAskResponse(
        answer="AI integration coming in Phase 6.",
        sources=[],
        query=request.question,
    )

@router.get("/suggestions", response_model=list[AISuggestion])
async def get_suggestions():
    return [
        AISuggestion(question="Which countries dominate my library?"),
        AISuggestion(question="What's the most represented genre?"),
        AISuggestion(question="Which artists have the highest danceability?"),
    ]
```

### Pattern 9: Top Genre per Country (Python aggregation)

**What:** The `genres` column on `artists` is a PostgreSQL `text[]` array. To find the top genre per country, fetch all artist genres for a country (via `selectinload`), flatten in Python, count occurrences, and return the most common. Do NOT use SQL `unnest()` + `GROUP BY` — it is complex to express in SQLAlchemy async and the dataset is small enough for Python.

**When to use:** `GET /api/countries` top_genre field, `GET /api/countries/{id}` genre_breakdown.

```python
from collections import Counter

def compute_genre_breakdown(artists: list) -> dict[str, int]:
    """Flatten all artist genres arrays and count occurrences."""
    all_genres = []
    for artist in artists:
        if artist.genres:
            all_genres.extend(artist.genres)
    return dict(Counter(all_genres).most_common(10))

def get_top_genre(artists: list) -> str | None:
    breakdown = compute_genre_breakdown(artists)
    return next(iter(breakdown), None)
```

### Anti-Patterns to Avoid

- **Lazy loading relationships in async context:** Accessing `country.artists` without `selectinload()` raises `MissingGreenlet`. Always use `selectinload()` eagerly.
- **Querying N+1 in a loop:** Never execute a DB query inside a `for` loop over ORM objects. Use aggregates or `selectinload()` to batch.
- **Raw string interpolation in SQL:** Never `text(f"WHERE name LIKE '%{q}%'")`. Use `func.similarity()` with bound parameters — asyncpg handles parameterization automatically.
- **Using `session.query()` (legacy API):** Use `select()` from `sqlalchemy` — `session.query()` is the SQLAlchemy 1.x legacy API.
- **Returning ORM objects directly from routes:** FastAPI will try to serialize them; Pydantic v2 needs `from_attributes=True`. Always declare `response_model` explicitly.
- **Omitting `response_model` on routes:** Without it, FastAPI serializes the raw dict/object without validation or OpenAPI docs.
- **Using global mutable state for search threshold:** Set `SIMILARITY_THRESHOLD` as a module constant; don't mutate `pg_trgm.similarity_threshold` via SQL `SET` inside routes (it's session-scoped and thread-unsafe in async).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy text matching | Custom Levenshtein loop | `func.similarity()` + pg_trgm GIN index | Native C-level Postgres implementation; already indexed |
| JSON Schema / API docs | Manual OpenAPI spec | FastAPI's auto-generated OpenAPI from response_model | Always in sync with code |
| Request validation | Manual `if` checks in routes | Pydantic v2 schema on route parameter | Type coercion, error messages, docs generation |
| Connection pool management | Custom pool | SQLAlchemy `create_async_engine` with pool_pre_ping | Handles reconnect, pool overflow, checkout timeout |
| Genre array unnesting + count | Complex SQL unnest | Python `Counter` on `artist.genres` list | Simpler, testable, adequate for library-scale data |
| Diversity score | Third-party metrics lib | Python `math.log()` implementation | 10 lines; no dependency; exact control |

**Key insight:** pg_trgm does the heavy lifting for search. SQLAlchemy handles all connection lifecycle and query building. Don't solve problems that are already solved by the installed stack.

---

## Common Pitfalls

### Pitfall 1: Lazy Loading in Async Context (MissingGreenlet)

**What goes wrong:** `await country.artists` fails with `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.`

**Why it happens:** SQLAlchemy async does not support implicit lazy loading. Accessing a relationship attribute that wasn't eagerly loaded triggers a synchronous DB call which can't run in the async context.

**How to avoid:** Use `selectinload()` in every query that will access relationship attributes:
```python
stmt = select(Country).options(selectinload(Country.artists)).where(...)
```

**Warning signs:** `MissingGreenlet` traceback at runtime during route execution; no error at definition time.

### Pitfall 2: func.similarity() Threshold Tuning for Music Names

**What goes wrong:** Search for "The Weeknd" returns nothing; search for "Weeknd" returns it. Short names and "The/A" prefixes confuse trigram similarity.

**Why it happens:** Default threshold is 0.3. Short strings (3-4 chars) have very few trigrams, making similarity scores low even for correct matches.

**How to avoid:** Use a lower threshold (0.15–0.2) for the search endpoint, and additionally use `word_similarity()` for partial word matching. Order results by score descending so best matches surface first regardless of threshold.

**Warning signs:** User reports no results for obvious queries; searching for known artist names returns nothing.

### Pitfall 3: Artist.genres is a PostgreSQL Array — Not a Python List Until Loaded

**What goes wrong:** `artist.genres` returns `None` or fails with a type error when iterating.

**Why it happens:** `ARRAY(Text)` PostgreSQL columns map to Python lists via asyncpg, but are `None` when the column is `NULL` (not an empty array). Code that does `for g in artist.genres` fails on NULL rows.

**How to avoid:** Always guard: `if artist.genres:` before iterating. Never assume empty list; always use `artist.genres or []`.

**Warning signs:** `TypeError: 'NoneType' object is not iterable` in genre computation code.

### Pitfall 4: "Not in Your Library" Signal — Must Join Against user_tracks

**What goes wrong:** Search returns tracks but front-end has no way to distinguish "in library" vs. "discovered via search."

**Why it happens:** The requirement says search must include a `not_in_library` boolean signal. This requires checking the `user_tracks` table for each search result.

**How to avoid:** The search query must include a subquery or LEFT JOIN against `user_tracks`:
```python
# EXISTS subquery approach
in_library_subq = (
    select(literal(1))
    .where(UserTrack.track_id == Track.id)
    .exists()
    .correlate(Track)
)
```
Don't use a Python-level lookup loop after the query — do it in the SQL for performance.

**Warning signs:** Frontend shows all search results identically; no library membership indicator.

### Pitfall 5: Audio Feature Averages with All-NULL Columns

**What goes wrong:** `func.avg(Track.energy)` returns `None` for all rows when audio features weren't collected (Phase 1 decision: nullable columns when 403 from Spotify).

**Why it happens:** `AVG()` of NULL values returns NULL in PostgreSQL. Routes that serialize `None` into the response need explicit Pydantic `Optional[float]` fields.

**How to avoid:** All audio feature average fields in schemas must be `Optional[float] = None`. Routes must not raise 500 when averages are all NULL.

**Warning signs:** Response serialization errors when all tracks have NULL audio features; Pydantic validation errors about `None` in non-optional fields.

### Pitfall 6: Top Genre Computation Requires artists with genres Loaded

**What goes wrong:** `get_country_list()` returns empty `top_genre` for all countries.

**Why it happens:** The country list query uses aggregates that don't fetch artist genres. Computing top genre in Python requires the genres array data.

**How to avoid:** Either (a) compute top genre in a separate query per country (N+1 — avoid), or (b) use a single SQL query with `unnest()` and `mode()`, or (c) use Python post-processing after loading countries with `selectinload(Country.artists)`. Option (c) is simplest for library-scale data. For the list endpoint with potentially 193+ countries, consider option (b) via `text()` with raw SQL if performance is needed.

**Warning signs:** `top_genre` is always `None` in country list response despite seeded artist data.

### Pitfall 7: Route Prefix Conflicts Between APIRouter and include_router

**What goes wrong:** Routes register under double prefix like `/api/api/countries`.

**Why it happens:** If APIRouter has `prefix="/api/countries"` AND `include_router` is called with `prefix="/api"`, the prefixes stack.

**How to avoid:** Set the full prefix on the router (`prefix="/api/countries"`) and use `include_router` without an additional prefix:
```python
app.include_router(countries.router)  # No extra prefix here
```

**Warning signs:** Routes appear in OpenAPI docs with doubled path segments; all routes return 404.

---

## Code Examples

Verified patterns from official sources:

### Full Country List Query with Aggregates

```python
# Source: https://docs.sqlalchemy.org/en/20/tutorial/data_select.html
# app/services/country_service.py
from sqlalchemy import select, func, outerjoin
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Country, Artist, Track

async def get_country_list(db: AsyncSession) -> list[dict]:
    stmt = (
        select(
            Country.id,
            Country.name,
            Country.iso_alpha2,
            Country.latitude,
            Country.longitude,
            func.count(Artist.id.distinct()).label("artist_count"),
            func.count(Track.id.distinct()).label("track_count"),
        )
        .outerjoin(Artist, Artist.country_id == Country.id)
        .outerjoin(Track, Track.artist_id == Artist.id)
        .group_by(Country.id, Country.name, Country.iso_alpha2, Country.latitude, Country.longitude)
        .order_by(func.count(Artist.id.distinct()).desc())
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()
    return [dict(r) for r in rows]
```

### Country Detail with Artists and Genre Breakdown

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html (selectinload pattern)
from sqlalchemy.orm import selectinload

async def get_country_detail(db: AsyncSession, country_id: int) -> dict | None:
    stmt = (
        select(Country)
        .where(Country.id == country_id)
        .options(
            selectinload(Country.artists).selectinload(Artist.tracks)
        )
    )
    result = await db.execute(stmt)
    country = result.scalar_one_or_none()
    if country is None:
        return None

    genre_breakdown = compute_genre_breakdown(country.artists)

    # Audio feature averages — handle all-NULL gracefully
    all_tracks = [t for a in country.artists for t in a.tracks]
    def safe_avg(values):
        vals = [v for v in values if v is not None]
        return sum(vals) / len(vals) if vals else None

    audio_averages = {
        "energy": safe_avg([t.energy for t in all_tracks]),
        "danceability": safe_avg([t.danceability for t in all_tracks]),
        "valence": safe_avg([t.valence for t in all_tracks]),
        "tempo": safe_avg([t.tempo for t in all_tracks]),
        "acousticness": safe_avg([t.acousticness for t in all_tracks]),
    }

    return {
        "id": country.id,
        "name": country.name,
        "iso_alpha2": country.iso_alpha2,
        "artists": country.artists,
        "genre_breakdown": genre_breakdown,
        "audio_feature_averages": audio_averages,
    }
```

### Global Audio Feature Averages (for comparison endpoint)

```python
# Source: https://docs.sqlalchemy.org/en/20/tutorial/data_select.html
async def get_global_audio_averages(db: AsyncSession) -> dict:
    stmt = select(
        func.avg(Track.energy).label("energy"),
        func.avg(Track.danceability).label("danceability"),
        func.avg(Track.valence).label("valence"),
        func.avg(Track.tempo).label("tempo"),
        func.avg(Track.acousticness).label("acousticness"),
    )
    result = await db.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else {}
```

### pg_trgm Fuzzy Search

```python
# Source: https://www.postgresql.org/docs/current/pgtrgm.html
# + https://docs.sqlalchemy.org/en/20/core/functions.html
from sqlalchemy import select, func, literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Artist, Track, UserTrack

SEARCH_THRESHOLD = 0.2

async def fuzzy_search(db: AsyncSession, q: str, limit: int = 20) -> dict:
    # Artists
    artist_stmt = (
        select(
            Artist.id,
            Artist.name,
            Artist.spotify_id,
            Artist.genres,
            Artist.image_url,
            func.similarity(Artist.name, q).label("score"),
        )
        .where(func.similarity(Artist.name, q) > SEARCH_THRESHOLD)
        .order_by(func.similarity(Artist.name, q).desc())
        .limit(limit)
    )
    artist_rows = (await db.execute(artist_stmt)).mappings().all()

    # Tracks — with "in_library" signal
    track_stmt = (
        select(
            Track.id,
            Track.name,
            Track.spotify_id,
            Track.album_name,
            func.similarity(Track.name, q).label("score"),
            select(literal(True))
            .where(UserTrack.track_id == Track.id)
            .exists()
            .label("in_library"),
        )
        .where(func.similarity(Track.name, q) > SEARCH_THRESHOLD)
        .order_by(func.similarity(Track.name, q).desc())
        .limit(limit)
    )
    track_rows = (await db.execute(track_stmt)).mappings().all()

    return {
        "artists": [dict(r) for r in artist_rows],
        "tracks": [dict(r) for r in track_rows],
        "query": q,
    }
```

### Analytics Dashboard — Global Stats

```python
# app/services/analytics_service.py
from sqlalchemy import select, func, distinct
from app.models import Country, Artist, Track, UserTrack
import math

async def get_dashboard_stats(db: AsyncSession) -> dict:
    # Counts
    counts_stmt = select(
        func.count(distinct(Country.id)).label("country_count"),
        func.count(distinct(Artist.id)).label("artist_count"),
        func.count(distinct(Track.id)).label("track_count"),
    ).select_from(Country).outerjoin(Artist, Artist.country_id == Country.id).outerjoin(Track, Track.artist_id == Artist.id)
    counts = (await db.execute(counts_stmt)).mappings().first()

    # Per-country artist counts for diversity score
    per_country_stmt = (
        select(func.count(Artist.id).label("cnt"))
        .where(Artist.country_id.is_not(None))
        .group_by(Artist.country_id)
    )
    per_country = (await db.execute(per_country_stmt)).scalars().all()
    diversity_score = calculate_diversity_score(list(per_country))

    return {
        **dict(counts),
        "diversity_score": diversity_score,
    }
```

### Wiring Routers in main.py

```python
# Source: https://fastapi.tiangolo.com/tutorial/bigger-applications/
# app/main.py — additions to existing file
from app.api.routes import countries, artists, search, analytics, ai

# After middleware setup, before existing routes:
app.include_router(countries.router)
app.include_router(artists.router)
app.include_router(search.router)
app.include_router(analytics.router)
app.include_router(ai.router)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `orm_mode = True` in Pydantic Config | `model_config = ConfigDict(from_attributes=True)` | Pydantic v2 (2023) | Old syntax raises deprecation warning; breaks in strict mode |
| `session.query(Model).filter(...)` | `select(Model).where(...)` | SQLAlchemy 2.0 (2023) | Legacy API still works but not recommended |
| `async_scoped_session` | `async_sessionmaker` + DI | SQLAlchemy 2.0 | Cleaner per-request lifecycle |
| `@app.on_event("startup")` | `@asynccontextmanager` lifespan | FastAPI 0.93 | Already using lifespan in main.py |
| Lazy loading relationships | `selectinload()` / `joinedload()` | Required in async context | Lazy load raises MissingGreenlet in async |
| `set_limit(0.5)` for pg_trgm | `SET pg_trgm.similarity_threshold = 0.5` | PostgreSQL 9.6+ | Function-based approach deprecated |

**Deprecated/outdated:**

- `orm_mode = True`: Use `model_config = ConfigDict(from_attributes=True)` in Pydantic v2.
- `session.query()`: Use `select()` with `await db.execute()`.
- `AsyncSession.run_sync()` for simple queries: Only needed for complex introspection; avoid for ordinary CRUD.

---

## Open Questions

1. **Top genre for country list: SQL or Python?**
   - What we know: `genres` is a `text[]` array. Getting top genre in SQL requires `unnest()` + `mode()` or a subquery. Python approach needs loading all artists.
   - What's unclear: Performance at 193+ countries with full artist load vs. SQL unnest complexity.
   - Recommendation: Start with Python post-processing using `selectinload`. If the country list endpoint is slow (>200ms), add a SQL `unnest()` query. For SoundAtlas scale (personal library), Python is fine.

2. **Search threshold: 0.2 or lower for music names?**
   - What we know: Default pg_trgm threshold is 0.3. Short artist names (3-4 chars) score low even for correct matches.
   - What's unclear: Exact threshold that balances recall (finding real matches) vs. precision (not returning garbage).
   - Recommendation: Start at 0.2 for both artists and tracks. Add `word_similarity()` as a fallback for names that fail `similarity()`. Expose threshold as a config constant so it can be tuned without code changes.

3. **Comparison endpoint: what constitutes "global" averages?**
   - What we know: `GET /api/countries/{id}/comparison` needs country audio feature averages vs. global averages. Global could mean (a) all tracks in DB, or (b) only tracks in `user_tracks`.
   - What's unclear: Which definition matches HealthMap's intent for the comparison.
   - Recommendation: Use all tracks in the DB as "global" — this gives a stable reference baseline regardless of library size.

4. **Analytics genre endpoint: per-country genre distribution needs unnest**
   - What we know: `GET /api/analytics/genres` should return genre distribution globally AND per country. Global requires unnesting all artist genres arrays.
   - What's unclear: Whether SQLAlchemy's `func.unnest()` works cleanly in async context or if raw `text()` SQL is needed.
   - Recommendation: Use `text()` with a raw SQL query for the unnest+count operation — it's a single read query and raw SQL is explicit about what's happening:
     ```python
     stmt = text("""
         SELECT unnest(genres) AS genre, COUNT(*) AS count
         FROM artists
         WHERE genres IS NOT NULL
         GROUP BY genre
         ORDER BY count DESC
         LIMIT 20
     """)
     result = await db.execute(stmt)
     ```

---

## Sources

### Primary (HIGH confidence)

- SQLAlchemy 2.0 Official Docs — https://docs.sqlalchemy.org/en/20/tutorial/data_select.html — aggregate query patterns (`func.count`, `func.avg`, `group_by`, `scalar_subquery`)
- SQLAlchemy 2.0 Async Docs — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html — `selectinload` as recommended eager loading strategy, `AsyncSession` constraints
- FastAPI Official Docs — https://fastapi.tiangolo.com/tutorial/bigger-applications/ — `APIRouter`, `include_router`, prefix/tags pattern
- FastAPI Official Docs — https://fastapi.tiangolo.com/tutorial/response-model/ — `response_model`, `response_model_exclude_unset`, type annotation patterns
- PostgreSQL Official Docs — https://www.postgresql.org/docs/current/pgtrgm.html — `similarity()` function, threshold GUC, GIN vs GiST indexes, operator list

### Secondary (MEDIUM confidence)

- zhanymkanov/fastapi-best-practices — https://github.com/zhanymkanov/fastapi-best-practices — project structure by domain, service layer, async dependency patterns (cross-verified with FastAPI official docs)
- FastAPI SQLAlchemy 2.0 production article — https://dev-faizan.medium.com/fastapi-sqlalchemy-2-0-modern-async-database-patterns-7879d39b6843 — async DI patterns (verified against SQLAlchemy docs)
- SQLAlchemy pg_trgm discussion — https://github.com/sqlalchemy/sqlalchemy/discussions/7641 — `func.similarity()` usage with SQLAlchemy expressions
- Shannon Diversity Index — https://en.wikipedia.org/wiki/Diversity_index — formula and normalization approach

### Tertiary (LOW confidence)

- FastAPI production patterns — https://orchestrator.dev/blog/2025-1-30-fastapi-production-patterns/ — service layer architecture (single source, not verified against official docs; treat as supplementary)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages already installed and verified in Phase 1; versions locked in requirements.txt
- Architecture (APIRouter, service layer): HIGH — verified against FastAPI official docs
- SQLAlchemy async patterns (selectinload, aggregate): HIGH — verified against official SQLAlchemy 2.0 docs
- pg_trgm patterns: HIGH — verified against official PostgreSQL docs; GIN indexes already exist from Phase 1 migration
- Diversity score formula: MEDIUM — Shannon entropy is well-established; normalization approach is standard ecology/information theory
- Search threshold value: LOW — 0.2 is a reasonable starting point but must be empirically tuned against actual library data
- top_genre via Python unnest: MEDIUM — standard Python Counter pattern; performance assumption may not hold at large scale

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days — stable stack; all packages pinned; no moving targets)
