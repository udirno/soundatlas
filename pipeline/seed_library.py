#!/usr/bin/env python3
"""
seed_library.py — Seed artists and tracks from the Spotify library export into PostgreSQL.

Parses YourLibrary.json, inserts all unique artists and tracks into the database.
Artist spotify_id is left NULL initially — resolved by enrich_spotify.py in the next step.

Usage:
    python seed_library.py [--env-file /path/to/.env] [--export-path /path/to/YourLibrary.json]

Run inside Docker:
    docker run --rm \\
      --network soundatlas_soundatlas_network \\
      -e POSTGRES_HOST=postgres \\
      -e POSTGRES_USER=soundatlas_user \\
      -e POSTGRES_PASSWORD=soundatlas_password \\
      -e POSTGRES_DB=soundatlas_db \\
      -v $(pwd)/pipeline:/app \\
      -v ~/Downloads/Spotify\\ Account\\ Data:/data \\
      -w /app \\
      python:3.12-slim \\
      bash -c "pip install -r requirements.txt && python seed_library.py --export-path /data/YourLibrary.json"
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_EXPORT_PATH = Path("~/Downloads/Spotify Account Data/YourLibrary.json").expanduser()
BATCH_SIZE = 500


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


def seed_library(db_url: str, export_path: Path) -> None:
    """
    Parse YourLibrary.json and seed artists, tracks, and user_tracks into PostgreSQL.

    - Artists are inserted with name only (spotify_id resolved later by enrich_spotify.py).
    - Tracks are inserted with ON CONFLICT (spotify_id) DO NOTHING for idempotency.
    - user_tracks are inserted with existence check for idempotency (no unique constraint).
    """
    # Import here so parse_library.py must be in the same directory
    sys.path.insert(0, str(Path(__file__).parent))
    from parse_library import parse_liked_tracks

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    logger.info("Parsing Spotify library export from %s", export_path)
    tracks = parse_liked_tracks(export_path)
    logger.info("Parsed %d unique tracks", len(tracks))

    # Collect unique artist names
    unique_artists = {}  # name -> None (ordered dict for deterministic iteration)
    for track in tracks:
        name = track["artist_name"]
        if name not in unique_artists:
            unique_artists[name] = None

    logger.info("Found %d unique artists", len(unique_artists))

    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        # --- Seed artists ---
        # Artists table has spotify_id as UNIQUE but name is NOT unique.
        # For idempotency: SELECT existing artists by name, INSERT only new ones.
        artist_name_to_id: dict[str, int] = {}

        # Fetch all existing artists by name
        cur.execute("SELECT id, name FROM artists")
        for row in cur.fetchall():
            artist_id, artist_name = row
            # If multiple artists share a name, keep the first encountered
            if artist_name not in artist_name_to_id:
                artist_name_to_id[artist_name] = artist_id

        artists_new = 0
        artists_existing = 0

        for artist_name in unique_artists:
            if artist_name in artist_name_to_id:
                artists_existing += 1
                continue

            # Insert new artist with name only; spotify_id resolved later
            cur.execute(
                """
                INSERT INTO artists (name)
                VALUES (%s)
                RETURNING id
                """,
                (artist_name,),
            )
            new_id = cur.fetchone()[0]
            artist_name_to_id[artist_name] = new_id
            artists_new += 1

        conn.commit()
        logger.info(
            "Artists: %d new, %d already existed", artists_new, artists_existing
        )

        # --- Seed tracks ---
        # tracks.spotify_id is UNIQUE NOT NULL — use ON CONFLICT DO NOTHING for idempotency.
        track_spotify_id_to_id: dict[str, int] = {}

        # Fetch existing track spotify_ids
        cur.execute("SELECT id, spotify_id FROM tracks WHERE spotify_id IS NOT NULL")
        for row in cur.fetchall():
            track_db_id, track_spotify_id = row
            track_spotify_id_to_id[track_spotify_id] = track_db_id

        tracks_new = 0
        tracks_existing = 0
        batch: list[tuple] = []

        def flush_track_batch(batch: list[tuple]) -> None:
            """Insert a batch of tracks and update track_spotify_id_to_id."""
            if not batch:
                return
            cur.executemany(
                """
                INSERT INTO tracks (name, spotify_id, artist_id, album_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (spotify_id) DO NOTHING
                """,
                batch,
            )
            conn.commit()

        returning_batch: list[tuple] = []  # (name, spotify_id, artist_id, album_name)

        for track in tracks:
            spotify_id = track["spotify_id"]
            if spotify_id in track_spotify_id_to_id:
                tracks_existing += 1
                continue

            artist_id = artist_name_to_id.get(track["artist_name"])
            batch.append((track["name"], spotify_id, artist_id, track["album_name"] or None))

            if len(batch) >= BATCH_SIZE:
                flush_track_batch(batch)
                tracks_new += len(batch)
                batch = []

        if batch:
            flush_track_batch(batch)
            tracks_new += len(batch)

        logger.info(
            "Tracks: %d new, %d already existed", tracks_new, tracks_existing
        )

        # Refresh track id map (needed for user_tracks)
        cur.execute("SELECT id, spotify_id FROM tracks WHERE spotify_id IS NOT NULL")
        for row in cur.fetchall():
            track_db_id, track_spotify_id = row
            track_spotify_id_to_id[track_spotify_id] = track_db_id

        # --- Seed user_tracks ---
        # user_tracks has no unique constraint on (track_id, artist_id).
        # Load existing (track_id, artist_id) pairs to avoid duplicates on re-run.
        cur.execute("SELECT track_id, artist_id FROM user_tracks")
        existing_user_tracks: set[tuple] = set()
        for row in cur.fetchall():
            existing_user_tracks.add((row[0], row[1]))

        user_tracks_new = 0
        user_tracks_existing = 0
        user_tracks_batch: list[tuple] = []

        def flush_user_track_batch(batch: list[tuple]) -> None:
            if not batch:
                return
            cur.executemany(
                """
                INSERT INTO user_tracks (track_id, artist_id)
                VALUES (%s, %s)
                """,
                batch,
            )
            conn.commit()

        for track in tracks:
            spotify_id = track["spotify_id"]
            track_db_id = track_spotify_id_to_id.get(spotify_id)
            if track_db_id is None:
                logger.warning("Track %s not found in DB after insert — skipping user_track", spotify_id)
                continue

            artist_id = artist_name_to_id.get(track["artist_name"])
            pair = (track_db_id, artist_id)

            if pair in existing_user_tracks:
                user_tracks_existing += 1
                continue

            user_tracks_batch.append(pair)
            existing_user_tracks.add(pair)

            if len(user_tracks_batch) >= BATCH_SIZE:
                flush_user_track_batch(user_tracks_batch)
                user_tracks_new += len(user_tracks_batch)
                user_tracks_batch = []

        if user_tracks_batch:
            flush_user_track_batch(user_tracks_batch)
            user_tracks_new += len(user_tracks_batch)

        logger.info(
            "user_tracks: %d new, %d already existed", user_tracks_new, user_tracks_existing
        )

        total_artists = artists_new + artists_existing
        total_tracks = tracks_new + tracks_existing
        total_user_tracks = user_tracks_new + user_tracks_existing
        print(
            f"Seeded {artists_new} artists ({total_artists} total), "
            f"{tracks_new} tracks ({total_tracks} total), "
            f"{user_tracks_new} user_tracks ({total_user_tracks} total)"
        )

    except Exception as e:
        conn.rollback()
        logger.error("Error seeding library: %s", e)
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed artists and tracks from Spotify library export into PostgreSQL"
    )
    parser.add_argument(
        "--env-file",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        help="Path to .env file (defaults to project root .env)",
    )
    parser.add_argument(
        "--export-path",
        default=str(DEFAULT_EXPORT_PATH),
        help="Path to YourLibrary.json from Spotify data export",
    )
    args = parser.parse_args()

    if not os.path.exists(args.env_file):
        print(f"Warning: .env file not found at {args.env_file}", file=sys.stderr)

    export_path = Path(args.export_path).expanduser().resolve()
    if not export_path.exists():
        print(f"Error: export file not found: {export_path}", file=sys.stderr)
        sys.exit(1)

    db_url = build_sync_db_url(args.env_file)
    seed_library(db_url, export_path)


if __name__ == "__main__":
    main()
