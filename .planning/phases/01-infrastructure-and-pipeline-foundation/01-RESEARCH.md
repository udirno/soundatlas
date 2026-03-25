# Phase 1: Infrastructure and Pipeline Foundation - Research

**Researched:** 2026-03-24
**Domain:** Docker Compose / PostgreSQL / FastAPI / Python pipeline scripting / Spotify API
**Confidence:** HIGH (stack decisions verified; Spotify endpoint status confirmed with official source)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Database schema design
- Seed countries table with all UN-recognized countries (~193) — comprehensive world coverage even for countries with zero artists
- Audio features stored as nullable float columns directly on the tracks table (energy, danceability, valence, tempo, etc.) — no separate table
- Artist genres stored as PostgreSQL text[] array column on artists table — no separate genres/join table
- user_tracks table is minimal: track IDs, artist FK, and timestamps only — no play count or extra metadata

#### Docker environment layout
- Single docker-compose.yml file — no base/override split, dev-only project
- Pipeline scripts run on the host machine (not in Docker), connecting to PostgreSQL in Docker
- PostgreSQL data persists via named Docker volume — survives `docker compose down`/up cycles
- Standard port mapping: PostgreSQL 5432, Redis 6379, FastAPI 8000, Next.js 3000

#### Spotify export parsing
- Parser built as an importable Python module — Phase 2 enrichment scripts can import and reuse it
- Input path provided via CLI argument or environment variable (not hardcoded)
- Malformed entries (missing artist name, no Spotify ID) are skipped with a logged warning — don't block the parse
- Deduplication happens during parsing — same Spotify track ID appearing multiple times keeps first occurrence only

#### Audio features validation
- Standalone validation script separate from the parser — run independently to test endpoint access
- Uses a real track ID extracted from the user's YourLibrary.json export — proves the full flow works
- Single track test is sufficient — no batch testing needed in validation
- On 403 result, writes a config file flag (e.g., AUDIO_FEATURES_AVAILABLE=false) that Phase 2 reads to decide whether to skip audio features enrichment

### Claude's Discretion
- Exact database migration tool/approach
- Docker healthcheck configuration
- Python project structure and dependency management
- Logging format and verbosity levels
- Error handling patterns within scripts

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

This phase establishes the full development environment from scratch: Docker Compose services, PostgreSQL schema with seeded reference data, and two host-side Python pipeline scripts. The technical domains span Docker Compose service orchestration, async FastAPI/SQLAlchemy stack, Alembic migrations, and Python scripting against a Spotify data export.

The most time-sensitive finding is that **Spotify's audio features endpoint (`/v1/audio-features`) has been definitively restricted since November 27, 2024** for all apps registered after that date. This is confirmed via Spotify's official developer blog. The validation script must treat 403 as the expected outcome for newly registered apps and write a flag file accordingly. The rest of the pipeline (schema with nullable float columns) is designed to tolerate this regardless of result.

For the Python tooling, **uv** is the current standard for Python dependency management (replacing pip/pip-tools), and **pydantic-settings** with `BaseSettings` + `model_config` is the modern approach for `.env` loading in FastAPI — replacing the older `load_dotenv()` pattern. Alembic initialized with `-t async` is the right choice for async SQLAlchemy 2.0 + asyncpg migrations.

**Primary recommendation:** Use uv for Python package management, Alembic (`-t async`) for migrations, pydantic-settings for config, and design the Spotify validation script to treat 403 as a known success case with graceful fallback flag.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | latest (0.115+) | Async web framework | lifespan pattern, DI, pydantic-native |
| SQLAlchemy | 2.0+ | ORM + async engine | `create_async_engine`, `AsyncSession`, `async_sessionmaker` |
| asyncpg | 0.29.x | PostgreSQL async driver | Only production-grade async PG driver |
| Alembic | latest (1.13+) | Schema migrations | `-t async` template, autogenerate support |
| pydantic-settings | 2.x | `.env` loading + settings | `BaseSettings` + `model_config`, cached via `@lru_cache` |
| redis-py | 5.x | Redis client (async) | `redis.asyncio` module, standard FastAPI pairing |
| uv | latest | Python package management | 100x faster than pip, pyproject.toml + uv.lock |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| spotipy | 2.23+ | Spotify API client | Audio features validation script |
| pycountry | 24.x | ISO country data (alpha-2, name) | Countries seed data — provides alpha-2 codes and names |
| python-dotenv | 1.x | Fallback .env loading for scripts | Host-side pipeline scripts that don't use pydantic-settings |
| uvicorn | 0.30+ | ASGI server | FastAPI runtime inside Docker |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv | pip + virtualenv | pip is slower, no lock file native — uv is the 2025 standard |
| pydantic-settings | load_dotenv() directly | load_dotenv is an anti-pattern in FastAPI — no type safety, no caching |
| Alembic | SQLAlchemy `create_all()` | `create_all` can't do incremental migrations — use Alembic |
| asyncpg | psycopg3 async | Both valid; asyncpg more established in FastAPI ecosystem |
| pycountry + gavinr/world-countries-centroids | restcountries API | API adds network dependency at seed time; static CSV is reliable |

**Installation (backend):**
```bash
uv add fastapi uvicorn sqlalchemy asyncpg alembic pydantic-settings redis
uv add --dev pytest httpx
```

**Installation (pipeline scripts):**
```bash
uv add spotipy pycountry python-dotenv
```

---

## Architecture Patterns

### Recommended Project Structure
```
soundatlas/
├── docker-compose.yml          # Single file, all 4 services
├── .env                        # Gitignored, all secrets
├── .env.example                # Committed, shows required keys
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml          # uv-managed dependencies
│   ├── alembic/
│   │   ├── env.py              # Async-configured env
│   │   └── versions/           # Migration files
│   └── app/
│       ├── main.py             # FastAPI app + lifespan
│       ├── config.py           # pydantic-settings Settings class
│       ├── database.py         # engine, AsyncSessionLocal, get_db
│       └── models/             # SQLAlchemy ORM models
├── frontend/
│   ├── Dockerfile
│   └── ...                     # Next.js app
└── pipeline/
    ├── pyproject.toml          # Separate uv project for scripts
    ├── parse_library.py        # Importable parser module (PIPE-01)
    └── validate_audio_features.py  # Validation script (PIPE-06)
```

### Pattern 1: FastAPI Lifespan with Async SQLAlchemy
**What:** Initialize DB engine and Redis at app startup, dispose on shutdown. Store in `app.state`.
**When to use:** Any app-wide resource that should live for the full process lifetime.

```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    app.state.async_session = async_sessionmaker(
        app.state.engine,
        expire_on_commit=False,
    )
    app.state.redis = await aioredis.from_url(settings.REDIS_URL)
    yield
    # Shutdown
    await app.state.redis.close()
    await app.state.engine.dispose()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Async Session Dependency Injection
**What:** Yield a fresh `AsyncSession` per request, commit/rollback automatically.
**When to use:** All database-touching route handlers.

```python
# Source: https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# In routes:
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    ...
```

### Pattern 3: Pydantic Settings for .env Loading
**What:** Type-safe config loaded once from `.env`, cached with `@lru_cache`.
**When to use:** All configuration in the FastAPI backend.

```python
# Source: https://fastapi.tiangolo.com/advanced/settings/
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

### Pattern 4: Alembic Async Initialization
**What:** Initialize Alembic with the async template so env.py handles asyncpg correctly.
**When to use:** Any project using async SQLAlchemy with asyncpg.

```bash
# Source: https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/
alembic init -t async alembic
```

The generated `env.py` already includes an async `run_migrations_online()` function. Set `target_metadata = Base.metadata` and configure the URL from settings:
```python
# In alembic/env.py
from app.config import settings
from app.models import Base

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

### Pattern 5: Docker Healthchecks with `depends_on`
**What:** PostgreSQL and Redis health gates prevent FastAPI from starting before they're ready.
**When to use:** Always — eliminates retry loops in application startup code.

```yaml
# Source: https://last9.io/blog/docker-compose-health-checks/
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  backend:
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

### Pattern 6: Importable Parser Module with CLI Entrypoint
**What:** `parse_library.py` exposes a `parse_liked_tracks(path)` function AND a `__main__` block for CLI use.
**When to use:** Phase 1 parser must be importable by Phase 2 enrichment scripts (locked decision).

```python
# pipeline/parse_library.py
import json
import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def parse_liked_tracks(export_path: str | Path) -> list[dict]:
    """
    Parse YourLibrary.json and return deduplicated liked tracks.
    Returns list of dicts with keys: spotify_id, name, artist_name, artist_uri
    Skips malformed entries with logged warnings.
    """
    with open(export_path) as f:
        data = json.load(f)

    tracks = data.get("tracks", [])
    seen_ids = set()
    results = []

    for entry in tracks:
        uri = entry.get("uri", "")
        artist_name = entry.get("artist", "")

        if not uri or not artist_name:
            logger.warning("Skipping malformed entry: %s", entry)
            continue

        # Extract track ID from URI (format: "spotify:track:<id>")
        parts = uri.split(":")
        if len(parts) != 3 or parts[1] != "track":
            logger.warning("Skipping entry with unexpected URI format: %s", uri)
            continue

        spotify_id = parts[2]
        if spotify_id in seen_ids:
            continue  # Deduplicate by track ID, keep first occurrence
        seen_ids.add(spotify_id)

        results.append({
            "spotify_id": spotify_id,
            "name": entry.get("track", ""),
            "artist_name": artist_name,
            "album_name": entry.get("album", ""),
        })

    logger.info("Parsed %d unique liked tracks", len(results))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=None, help="Path to YourLibrary.json")
    args = parser.parse_args()

    import os
    path = args.path or os.environ.get("SPOTIFY_EXPORT_PATH", "YourLibrary.json")
    tracks = parse_liked_tracks(path)
    print(f"Found {len(tracks)} liked tracks")
```

### Anti-Patterns to Avoid
- **Using `@app.on_event("startup")`:** Deprecated since FastAPI 0.93. Use `lifespan` context manager instead.
- **Global engine at module level:** Engine created at import time ignores lifespan management — can't be tested cleanly.
- **Hardcoded secrets anywhere:** No `.env` values in any `.py` or `.yml` file — only in `.env` (gitignored).
- **`alembic init` without `-t async`:** Default template uses sync driver; requires manual env.py rewrite for asyncpg.
- **`docker compose up` without healthchecks:** FastAPI may start before PostgreSQL is ready, causing connection errors on startup.
- **Running Alembic inside Docker CMD:** Migrations should run from host or a separate init container, not baked into the main service CMD for dev projects.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database migrations | Custom SQL files + apply script | Alembic | Handles ordering, rollbacks, autogenerate, concurrent safety |
| Settings from .env | `os.getenv()` calls scattered everywhere | pydantic-settings `BaseSettings` | Type validation, defaults, caching, test overrides |
| Service startup ordering | Sleep loops / retry in app code | Docker healthchecks + `depends_on` | Docker manages this at the compose level |
| Countries data | Scraping Wikipedia / manual CSV | pycountry + world-countries-centroids CSV | ISO standard, maintained, covers 249 countries |
| Spotify API auth | Manual OAuth token management | spotipy `SpotifyClientCredentials` | Handles token refresh, retry, and rate limit headers |
| JSON field extraction | Regex on raw JSON | `json.load()` + dict access with `.get()` | Reliable, handles encoding, no off-by-one risks |

**Key insight:** Every problem in this phase has a mature library. The only custom code should be: the `parse_liked_tracks()` function, the SQLAlchemy models, and the validation logic for the audio features 403 path.

---

## Common Pitfalls

### Pitfall 1: Audio Features Returns 403 For All New Apps
**What goes wrong:** Validation script gets 403 and developer thinks the code is broken.
**Why it happens:** Spotify restricted `/v1/audio-features` on November 27, 2024 for all apps registered after that date. This is permanent and expected.
**How to avoid:** Validation script must treat 403 as a handled outcome — write `AUDIO_FEATURES_AVAILABLE=false` to a `.pipeline_config` file and exit with code 0. Phase 2 will read this flag.
**Warning signs:** Any `SpotifyException` with `http_status=403` on the audio features call.

### Pitfall 2: Alembic Can't Connect to asyncpg Without `-t async` Template
**What goes wrong:** `alembic revision --autogenerate` or `alembic upgrade head` fails with async/event loop errors.
**Why it happens:** Default `alembic init` generates a sync `env.py` that can't run with `postgresql+asyncpg://` URL.
**How to avoid:** Always init with `alembic init -t async alembic`. The generated env.py includes a proper `run_migrations_online()` for async.
**Warning signs:** `RuntimeError: no running event loop` or `asyncpg: cannot reuse connection` during migration runs.

### Pitfall 3: Pipeline Scripts Can't Connect to Dockerized PostgreSQL
**What goes wrong:** `psycopg2.OperationalError: could not connect to server` from host machine.
**Why it happens:** Scripts running on the host connect to `localhost:5432`, which works only if Docker port mapping is `5432:5432`. Connection string must use `localhost`, not `postgres` (the Docker service name).
**How to avoid:** Use two DATABASE_URL variants in `.env`:
  - `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/soundatlas` (host scripts)
  - `DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/soundatlas` (FastAPI inside Docker)
  Or use a single `DATABASE_URL` env var that host scripts and Docker can both see via the host network.
**Warning signs:** Connection refused on port 5432 from scripts; works fine from inside Docker.

### Pitfall 4: YourLibrary.json tracks Array Uses `"artist"` Not `"artists"`
**What goes wrong:** Parser produces zero results because it reads the wrong field name.
**Why it happens:** The personal data export format uses flat field names (`"artist"`, `"track"`, `"album"`) not the API response nested objects (`"artists": [{...}]`). These are different schemas.
**How to avoid:** The personal data export structure is:
  ```json
  {
    "tracks": [
      {"artist": "Artist Name", "album": "Album Name", "track": "Track Name", "uri": "spotify:track:ID"}
    ]
  }
  ```
  Use `entry.get("artist")` not `entry.get("artists", [{}])[0].get("name")`.
**Warning signs:** Empty parse results, no warnings logged.

### Pitfall 5: `expire_on_commit=True` Breaks Async SQLAlchemy Access Post-Commit
**What goes wrong:** Accessing model attributes after `session.commit()` raises `MissingGreenlet` or lazy load errors.
**Why it happens:** SQLAlchemy's default `expire_on_commit=True` tries to lazy-load expired attributes, which requires a sync greenlet in async context.
**How to avoid:** Always set `expire_on_commit=False` in `async_sessionmaker`:
  ```python
  async_sessionmaker(engine, expire_on_commit=False)
  ```
**Warning signs:** `sqlalchemy.exc.MissingGreenlet` after commit inside async route.

### Pitfall 6: pg_trgm Extension Must Be Created Before Migrations Use It
**What goes wrong:** Alembic migration fails because `CREATE INDEX USING GIN (column gin_trgm_ops)` requires `pg_trgm` to exist first.
**Why it happens:** Extension creation must happen before any index using it.
**How to avoid:** Put `CREATE EXTENSION IF NOT EXISTS pg_trgm;` in the first migration file (or in a PostgreSQL init script via `/docker-entrypoint-initdb.d/`). Using `IF NOT EXISTS` makes it idempotent.
**Warning signs:** `ERROR: operator class "gin_trgm_ops" does not exist` during migration.

### Pitfall 7: Named Volume Not Declared in Top-Level `volumes`
**What goes wrong:** `docker compose up` fails with `volume 'postgres_data' declared as external, but could not be found`.
**Why it happens:** Docker Compose requires named volumes to be declared under the top-level `volumes:` key.
**How to avoid:** Always declare named volumes at the top level:
  ```yaml
  volumes:
    postgres_data:
  ```
**Warning signs:** Docker Compose error on first `up`, before any container starts.

---

## Code Examples

Verified patterns from official/authoritative sources:

### Docker Compose: Full Service Block with Healthchecks
```yaml
# Source: https://last9.io/blog/docker-compose-health-checks/
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    env_file: .env

volumes:
  postgres_data:
```

### SQLAlchemy Model Base with Naming Conventions
```python
# Source: https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
```

### Countries Seed Script
```python
# pycountry provides alpha_2 and name; centroid CSV provides lat/lon
# Source: https://pypi.org/project/pycountry/ + https://github.com/gavinr/world-countries-centroids
import pycountry
import csv
import psycopg2

# Load centroids from gavinr/world-countries-centroids CSV (fields: COUNTRY, ISO, longitude, latitude)
centroids = {}
with open("world-countries-centroids.csv") as f:
    for row in csv.DictReader(f):
        centroids[row["ISO"]] = (float(row["latitude"]), float(row["longitude"]))

# Seed table
conn = psycopg2.connect(...)
for country in pycountry.countries:
    lat, lon = centroids.get(country.alpha_2, (None, None))
    conn.execute(
        "INSERT INTO countries (name, iso_alpha2, latitude, longitude) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (country.name, country.alpha_2, lat, lon)
    )
conn.commit()
```

### Audio Features Validation Script
```python
# pipeline/validate_audio_features.py
# Source patterns: https://spotipy.readthedocs.io/ + locked decisions
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from parse_library import parse_liked_tracks
import logging

logger = logging.getLogger(__name__)

def validate_audio_features(export_path: str, config_output_path: str = ".pipeline_config") -> bool:
    tracks = parse_liked_tracks(export_path)
    if not tracks:
        logger.error("No tracks found in export — cannot validate")
        return False

    test_track_id = tracks[0]["spotify_id"]

    sp = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        )
    )

    try:
        result = sp.audio_features([test_track_id])
        available = result is not None and result[0] is not None
    except spotipy.SpotifyException as e:
        if e.http_status == 403:
            logger.warning("Audio features endpoint returned 403 — restricted for this app registration")
            available = False
        else:
            raise

    flag_value = "true" if available else "false"
    with open(config_output_path, "w") as f:
        f.write(f"AUDIO_FEATURES_AVAILABLE={flag_value}\n")

    logger.info("Audio features available: %s (written to %s)", available, config_output_path)
    return available


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=os.environ.get("SPOTIFY_EXPORT_PATH", "YourLibrary.json"))
    parser.add_argument("--output", default=".pipeline_config")
    args = parser.parse_args()

    validate_audio_features(args.path, args.output)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `@asynccontextmanager` lifespan | FastAPI 0.93 (2023) | Deprecated event handlers should not be used |
| `pip` + `requirements.txt` | `uv` + `pyproject.toml` + `uv.lock` | 2023-2025 | Dramatically faster installs, reproducible builds |
| `load_dotenv()` global | `pydantic-settings` `BaseSettings` | 2022+ | Type safety, validation, caching |
| `SQLAlchemy 1.x` ORM | `SQLAlchemy 2.0` with `AsyncAttrs` + `async_sessionmaker` | 2023 | Native async, cleaner session management |
| `alembic init` (sync default) | `alembic init -t async` | Alembic 1.9+ | Correct async env.py generated automatically |
| `new mapboxgl.Marker()` for bulk points | GeoJSON + circle layer | N/A (Phase 4 concern) | Out of scope for this phase |

**Deprecated/outdated:**
- `@app.on_event("startup")` and `@app.on_event("shutdown")`: Use `lifespan` parameter on `FastAPI()`.
- Spotify `/v1/audio-features` for new apps: Restricted Nov 27, 2024. 403 is expected; graceful fallback required.
- `async_scoped_session`: Replaced by `async_sessionmaker` + dependency injection pattern.

---

## Open Questions

1. **Exact YourLibrary.json field names**
   - What we know: The personal data export has flat fields (`"artist"`, `"track"`, `"album"`, `"uri"`), confirmed by community reports and rfong.github.io article. URI format is `"spotify:track:<ID>"`.
   - What's unclear: Whether `"album"` field is always present; whether there are edge cases with local files or podcast episodes in the tracks array.
   - Recommendation: Parser should use `.get()` for all fields with empty-string defaults. Filter out entries where `"uri"` doesn't start with `"spotify:track:"` to exclude episodes/local files.

2. **Spotify audio features for the user's specific app registration**
   - What we know: Apps registered after November 27, 2024 are definitively blocked (403). Apps registered before that date and with extended access granted retain access.
   - What's unclear: The user's app registration date and whether they applied for extended access before the cutoff.
   - Recommendation: Run the validation script as the first step of Phase 1. The 403 outcome is fully designed for — nullable columns, flag file, Phase 2 skip logic. Don't attempt workarounds.

3. **Countries seed data coverage for 193 UN-recognized countries**
   - What we know: `pycountry` covers 249 countries/territories (ISO 3166-1 full list). `gavinr/world-countries-centroids` provides centroids for most but may not cover all 249. UN-recognized count is ~193.
   - What's unclear: Exact overlap between the centroid dataset and pycountry's 249 entries.
   - Recommendation: Seed all pycountry entries (249) — this exceeds the 193 UN requirement. Allow NULL for lat/lon when centroid data is missing. Use `ON CONFLICT DO NOTHING` for idempotency.

---

## Sources

### Primary (HIGH confidence)
- Spotify Developer Blog (official) — https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api — confirmed audio features restricted Nov 27, 2024
- FastAPI official docs — https://fastapi.tiangolo.com/advanced/events/ — lifespan pattern code example
- FastAPI official docs — https://fastapi.tiangolo.com/advanced/settings/ — pydantic-settings `BaseSettings` + `model_config` + `@lru_cache`

### Secondary (MEDIUM confidence)
- berkkaraal.com — https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/ — FastAPI + async SQLAlchemy 2 + Alembic + Docker setup (verified against SQLAlchemy 2 docs)
- leapcell.io — https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg — async engine patterns
- last9.io — https://last9.io/blog/docker-compose-health-checks/ — Docker healthcheck patterns (cross-verified with Docker official docs)
- gavinr/world-countries-centroids GitHub — https://github.com/gavinr/world-countries-centroids — ISO alpha-2 + lat/lon centroid CSV
- pycountry PyPI — https://pypi.org/project/pycountry/ — ISO country data

### Tertiary (LOW confidence)
- rfong.github.io — https://rfong.github.io/rflog/2022/01/30/spotify-export-jq/ — YourLibrary.json field structure (`artist`, `uri`, `album`, `track`). LOW confidence because: (1) article is from 2022 and Spotify may have changed field names, (2) not an official source. **Validate against the actual export file before coding.**

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via official docs or Context7
- Architecture: HIGH — FastAPI lifespan, async SQLAlchemy, Alembic async template are well-documented current patterns
- Spotify endpoint restriction: HIGH — confirmed via official Spotify developer blog
- YourLibrary.json schema: LOW — community-sourced, 2022 article; must verify against actual file
- Pitfalls: MEDIUM — some verified via official docs, some based on cross-referenced community patterns

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days — stable stack; Spotify policy could change but 403 outcome is handled regardless)
