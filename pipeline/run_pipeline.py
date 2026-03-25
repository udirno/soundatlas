#!/usr/bin/env python3
"""
run_pipeline.py — SoundAtlas pipeline orchestrator with stats logging.

Runs all enrichment steps in correct order:
  Step 1: seed_countries.py  (idempotent — seeds country reference data)
  Step 2: seed_library.py    (idempotent — seeds artists + tracks)
  Step 3: enrich_spotify.py  (idempotent — resolves spotify_id + metadata)
  Step 4: enrich_musicbrainz.py (idempotent — resolves countries)

After completion, queries PostgreSQL for comprehensive stats and prints a
formatted stats table.

Usage:
    python run_pipeline.py [--env-file /path/to/.env] [--export-path /path/to/YourLibrary.json]

Run inside Docker:
    docker run --rm \\
      --network soundatlas_soundatlas_network \\
      --env-file .env \\
      -e POSTGRES_HOST=postgres \\
      -v $(pwd)/pipeline:/app \\
      -v ~/Downloads/Spotify\\ Account\\ Data:/data \\
      -w /app \\
      python:3.12-slim \\
      bash -c "pip install -r requirements.txt && python run_pipeline.py --export-path /data/YourLibrary.json"

Stats-only mode (no API calls, just query current DB state):
    python run_pipeline.py --stats-only

Skip MusicBrainz step (useful for quick testing without the ~50min run):
    python run_pipeline.py --skip-musicbrainz --export-path /data/YourLibrary.json
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Scripts live in the same directory as this orchestrator
PIPELINE_DIR = Path(__file__).parent


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


def run_step(name: str, script: str, extra_args: list[str], env_file: str) -> bool:
    """Run a pipeline step via subprocess.

    Returns True on success, False on failure (non-zero exit code).
    """
    script_path = str(PIPELINE_DIR / script)
    cmd = [sys.executable, script_path, "--env-file", env_file] + extra_args

    logger.info("=" * 50)
    logger.info(f"Running step: {name}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info("=" * 50)

    try:
        result = subprocess.run(cmd, check=True)
        logger.info(f"Step '{name}' completed successfully (exit code 0)")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Step '{name}' FAILED with exit code {e.returncode}")
        logger.error("Pipeline halted — fix the issue and re-run (already-completed steps will be skipped)")
        return False


def query_stats(db_url: str) -> dict:
    """Query PostgreSQL for comprehensive pipeline stats.

    Returns a dict with all stats values needed for the formatted table.
    """
    conn = psycopg2.connect(db_url)
    conn.autocommit = True

    try:
        cur = conn.cursor()

        # Total counts
        cur.execute("SELECT COUNT(*) FROM artists")
        total_artists = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM tracks")
        total_tracks = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM user_tracks")
        total_user_tracks = cur.fetchone()[0]

        # Spotify enrichment coverage
        cur.execute("SELECT COUNT(*) FROM artists WHERE spotify_id IS NOT NULL")
        spotify_resolved = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM artists WHERE genres IS NOT NULL")
        genres_populated = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM artists WHERE image_url IS NOT NULL")
        images_populated = cur.fetchone()[0]

        # MusicBrainz resolution breakdown
        cur.execute(
            "SELECT mb_resolution_status, COUNT(*) FROM artists GROUP BY mb_resolution_status"
        )
        mb_rows = cur.fetchall()
        mb_breakdown = {row[0]: row[1] for row in mb_rows}

        # Country coverage
        cur.execute("SELECT COUNT(*) FROM artists WHERE country_id IS NOT NULL")
        artists_with_country = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(DISTINCT country_id) FROM artists WHERE country_id IS NOT NULL"
        )
        countries_represented = cur.fetchone()[0]

        return {
            "total_artists": total_artists,
            "total_tracks": total_tracks,
            "total_user_tracks": total_user_tracks,
            "spotify_resolved": spotify_resolved,
            "genres_populated": genres_populated,
            "images_populated": images_populated,
            "mb_breakdown": mb_breakdown,
            "artists_with_country": artists_with_country,
            "countries_represented": countries_represented,
        }

    finally:
        conn.close()


def pct(numerator: int, denominator: int) -> str:
    """Format a percentage string. Returns '0.0%' if denominator is 0."""
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def format_duration(seconds: float) -> str:
    """Format elapsed seconds as 'Xm Ys' or 'Xs'."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs:02d}s"


def print_stats(stats: dict, elapsed_seconds: float) -> None:
    """Print the formatted Pipeline Stats table to stdout."""
    total = stats["total_artists"]
    mb = stats["mb_breakdown"]

    # MusicBrainz status counts (with safe defaults for any missing status)
    mb_resolved = mb.get("resolved", 0)
    mb_not_found = mb.get("not_found", 0)
    mb_pending = mb.get("pending", 0)
    mb_skipped = mb.get("skipped", 0)

    duration_str = format_duration(elapsed_seconds)

    width = 50
    border = "=" * width

    print("")
    print(border)
    print("  SoundAtlas Pipeline Stats")
    print(border)
    print(f"  Total artists:         {total:,}")
    print(f"  Total tracks:          {stats['total_tracks']:,}")
    print(f"  Total user_tracks:     {stats['total_user_tracks']:,}")
    print("")
    print(f"  Spotify ID resolved:   {stats['spotify_resolved']:,} / {total:,}  ({pct(stats['spotify_resolved'], total)})")
    print(f"  Genres populated:      {stats['genres_populated']:,} / {total:,}  ({pct(stats['genres_populated'], total)})")
    print(f"  Images populated:      {stats['images_populated']:,} / {total:,}  ({pct(stats['images_populated'], total)})")
    print("")
    print("  MusicBrainz Results:")
    print(f"    resolved:            {mb_resolved:,}  ({pct(mb_resolved, total)})")
    print(f"    not_found:           {mb_not_found:,}  ({pct(mb_not_found, total)})")
    if mb_pending:
        print(f"    pending:             {mb_pending:,}  ({pct(mb_pending, total)})")
    else:
        print(f"    pending:             0  (0.0%)")
    if mb_skipped:
        print(f"    skipped:             {mb_skipped:,}  ({pct(mb_skipped, total)})")
    print("")
    print(f"  Countries represented: {stats['countries_represented']}")
    print(f"  Artists with country:  {stats['artists_with_country']:,} / {total:,}  ({pct(stats['artists_with_country'], total)})")
    print("")
    print(f"  Duration:              {duration_str}")
    print(border)
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SoundAtlas pipeline orchestrator — runs all enrichment steps in order"
    )
    parser.add_argument(
        "--env-file",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        ),
        help="Path to .env file (defaults to project root .env)",
    )
    parser.add_argument(
        "--export-path",
        default=None,
        help="Path to YourLibrary.json (passed to seed_library.py; defaults to ~/Downloads/Spotify Account Data/YourLibrary.json)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Skip all pipeline steps — just query and print current DB stats",
    )
    parser.add_argument(
        "--skip-musicbrainz",
        action="store_true",
        help="Skip step 4 (MusicBrainz enrichment) — useful for quick testing",
    )
    args = parser.parse_args()

    start_time = time.time()

    if not args.stats_only:
        # --- Step 1: seed_countries.py ---
        ok = run_step(
            name="seed_countries",
            script="seed_countries.py",
            extra_args=[],
            env_file=args.env_file,
        )
        if not ok:
            sys.exit(1)

        # --- Step 2: seed_library.py ---
        seed_extra = []
        if args.export_path:
            seed_extra = ["--export-path", args.export_path]

        ok = run_step(
            name="seed_library",
            script="seed_library.py",
            extra_args=seed_extra,
            env_file=args.env_file,
        )
        if not ok:
            sys.exit(1)

        # --- Step 3: enrich_spotify.py ---
        ok = run_step(
            name="enrich_spotify",
            script="enrich_spotify.py",
            extra_args=[],
            env_file=args.env_file,
        )
        if not ok:
            sys.exit(1)

        # --- Step 4: enrich_musicbrainz.py (optional) ---
        if not args.skip_musicbrainz:
            ok = run_step(
                name="enrich_musicbrainz",
                script="enrich_musicbrainz.py",
                extra_args=[],
                env_file=args.env_file,
            )
            if not ok:
                sys.exit(1)
        else:
            logger.info("Skipping MusicBrainz step (--skip-musicbrainz flag set)")

    else:
        logger.info("--stats-only mode: skipping all pipeline steps")

    # --- Query and print stats ---
    elapsed = time.time() - start_time

    logger.info("Querying database for final stats...")
    db_url = build_sync_db_url(args.env_file)

    try:
        stats = query_stats(db_url)
    except Exception as e:
        logger.error(f"Failed to query stats from database: {e}")
        sys.exit(1)

    print_stats(stats, elapsed)


if __name__ == "__main__":
    main()
