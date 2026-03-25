#!/usr/bin/env python3
"""
enrich_spotify.py — Enrich artist rows with Spotify API metadata.

Steps:
  1. Check pipeline/.audio_features_available flag. If AUDIO_FEATURES_AVAILABLE=false,
     skip audio feature enrichment (log and continue to artist metadata only).
  2. Resolve Spotify artist IDs for artists with spotify_id IS NULL via sp.search().
  3. Fetch genres, popularity, and image_url for all artists with spotify_id IS NOT NULL
     and genres IS NULL, using sp.artists() in batches of 50.

Usage:
    python enrich_spotify.py [--env-file /path/to/.env]

Run inside Docker:
    docker run --rm \\
      --network soundatlas_soundatlas_network \\
      --env-file .env \\
      -e POSTGRES_HOST=postgres \\
      -v $(pwd)/pipeline:/app \\
      -w /app \\
      python:3.12-slim \\
      bash -c "pip install -r requirements.txt && python enrich_spotify.py"
"""

import argparse
import logging
import os
import sys
import time
import unicodedata
from pathlib import Path

import psycopg2
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)

# Path to flag file written by validate_audio_features.py
FLAG_FILE = Path(__file__).parent / ".audio_features_available"

# Spotify API limits
ARTIST_BATCH_SIZE = 50   # sp.artists() accepts max 50 IDs per call
SEARCH_LOG_INTERVAL = 100  # Log progress every N artists during search step


def build_sync_db_url(env_file: str) -> str:
    """Build a psycopg2-compatible sync connection URL from environment."""
    load_dotenv(env_file, override=False)

    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    user = os.getenv("POSTGRES_USER", "soundatlas_user")
    password = os.getenv("POSTGRES_PASSWORD", "soundatlas_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "soundatlas_db")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def check_audio_features_flag() -> bool:
    """
    Read pipeline/.audio_features_available flag file.

    Returns True if audio features are available, False otherwise.
    Logs the result either way.
    """
    if not FLAG_FILE.exists():
        logger.warning(
            "Flag file not found at %s — assuming audio features unavailable", FLAG_FILE
        )
        return False

    with open(FLAG_FILE) as f:
        content = f.read()

    for line in content.splitlines():
        if line.startswith("AUDIO_FEATURES_AVAILABLE="):
            value = line.split("=", 1)[1].strip().lower()
            available = value == "true"
            if available:
                logger.info("Audio features: AVAILABLE (flag file)")
            else:
                logger.info(
                    "Audio features unavailable — skipping audio feature enrichment (flag file: %s)",
                    FLAG_FILE,
                )
            return available

    logger.warning("AUDIO_FEATURES_AVAILABLE key not found in flag file — assuming unavailable")
    return False


def _normalize_name(name: str) -> str:
    """Normalize artist name for fuzzy comparison (lowercase, strip, remove accents)."""
    name = name.strip().lower()
    # NFKD normalization strips accents
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return name


def resolve_artist_ids(
    sp: spotipy.Spotify,
    conn: psycopg2.extensions.connection,
) -> tuple[int, int]:
    """
    Resolve Spotify artist IDs for all artists with spotify_id IS NULL.

    Searches Spotify by artist name, takes top result, compares names.
    Updates the artists row if match found.

    Returns (resolved_count, skipped_count).
    """
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM artists WHERE spotify_id IS NULL ORDER BY id")
    artists_to_resolve = cur.fetchall()

    total = len(artists_to_resolve)
    logger.info("Resolving Spotify artist IDs for %d artists with spotify_id IS NULL", total)

    resolved = 0
    skipped = 0

    for i, (artist_id, artist_name) in enumerate(artists_to_resolve, 1):
        if i % SEARCH_LOG_INTERVAL == 0 or i == total:
            logger.info("  Search progress: %d/%d (resolved=%d, skipped=%d)", i, total, resolved, skipped)

        try:
            results = sp.search(q=artist_name, type="artist", limit=1)
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                logger.warning("Rate limited by Spotify — sleeping %d seconds", retry_after)
                time.sleep(retry_after)
                results = sp.search(q=artist_name, type="artist", limit=1)
            else:
                logger.warning("Spotify API error for '%s': %s — skipping", artist_name, e)
                skipped += 1
                continue

        items = results.get("artists", {}).get("items", [])
        if not items:
            logger.debug("No Spotify search results for '%s' — skipping", artist_name)
            skipped += 1
            continue

        top = items[0]
        result_name = top.get("name", "")
        result_id = top.get("id", "")

        # Normalize both names before comparing
        if _normalize_name(result_name) == _normalize_name(artist_name):
            try:
                cur.execute(
                    "UPDATE artists SET spotify_id = %s WHERE id = %s",
                    (result_id, artist_id),
                )
                conn.commit()
                resolved += 1
            except psycopg2.errors.UniqueViolation:
                # Another artist in DB already has this spotify_id (duplicate mapping).
                # Roll back the failed statement and skip — leave spotify_id NULL.
                conn.rollback()
                logger.debug(
                    "spotify_id=%s already claimed by another artist — skipping '%s'",
                    result_id,
                    artist_name,
                )
                skipped += 1
        else:
            logger.debug(
                "Name mismatch for '%s': got '%s' — skipping", artist_name, result_name
            )
            skipped += 1

    logger.info(
        "Artist ID resolution complete: %d resolved, %d skipped out of %d", resolved, skipped, total
    )
    return resolved, skipped


def fetch_artist_metadata(
    sp: spotipy.Spotify,
    conn: psycopg2.extensions.connection,
) -> tuple[int, int]:
    """
    Fetch genres, popularity, and image_url for all artists with spotify_id
    that have not yet been enriched (genres IS NULL).

    Uses sp.artists() in batches of 50. Updates the artists row after each batch.

    Returns (enriched_count, empty_genres_count).
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, spotify_id
        FROM artists
        WHERE spotify_id IS NOT NULL AND genres IS NULL
        ORDER BY id
        """
    )
    to_enrich = cur.fetchall()  # list of (db_id, spotify_id)

    total = len(to_enrich)
    logger.info("Fetching metadata for %d artists via sp.artists() in batches of %d", total, ARTIST_BATCH_SIZE)

    enriched = 0
    empty_genres = 0

    for batch_start in range(0, total, ARTIST_BATCH_SIZE):
        batch = to_enrich[batch_start:batch_start + ARTIST_BATCH_SIZE]
        db_ids = [row[0] for row in batch]
        spotify_ids = [row[1] for row in batch]

        try:
            result = sp.artists(spotify_ids)
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                logger.warning("Rate limited by Spotify — sleeping %d seconds", retry_after)
                time.sleep(retry_after)
                result = sp.artists(spotify_ids)
            else:
                logger.warning(
                    "Spotify API error for batch starting at %d: %s — skipping batch", batch_start, e
                )
                continue

        returned_artists = result.get("artists", [])

        # Build a map from spotify_id -> artist data for the response
        id_to_data: dict[str, dict] = {}
        for artist_data in returned_artists:
            if artist_data:
                id_to_data[artist_data["id"]] = artist_data

        # Update each artist row from the batch
        for db_id, spotify_id in zip(db_ids, spotify_ids):
            artist_data = id_to_data.get(spotify_id)
            if not artist_data:
                logger.debug("No data returned for spotify_id=%s — skipping", spotify_id)
                continue

            genres = artist_data.get("genres", []) or []
            popularity = artist_data.get("popularity")
            images = artist_data.get("images", [])
            image_url = images[0]["url"] if images else None

            if not genres:
                empty_genres += 1

            cur.execute(
                """
                UPDATE artists
                SET genres = %s,
                    popularity = %s,
                    image_url = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (genres, popularity, image_url, db_id),
            )
            enriched += 1

        conn.commit()

        if (batch_start // ARTIST_BATCH_SIZE + 1) % 10 == 0 or batch_start + ARTIST_BATCH_SIZE >= total:
            logger.info(
                "  Metadata progress: %d/%d enriched",
                min(batch_start + ARTIST_BATCH_SIZE, total),
                total,
            )

    logger.info(
        "Metadata fetch complete: %d enriched, %d had empty genres", enriched, empty_genres
    )
    return enriched, empty_genres


def enrich_spotify(db_url: str) -> None:
    """Main enrichment entry point."""
    # Step 1: Check audio features flag
    audio_features_available = check_audio_features_flag()
    if not audio_features_available:
        # Already logged inside check_audio_features_flag()
        pass
    # Do NOT call sp.audio_features() under any circumstance when flag is false.

    # Step 2: Connect to Spotify
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set. "
            "Check your .env file or environment."
        )
        sys.exit(1)

    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )

    # Step 3: Connect to PostgreSQL
    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        # Step 4: Resolve artist IDs for artists without spotify_id
        resolved, id_skipped = resolve_artist_ids(sp, conn)

        # Step 5: Fetch artist metadata in batches
        enriched, empty_genres = fetch_artist_metadata(sp, conn)

        # Summary
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM artists")
        total_artists = cur.fetchone()[0]

        print(
            f"Resolved {resolved}/{total_artists} artist IDs in this run "
            f"({id_skipped} skipped — name mismatch or no results), "
            f"enriched {enriched} artists with metadata, "
            f"{empty_genres} had empty genres"
        )

    except Exception as e:
        conn.rollback()
        logger.error("Error during enrichment: %s", e)
        raise
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Enrich artist rows with Spotify API metadata (genres, popularity, image_url)"
    )
    parser.add_argument(
        "--env-file",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        help="Path to .env file (defaults to project root .env)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.env_file) and args.env_file != "/.env":
        print(f"Warning: .env file not found at {args.env_file}", file=sys.stderr)

    db_url = build_sync_db_url(args.env_file)
    enrich_spotify(db_url)


if __name__ == "__main__":
    main()
