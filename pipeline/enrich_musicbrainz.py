#!/usr/bin/env python3
"""
enrich_musicbrainz.py — Resolve origin countries for artists via MusicBrainz API.

Queries the MusicBrainz API for each artist with mb_resolution_status='pending',
extracts the country field (ISO alpha-2), and updates the artists table with
country_id and mb_resolution_status.

The mb_resolution_status column is the checkpoint mechanism:
  - pending: not yet processed
  - resolved: country found and matched to countries table
  - not_found: no confident match or no country data in MusicBrainz
  - skipped: artist name was empty/NULL, cannot be searched

Each artist row is committed individually — if the script crashes and restarts,
it resumes from where it left off (only processes remaining pending artists).

Usage:
    python pipeline/enrich_musicbrainz.py [--env-file /path/to/.env]

Run inside Docker for database access:
    docker run --rm \\
      --network soundatlas_soundatlas_network \\
      --env-file .env \\
      -e POSTGRES_HOST=postgres \\
      -v $(pwd)/pipeline:/app \\
      -w /app \\
      python:3.12-slim \\
      bash -c "pip install -r requirements.txt && python enrich_musicbrainz.py"

MusicBrainz API constraints:
  - Must call set_useragent() before any API request
  - Built-in rate limiting at 1 req/sec — do NOT add manual time.sleep(1)
  - country field is ISO alpha-2, matching countries.iso_alpha2 directly
  - Do NOT use area field — areas can be cities/regions, not countries
"""

import argparse
import logging
import os
import time
import unicodedata

import musicbrainzngs
import psycopg2
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_sync_db_url(env_file: str) -> str:
    """Build a psycopg2-compatible sync connection URL from environment."""
    load_dotenv(env_file, override=False)

    # Try SYNC_DATABASE_URL override first
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    # Build from individual components (preferred)
    user = os.getenv("POSTGRES_USER", "soundatlas_user")
    password = os.getenv("POSTGRES_PASSWORD", "soundatlas_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "soundatlas_db")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def normalize_name(name: str) -> str:
    """Normalize artist name for comparison: NFKD, ASCII, lowercase, strip."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_name.lower().strip()


def load_country_lookup(cur) -> dict:
    """Pre-load ISO alpha-2 -> country id mapping from countries table."""
    cur.execute("SELECT iso_alpha2, id FROM countries")
    rows = cur.fetchall()
    lookup = {row[0]: row[1] for row in rows}
    logger.info(f"Loaded {len(lookup)} countries into lookup dict")
    return lookup


def mark_skipped_artists(cur, conn) -> int:
    """Mark artists with empty/NULL names as skipped — cannot be searched."""
    cur.execute(
        """
        UPDATE artists
        SET mb_resolution_status = 'skipped', updated_at = NOW()
        WHERE mb_resolution_status = 'pending'
          AND (name IS NULL OR TRIM(name) = '')
        """
    )
    count = cur.rowcount
    conn.commit()
    logger.info(f"Skipped {count} artists with empty/NULL names")
    return count


def fetch_pending_artists(cur) -> list:
    """Fetch all pending artists ordered by id for deterministic processing."""
    cur.execute(
        "SELECT id, name FROM artists WHERE mb_resolution_status = 'pending' ORDER BY id"
    )
    return cur.fetchall()


def update_artist_status(cur, conn, artist_id: int, status: str, mb_id: str | None, country_id: int | None) -> None:
    """Update a single artist's resolution status and commit immediately (checkpoint)."""
    cur.execute(
        """
        UPDATE artists
        SET mb_resolution_status = %s,
            mb_id = %s,
            country_id = %s,
            updated_at = NOW()
        WHERE id = %s AND mb_resolution_status = 'pending'
        """,
        (status, mb_id, country_id, artist_id),
    )
    conn.commit()


def search_artist_country(artist_name: str, country_lookup: dict) -> tuple[str, str | None, int | None]:
    """
    Search MusicBrainz for an artist and return (status, mb_id, country_id).

    status: 'resolved' | 'not_found'
    mb_id: MusicBrainz artist MBID (str or None)
    country_id: foreign key into countries table (int or None)
    """
    result = musicbrainzngs.search_artists(artist=artist_name, limit=5)
    artist_list = result.get("artist-list", [])

    if not artist_list:
        return "not_found", None, None

    top = artist_list[0]
    mb_id = top.get("id")

    # Score is a string in the API response — convert to int
    try:
        score = int(top.get("ext:score", 0))
    except (ValueError, TypeError):
        score = 0

    if score < 80:
        return "not_found", mb_id, None

    # Name-based disambiguation: compare normalized names
    top_name = top.get("name", "")
    norm_query = normalize_name(artist_name)
    norm_result = normalize_name(top_name)

    if norm_query != norm_result and score < 95:
        return "not_found", mb_id, None

    # Extract country (ISO alpha-2) — do NOT use area field
    country_code = top.get("country")
    if country_code and country_code in country_lookup:
        country_id = country_lookup[country_code]
        return "resolved", mb_id, country_id

    # No country or country not in our lookup
    return "not_found", mb_id, None


def enrich_musicbrainz(db_url: str) -> None:
    """Main enrichment routine."""
    # Configure MusicBrainz user agent — MUST be called before any API request
    musicbrainzngs.set_useragent("SoundAtlas", "1.0", "https://github.com/udirno/soundatlas")

    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        # Pre-load country lookup (avoids N+1 queries)
        country_lookup = load_country_lookup(cur)

        # Mark artists with empty/NULL names as skipped
        mark_skipped_artists(cur, conn)

        # Fetch remaining pending artists
        pending = fetch_pending_artists(cur)
        total = len(pending)
        logger.info(f"Processing {total} pending artists")

        if total == 0:
            logger.info("No pending artists to process — exiting")
            return

        resolved_count = 0
        not_found_count = 0

        for i, (artist_id, artist_name) in enumerate(pending, start=1):
            try:
                status, mb_id, country_id = search_artist_country(artist_name, country_lookup)

                if status == "resolved":
                    resolved_count += 1
                else:
                    not_found_count += 1

                update_artist_status(cur, conn, artist_id, status, mb_id, country_id)

            except musicbrainzngs.NetworkError as e:
                logger.warning(f"NetworkError for artist '{artist_name}' (id={artist_id}): {e} — retrying in 5s")
                time.sleep(5)
                try:
                    status, mb_id, country_id = search_artist_country(artist_name, country_lookup)
                    if status == "resolved":
                        resolved_count += 1
                    else:
                        not_found_count += 1
                    update_artist_status(cur, conn, artist_id, status, mb_id, country_id)
                except Exception as retry_err:
                    logger.error(f"Retry failed for artist '{artist_name}' (id={artist_id}): {retry_err} — marking not_found")
                    not_found_count += 1
                    update_artist_status(cur, conn, artist_id, "not_found", None, None)

            except musicbrainzngs.WebServiceError as e:
                logger.error(f"WebServiceError for artist '{artist_name}' (id={artist_id}): {e} — marking not_found")
                not_found_count += 1
                update_artist_status(cur, conn, artist_id, "not_found", None, None)

            # Progress logging every 100 artists
            if i % 100 == 0:
                logger.info(f"Processed {i}/{total} artists ({resolved_count} resolved, {not_found_count} not_found)")

        logger.info(
            f"MusicBrainz resolution complete: {resolved_count} resolved, "
            f"{not_found_count} not_found, 0 skipped out of {total} total"
        )

    except Exception as e:
        conn.rollback()
        logger.error(f"Fatal error during enrichment: {e}")
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve artist origin countries via MusicBrainz API"
    )
    parser.add_argument(
        "--env-file",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        ),
        help="Path to .env file (defaults to project root .env)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.env_file):
        import sys
        print(f"Warning: .env file not found at {args.env_file}", file=sys.stderr)

    db_url = build_sync_db_url(args.env_file)
    enrich_musicbrainz(db_url)


if __name__ == "__main__":
    main()
