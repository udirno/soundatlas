# Phase 2: Data Enrichment Pipeline - Research

**Researched:** 2026-03-24
**Domain:** Spotify API (artist metadata), MusicBrainz API (country resolution), PostgreSQL upsert patterns, Python pipeline checkpoint/resume
**Confidence:** HIGH (stack verified; critical constraint — audio features unavailable — confirmed live; MusicBrainz patterns verified via official docs)

---

## Prior Decisions Carried Into This Phase

The following are locked decisions from Phase 1 that directly constrain Phase 2 implementation. They are not up for reconsideration.

### Audio Features Endpoint: CONFIRMED UNAVAILABLE

The `pipeline/.audio_features_available` flag file was written by Phase 1:
```
AUDIO_FEATURES_AVAILABLE=false
VALIDATED_AT=2026-03-24T23:49:43Z
VALIDATED_TRACK_ID=3zpGLSQ8QbbUnNjweWPLMD
```

**This means:** Phase 2 must skip audio features entirely. Do not write any code that calls `sp.audio_features()`. Read the flag file at startup and branch accordingly.

### Docker Networking Is Mandatory for Database Access

Local PostgreSQL on port 5432 shadows the Docker instance. All pipeline scripts connecting to the database must run inside Docker:
```bash
docker run --rm \
  --network soundatlas_soundatlas_network \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_USER=soundatlas_user \
  -e POSTGRES_PASSWORD=soundatlas_password \
  -e POSTGRES_DB=soundatlas_db \
  -e SPOTIFY_CLIENT_ID=... \
  -e SPOTIFY_CLIENT_SECRET=... \
  python:3.12-slim bash -c "pip install -r requirements.txt && python enrich_artists.py"
```

The confirmed network name is `soundatlas_soundatlas_network` (Docker Compose prefixes project name `soundatlas_` to declared network name `soundatlas_network`).

### `mb_resolution_status` Column Is the Checkpoint Mechanism

Artists table has `mb_resolution_status VARCHAR(20) NOT NULL DEFAULT 'pending'`. Valid values: `pending`, `resolved`, `not_found`, `skipped`. The MusicBrainz script always queries `WHERE mb_resolution_status = 'pending'` and commits each artist row individually. This replaces any need for an external checkpoint file.

### Database Access Pattern for Pipeline Scripts

Phase 1 established that pipeline scripts use **sync psycopg2** (not async SQLAlchemy) for direct database operations. See `seed_countries.py` — uses `psycopg2.connect()`, raw SQL with `ON CONFLICT`, and manual `conn.commit()`. Phase 2 follows the same pattern.

### Pipeline Script Location and Imports

Scripts live in `pipeline/`. The `parse_library.py` module is importable from other scripts in that directory. Phase 2 scripts must be importable too (for Phase 3 orchestration if needed).

---

## Summary

Phase 2 has three enrichment scripts to build: (1) Spotify artist metadata (genres, popularity, image URL) for unique artists in batches of 50, (2) MusicBrainz country resolution with built-in rate limiting and checkpoint/resume via `mb_resolution_status` column, and (3) PostgreSQL upsert seeding with stats logging.

The most important finding for planning is that **Spotify's `genres` and `popularity` fields on artists are marked as deprecated** in the current API documentation but remain accessible and functional as of March 2026. Multiple community reports note inconsistent genre data (some artists returning empty arrays since late 2024), so the pipeline must tolerate empty arrays gracefully. The `images` field is stable and returns an array of objects with `url`, `height`, `width` — use the first (widest) image URL.

For MusicBrainz, the `musicbrainzngs` Python library has built-in rate limiting at 1 req/sec by default via `set_rate_limit(limit_or_interval=1.0, new_requests=1)` — no manual `time.sleep(1)` needed. The `country` field in search results is a 2-letter ISO alpha-2 code, directly matching the `iso_alpha2` column in the `countries` table. Disambiguation handling requires comparing the top search result's name against the search query (normalized) and checking the score — MusicBrainz returns a relevance score (0-100) per result.

**Primary recommendation:** Use `musicbrainzngs` (0.7.1) for MusicBrainz, `spotipy` (already installed, 2.24.0) for Spotify artist metadata, `psycopg2-binary` (already installed) for all DB writes with `ON CONFLICT DO UPDATE`, and `mb_resolution_status` column as the checkpoint mechanism — no external file needed.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| spotipy | 2.24.0 (already installed) | Spotify artist batch fetch | Official Spotify Python client; already in pipeline |
| musicbrainzngs | 0.7.1 | MusicBrainz artist search + country lookup | Only maintained Python MusicBrainz client; built-in rate limiting |
| psycopg2-binary | 2.9.9 (already installed) | PostgreSQL writes with upsert | Sync pattern established in Phase 1; already in requirements.txt |
| python-dotenv | 1.0.1 (already installed) | .env loading for scripts | Already in pipeline |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| time | stdlib | Rate limiting fallback timing if needed | Only if musicbrainzngs rate limiter proves insufficient |
| datetime | stdlib | Pipeline stats timing (start/end timestamps) | Stats logging in 02-03 |
| logging | stdlib | Structured pipeline logging | All scripts |
| pathlib | stdlib | Flag file reading (`pipeline/.audio_features_available`) | 02-01 reads this flag |
| unicodedata | stdlib | Artist name normalization before MusicBrainz search | Helps with diacritics matching |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| musicbrainzngs | Direct HTTP requests to MB API | musicbrainzngs handles rate limiting, retries, XML/JSON parsing — no benefit to raw requests |
| psycopg2 upsert | SQLAlchemy insert().on_conflict_do_update() | SQLAlchemy approach valid but adds complexity; psycopg2 already established in pipeline |
| mb_resolution_status as checkpoint | External JSON/SQLite checkpoint file | DB column is simpler, atomic, and survives restarts without a separate file to manage |

**Installation (add to pipeline/requirements.txt):**
```bash
pip install musicbrainzngs==0.7.1
# OR with uv from pipeline/ directory:
uv add musicbrainzngs
```

All other libraries are already in `pipeline/requirements.txt`.

---

## Architecture Patterns

### Recommended Pipeline Script Structure
```
pipeline/
├── parse_library.py              # Phase 1 — importable parser (existing)
├── validate_audio_features.py    # Phase 1 — writes .audio_features_available (existing)
├── seed_countries.py             # Phase 1 — countries seed (existing)
├── .audio_features_available     # Phase 1 output — flag file read by Phase 2
├── enrich_spotify.py             # Phase 2 — Spotify artist metadata enrichment (02-01)
├── enrich_musicbrainz.py         # Phase 2 — MusicBrainz country resolution (02-02)
├── seed_pipeline.py              # Phase 2 — orchestrates upserts + stats logging (02-03)
└── requirements.txt              # Updated to add musicbrainzngs
```

### Pattern 1: Read Audio Features Flag Before Any Spotify Enrichment
**What:** Check `pipeline/.audio_features_available` at startup and skip audio feature fetching if false.
**When to use:** First thing in `enrich_spotify.py` (and any script that would call audio features).

```python
# Source: Phase 1 locked decision + pipeline/.audio_features_available confirmed false
from pathlib import Path

FLAG_FILE = Path(__file__).parent / ".audio_features_available"

def audio_features_available() -> bool:
    if not FLAG_FILE.exists():
        return False  # Treat missing flag as not available (safe default)
    content = FLAG_FILE.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("AUDIO_FEATURES_AVAILABLE="):
            return line.split("=", 1)[1].strip().lower() == "true"
    return False

# Usage at script top
FEATURES_AVAILABLE = audio_features_available()
if not FEATURES_AVAILABLE:
    print("Audio features unavailable (flag=false). Skipping audio feature enrichment.")
```

### Pattern 2: Spotify Artist Metadata Batch Fetch (batches of 50)
**What:** Fetch genres, popularity, and image URL for all unique artists in the DB.
**When to use:** `enrich_spotify.py` — the Spotify `artists()` method does NOT auto-chunk, so you must batch manually.

```python
# Source: Spotify Web API docs (get-multiple-artists) — max 50 IDs per call
# spotipy client.py confirms artists() sends all IDs in one request without chunking
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
)

def fetch_artists_batch(artist_ids: list[str]) -> list[dict]:
    """Fetch artist metadata for up to 50 Spotify artist IDs."""
    if not artist_ids:
        return []
    result = sp.artists(artist_ids)  # max 50 IDs
    return result.get("artists", [])

def enrich_artists_spotify(spotify_ids: list[str]) -> list[dict]:
    """Fetch all artists in batches of 50."""
    results = []
    for i in range(0, len(spotify_ids), 50):
        batch = spotify_ids[i:i + 50]
        artists = fetch_artists_batch(batch)
        results.extend(artists)
    return results
```

### Pattern 3: Extract Image URL from Spotify Images Array
**What:** Spotify returns `images` as an array of objects sorted widest first. Take index 0 for the full-size URL.
**When to use:** Processing each artist in the Spotify response.

```python
# Source: Spotify Web API docs — images array sorted widest first
def extract_image_url(artist_data: dict) -> str | None:
    images = artist_data.get("images", [])
    if images:
        return images[0].get("url")  # First = widest/largest
    return None

# Extract all fields from one artist response dict
def parse_artist_metadata(artist: dict) -> dict:
    return {
        "spotify_id": artist.get("id"),
        "genres": artist.get("genres") or [],  # May be empty array — tolerate it
        "popularity": artist.get("popularity"),  # Deprecated but still returned
        "image_url": extract_image_url(artist),
    }
```

### Pattern 4: MusicBrainz Country Resolution with Built-In Rate Limiting
**What:** Search MusicBrainz for each artist by name, check the top result's score and name match, extract ISO alpha-2 country code.
**When to use:** `enrich_musicbrainz.py` — process all artists WHERE mb_resolution_status = 'pending'.

```python
# Source: musicbrainzngs docs — https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/api/
# Source: MusicBrainz API search docs — country field is ISO 3166-1 alpha-2
import musicbrainzngs

# MUST be called before any API requests
musicbrainzngs.set_useragent(
    "SoundAtlas",
    "1.0",
    "https://github.com/yourusername/soundatlas",  # or contact email
)
# Default rate limit is already 1 req/sec — no need to change
# musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)  # This is the default

def resolve_artist_country(artist_name: str) -> dict:
    """
    Resolve artist country from MusicBrainz.
    Returns dict with keys: country_code, mb_id, status
    status: 'resolved' | 'not_found'
    """
    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=5)
        artist_list = result.get("artist-list", [])

        if not artist_list:
            return {"country_code": None, "mb_id": None, "status": "not_found"}

        # Top result — check score and name match
        top = artist_list[0]
        score = int(top.get("ext:score", 0))
        mb_name = top.get("name", "")

        # Require high confidence match
        if score < 80:
            return {"country_code": None, "mb_id": None, "status": "not_found"}

        # Normalize names for comparison
        import unicodedata
        def normalize(s):
            return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

        if normalize(mb_name) != normalize(artist_name):
            # Name doesn't match well enough — check disambiguation if available
            # If score is very high (>= 95) trust it despite name difference
            if score < 95:
                return {"country_code": None, "mb_id": None, "status": "not_found"}

        country_code = top.get("country")  # ISO alpha-2 or None
        mb_id = top.get("id")

        if country_code:
            return {"country_code": country_code, "mb_id": mb_id, "status": "resolved"}
        else:
            return {"country_code": None, "mb_id": mb_id, "status": "not_found"}

    except musicbrainzngs.WebServiceError as e:
        raise  # Caller handles retries
```

### Pattern 5: Checkpoint/Resume via `mb_resolution_status` Column
**What:** Always query `WHERE mb_resolution_status = 'pending'` and commit each row individually. Restart is safe because resolved/not_found rows are skipped.
**When to use:** The main loop in `enrich_musicbrainz.py`.

```python
# Source: Phase 1 locked decision + artists model confirmed (mb_resolution_status default 'pending')
import psycopg2

def get_pending_artists(conn) -> list[dict]:
    """Fetch all artists that haven't been processed yet."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, spotify_id
        FROM artists
        WHERE mb_resolution_status = 'pending'
        ORDER BY id
    """)
    rows = cur.fetchall()
    return [{"id": r[0], "name": r[1], "spotify_id": r[2]} for r in rows]

def update_artist_mb_status(conn, artist_id: int, country_code: str | None,
                             mb_id: str | None, status: str) -> None:
    """Update one artist row and commit immediately (checkpoint pattern)."""
    cur = conn.cursor()
    if country_code:
        # Look up country_id from countries table
        cur.execute(
            "SELECT id FROM countries WHERE iso_alpha2 = %s",
            (country_code,)
        )
        row = cur.fetchone()
        country_id = row[0] if row else None
    else:
        country_id = None

    cur.execute("""
        UPDATE artists
        SET mb_resolution_status = %s,
            mb_id = %s,
            country_id = %s,
            updated_at = NOW()
        WHERE id = %s
          AND mb_resolution_status = 'pending'
    """, (status, mb_id, country_id, artist_id))
    conn.commit()  # Commit after EACH artist — enables resume after crash
```

### Pattern 6: PostgreSQL Upsert for Artist and Track Enrichment
**What:** Use `INSERT ... ON CONFLICT (spotify_id) DO UPDATE SET ...` to safely re-run without duplicates.
**When to use:** `seed_pipeline.py` (02-03) and artist enrichment writes in `enrich_spotify.py`.

```python
# Source: Phase 1 established psycopg2 upsert pattern (seed_countries.py)
# Postgres ON CONFLICT for named unique constraint
def upsert_artist_metadata(conn, spotify_id: str, genres: list,
                            popularity: int | None, image_url: str | None) -> None:
    cur = conn.cursor()
    cur.execute("""
        UPDATE artists
        SET genres = %s,
            popularity = %s,
            image_url = %s,
            updated_at = NOW()
        WHERE spotify_id = %s
    """, (genres, popularity, image_url, spotify_id))
    conn.commit()
```

Note: For artist enrichment, UPDATE (not upsert) is the right pattern because artists are seeded in Phase 1 via the library parse. A true INSERT ... ON CONFLICT is needed only if new artists could be introduced at this step.

### Pattern 7: Pipeline Stats Logging
**What:** Print a summary table after pipeline completes with resolved/unresolved counts, tracks processed, and duration.
**When to use:** End of `seed_pipeline.py` or each enrichment script.

```python
import time

start_time = time.time()
# ... pipeline runs ...
elapsed = time.time() - start_time

def print_pipeline_stats(resolved: int, not_found: int, skipped: int,
                          tracks_processed: int, elapsed_seconds: float) -> None:
    total = resolved + not_found + skipped
    minutes, seconds = divmod(int(elapsed_seconds), 60)
    print()
    print("=" * 50)
    print("Pipeline Stats")
    print("=" * 50)
    print(f"  Artists resolved:    {resolved:>6}")
    print(f"  Artists not found:   {not_found:>6}")
    print(f"  Artists skipped:     {skipped:>6}")
    print(f"  Artists total:       {total:>6}")
    print(f"  Tracks processed:    {tracks_processed:>6}")
    print(f"  Duration:            {minutes}m {seconds}s")
    print("=" * 50)
```

### Anti-Patterns to Avoid
- **Calling `sp.audio_features()` without checking the flag file:** The endpoint is confirmed 403 for this app. Always gate on the flag.
- **Not setting `musicbrainzngs.set_useragent()`:** The library raises `UsageError` before making any request if this is missing. Set it once at script startup.
- **Trusting `score < 80` results from MusicBrainz:** Common names (e.g., "The Police", "Prince") can match wrong artists. High score threshold (80+) with name comparison is the minimum acceptable filter.
- **Batching Spotify `artists()` in groups > 50:** The API returns a 400 error for more than 50 IDs. Always chunk to 50.
- **Committing after the full loop in MusicBrainz enrichment:** If the script crashes, all progress is lost. Commit after each artist — that's the checkpoint/resume mechanism.
- **Running pipeline scripts directly on host:** Local PostgreSQL port 5432 shadows Docker. Always run in Docker with `--network soundatlas_soundatlas_network`.
- **Overwriting `mb_resolution_status = 'resolved'` on re-run:** The UPDATE query must include `AND mb_resolution_status = 'pending'` in the WHERE clause to prevent overwriting.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MusicBrainz rate limiting | Manual `time.sleep(1)` loop | `musicbrainzngs` built-in rate limiter | Already handles 1 req/sec; also handles 503 retry logic |
| MusicBrainz XML/JSON parsing | Raw requests + XML parse | `musicbrainzngs` | Library normalizes responses to Python dicts |
| Spotify auth + token refresh | Manual OAuth token management | `spotipy.SpotifyClientCredentials` | Already established in Phase 1; handles refresh automatically |
| Pipeline checkpoint state | External JSON/SQLite checkpoint file | `mb_resolution_status` column | Atomic, transactional, survives crashes without a separate file |
| Artist deduplication | Custom dedup logic | Query by `spotify_id` which has a UNIQUE constraint | Database enforces uniqueness; upsert is idempotent |
| Country code lookup | String matching against country names | Direct `iso_alpha2` lookup in `countries` table | MusicBrainz returns ISO alpha-2 directly; exact match to DB column |

**Key insight:** The `mb_resolution_status` column-as-checkpoint pattern eliminates the most common pipeline problem (lost progress on crash) without any external state management.

---

## Common Pitfalls

### Pitfall 1: Spotify `artists()` Does Not Auto-Chunk
**What goes wrong:** Passing more than 50 IDs to `sp.artists()` returns a 400 Bad Request error.
**Why it happens:** Unlike `sp.audio_features()` which has internal chunking (for i in range(0, len(ids), 50)), `sp.artists()` sends all IDs in one request directly to the API endpoint which has a hard 50-ID limit.
**How to avoid:** Always chunk manually: `for i in range(0, len(all_ids), 50): sp.artists(all_ids[i:i+50])`.
**Warning signs:** SpotifyException with HTTP 400 or "Invalid IDs" message.

### Pitfall 2: `musicbrainzngs.set_useragent()` Not Called Before Requests
**What goes wrong:** Script raises `musicbrainzngs.musicbrainz.UsageError: No useragent set` on the first API call.
**Why it happens:** MusicBrainz requires a User-Agent identifying the application — the library enforces this at the Python level.
**How to avoid:** Call `musicbrainzngs.set_useragent("AppName", "version", "contact")` at the top of the script before any API call.
**Warning signs:** `UsageError` on first `search_artists()` call.

### Pitfall 3: MusicBrainz `country` Field Is Often Absent in Search Results
**What goes wrong:** `top.get("country")` returns `None` even for well-known artists.
**Why it happens:** Not all MusicBrainz artist records have the `country` field populated — it's optional metadata. The API only returns it if curated. Some well-known artists only have `area` but not `country`.
**How to avoid:** `status = "not_found"` when `country` is None even if score is high. Do not try to derive country from `area` — areas can be cities/regions, not countries.
**Warning signs:** High-confidence matches (score > 90) returning `country=None`.

### Pitfall 4: Spotify Genres Often Return Empty Arrays
**What goes wrong:** `artist.get("genres")` returns `[]` for many artists, especially smaller acts.
**Why it happens:** Spotify genres are curated and assigned by Spotify's editorial team — not all artists have genre tags. As of late 2024, the coverage is inconsistent and field is deprecated.
**How to avoid:** Always treat empty genres array as valid data, not an error. Store `[]` as an empty PostgreSQL array. Do not retry or fail when genres is empty.
**Warning signs:** Many artists showing empty `genres` column in DB — this is expected.

### Pitfall 5: MusicBrainz Score Alone Is Not Sufficient for Disambiguation
**What goes wrong:** "Prince" matches Prince (the artist), Prince (classical musician), Prince (Ukrainian rapper), etc. Score may be 100 for wrong artist.
**Why it happens:** MusicBrainz scores measure text match quality, not artist identity. Common or ambiguous names score high for multiple different entities.
**How to avoid:** Combine score threshold (>= 80) with normalized name comparison. For very common names, consider adding `type:"person"` or `type:"group"` as additional search filters.
**Warning signs:** Country codes that don't match expected distribution (too many artists from one unexpected country).

### Pitfall 6: Overwriting Resolved Artists on Re-Run
**What goes wrong:** Re-running the MusicBrainz script overwrites previously resolved `country_id` with `NULL` (if artist is now not_found) or changes status.
**Why it happens:** Forgetting `AND mb_resolution_status = 'pending'` in the UPDATE WHERE clause.
**How to avoid:** All UPDATE statements for MusicBrainz enrichment must include `AND mb_resolution_status = 'pending'` in WHERE. Verified by reading back a resolved artist and confirming it's unchanged after re-run.
**Warning signs:** Decrease in resolved count after re-run.

### Pitfall 7: Docker Run Command Missing Environment Variables
**What goes wrong:** Pipeline script connects to Docker postgres but Spotify credentials are missing, causing 401.
**Why it happens:** Forgetting to pass `-e SPOTIFY_CLIENT_ID` and `-e SPOTIFY_CLIENT_SECRET` to `docker run`.
**How to avoid:** Use `--env-file` to pass the project `.env` file to `docker run`:
```bash
docker run --rm \
  --network soundatlas_soundatlas_network \
  --env-file /path/to/.env \
  -e POSTGRES_HOST=postgres \
  python:3.12-slim bash -c "..."
```
Note: `POSTGRES_HOST=postgres` must override the `.env` file's `localhost` value, hence it's passed separately after `--env-file`.
**Warning signs:** 401 Unauthorized from Spotify inside Docker; or "connection refused" from psycopg2.

### Pitfall 8: Spotify Artist ID vs Track Artist ID
**What goes wrong:** Using the track's `artist_name` string to look up on Spotify instead of the actual `spotify_id` of the artist.
**Why it happens:** The `YourLibrary.json` export contains `artist` (name string) and track URI, but not an artist URI. Phase 2 must use the artist's Spotify ID from the `artists` table, not re-search by name.
**Why it matters:** The `artists` table stores `spotify_id` for each artist (populated during Phase 1 seeding from the library parse). Use that ID directly for `sp.artists()` batch fetch.
**Warning signs:** Artist metadata lookup failures for artists with common names; duplicated artists in DB.

---

## Code Examples

Verified patterns from official sources and Phase 1 established code:

### Read Audio Features Flag File
```python
# Source: Phase 1 — pipeline/.audio_features_available flag file format
from pathlib import Path

def audio_features_available() -> bool:
    flag_file = Path(__file__).parent / ".audio_features_available"
    if not flag_file.exists():
        return False
    for line in flag_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("AUDIO_FEATURES_AVAILABLE="):
            return line.split("=", 1)[1].strip().lower() == "true"
    return False
```

### musicbrainzngs Setup and Artist Search
```python
# Source: https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/api/
import musicbrainzngs

musicbrainzngs.set_useragent(
    "SoundAtlas",
    "1.0",
    "contact@example.com",  # MusicBrainz requires contact info
)
# Built-in rate limit is 1 req/sec — already enabled by default

result = musicbrainzngs.search_artists(artist="Radiohead", limit=5)
for artist in result["artist-list"]:
    print(artist["id"], artist["name"], artist.get("country"), artist.get("ext:score"))
```

### Spotify Batch Artist Metadata Fetch
```python
# Source: https://developer.spotify.com/documentation/web-api/reference/get-multiple-artists
# Batch limit: 50 IDs per request (confirmed from Spotify API docs + spotipy client.py)
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
)

artist_ids = [...]  # list of Spotify artist IDs from artists table

for i in range(0, len(artist_ids), 50):
    batch = artist_ids[i:i + 50]
    response = sp.artists(batch)
    for artist in response["artists"]:
        if artist is None:
            continue  # Artist ID not found — skip
        genres = artist.get("genres") or []
        popularity = artist.get("popularity")
        images = artist.get("images", [])
        image_url = images[0]["url"] if images else None
        # Write to DB...
```

### psycopg2 Upsert Pattern for Artist Enrichment
```python
# Source: Phase 1 seed_countries.py pattern — psycopg2 direct SQL
import psycopg2

conn = psycopg2.connect(db_url)
conn.autocommit = False

cur = conn.cursor()
cur.execute("""
    UPDATE artists
    SET genres = %s,
        popularity = %s,
        image_url = %s,
        updated_at = NOW()
    WHERE spotify_id = %s
""", (genres, popularity, image_url, spotify_id))
conn.commit()
```

### Docker Run Pattern for Pipeline Scripts
```bash
# Source: Phase 1 established pattern (01-02-SUMMARY.md)
# Network: soundatlas_soundatlas_network (confirmed with `docker network ls`)
docker run --rm \
  --network soundatlas_soundatlas_network \
  --env-file /path/to/soundatlas/.env \
  -e POSTGRES_HOST=postgres \
  -v /path/to/soundatlas/pipeline:/app \
  -w /app \
  python:3.12-slim \
  bash -c "pip install -r requirements.txt && python enrich_spotify.py"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `time.sleep(1)` for MusicBrainz | `musicbrainzngs` built-in rate limiter | musicbrainzngs 0.6+ | No manual timing needed; handles 503 retries too |
| External checkpoint file (JSON/SQLite) | `mb_resolution_status` DB column | Phase 1 design decision | Atomic, crash-safe, no extra state to manage |
| Spotify audio features for all tracks | Skip entirely (flag=false) | Nov 27, 2024 | Confirmed 403; audio feature charts in Phase 4 will be hidden |
| Spotify batch artist fetch (100 IDs) | 50 IDs per batch | API always had 50 limit | Plan said 100 — actual limit is 50; requirement needs correction |
| Track audio features in 100-track batches | Skip entirely | Nov 27, 2024 | PIPE-02 is dead code; do not implement |

**Deprecated/outdated — for this phase:**
- PIPE-02 (Spotify audio features batch fetch in batches of 100): Flag confirmed false. **Do not implement**. Write a stub that checks the flag and logs "skipping — endpoint unavailable". Nullable columns already in DB.
- Spotify `recommendations` endpoint: Restricted Nov 2024 for new apps. Not needed in Phase 2 but avoid designing around it.

**Correction to phase requirements:**
- PIPE-02 states "batches of 100 tracks" — the actual Spotify audio features batch limit is 50 (not 100). However, since PIPE-02 is dead (flag=false), this is moot. Do not write audio features fetch code.
- The plan for 02-01 mentions "batches of 100 tracks" for audio features and "artist metadata fetch". Split these: artist metadata is 50 artists per batch, audio features are skipped.

---

## Open Questions

1. **Do artists in the `artists` table have `spotify_id` populated?**
   - What we know: `artists.spotify_id` column is defined as `UNIQUE`, nullable. Phase 1 seeded artists from `YourLibrary.json` which only has `artist` (name string) and track URI — not an artist URI.
   - What's unclear: Whether Phase 1's `seed_pipeline.py` (or equivalent) populated `spotify_id` on the artists rows, or whether artist rows only have `name` and no `spotify_id`.
   - Recommendation: Check the DB before writing enrichment code. If `spotify_id` is NULL on artist rows, Phase 2 must first resolve Spotify artist IDs by searching by name — an additional step not in the current plan.
   - **CRITICAL: Verify with `SELECT COUNT(*) FROM artists WHERE spotify_id IS NOT NULL;` before writing 02-01.**

2. **How many artists are in the `artists` table right now?**
   - What we know: Phase 1 parsed `YourLibrary.json` — the phase description says 3,022 artists.
   - What's unclear: Whether the parse-and-seed script was run in Phase 1 or whether that's planned for Phase 2 (02-03).
   - Recommendation: Check `SELECT COUNT(*) FROM artists;` before planning 02-01.

3. **MusicBrainz disambiguation accuracy for the actual 3,022 artist dataset**
   - What we know: The score threshold approach handles the most common disambiguation cases. Ambiguous names (Prince, The, etc.) will have lower scores.
   - What's unclear: What percentage of the 3,022 artists will be unresolvable via the score/name approach alone.
   - Recommendation: Per the blocker note in the phase description — run the full script and manually audit the first 200 resolved artists before trusting the full run. Plan this as a task step, not an afterthought.

4. **Spotify `genres` field reliability for Phase 4 filtering**
   - What we know: Field is deprecated and returning empty arrays for many artists since late 2024. The data will be stored but may be sparse.
   - What's unclear: What percentage of the 3,022 artists will have genres populated.
   - Recommendation: Store what's returned (including empty arrays). Phase 4 should show genre filters only when data is present, with a note about coverage.

---

## Sources

### Primary (HIGH confidence)
- MusicBrainz API Rate Limiting (official) — https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting — 1 req/sec IP limit, 503 on exceed
- MusicBrainz API Search (official) — https://musicbrainz.org/doc/MusicBrainz_API/Search — country field is ISO 3166-1 alpha-2
- musicbrainzngs docs (official) — https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/api/ — set_useragent, search_artists, set_rate_limit default
- Spotify Get Multiple Artists endpoint (official) — https://developer.spotify.com/documentation/web-api/reference/get-multiple-artists — 50 ID max, genres/popularity deprecated but functional
- Spotify Get Artist endpoint (official) — https://developer.spotify.com/documentation/web-api/reference/get-an-artist — confirmed genres and popularity marked deprecated but still accessible
- Phase 1 confirmed: `pipeline/.audio_features_available` = false — live validation result

### Secondary (MEDIUM confidence)
- spotipy client.py source (GitHub) — https://github.com/plamere/spotipy/blob/master/spotipy/client.py — confirmed `artists()` does NOT auto-chunk (unlike `audio_features()` which does)
- musicbrainzngs rate limiting GitHub issue #204 — https://github.com/alastair/python-musicbrainzngs/issues/204 — confirms set_rate_limit default is 1 req/sec
- SQLAlchemy 2.0 PostgreSQL upsert docs — https://docs.sqlalchemy.org/en/20/dialects/postgresql.html — ON CONFLICT DO UPDATE pattern (used psycopg2 direct SQL instead, per Phase 1 pattern)

### Tertiary (LOW confidence)
- Spotify Community Forum — https://community.spotify.com/t5/Spotify-for-Developers/Get-Artist-API-is-not-returning-any-or-all-Genres — genres returning empty since late 2024 for many artists. LOW: community report, not official docs.
- WebSearch: MusicBrainz disambiguation best practices — multiple community sources agree on score threshold approach but exact threshold varies. Use 80 as a conservative starting point; adjust after auditing first 200 results.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — spotipy and psycopg2 already installed/verified; musicbrainzngs version from PyPI; batch limits confirmed from official Spotify API docs
- Audio features skip: HIGH — confirmed live (flag file written, AUDIO_FEATURES_AVAILABLE=false)
- MusicBrainz rate limiting: HIGH — official docs + musicbrainzngs library defaults confirmed
- MusicBrainz disambiguation accuracy: LOW — untested against actual 3,022 artist dataset; manual audit required
- Spotify genres reliability: MEDIUM — deprecated per official docs, community reports of empty arrays, but still accessible
- Docker networking pattern: HIGH — confirmed from Phase 1 execution and `docker network ls`

**Research date:** 2026-03-24
**Valid until:** 2026-04-23 (30 days — Spotify API policy could change but 403 fallback is already handled; MusicBrainz API is stable)
