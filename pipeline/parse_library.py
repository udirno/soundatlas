"""
parse_library.py — Spotify export parser module

Parses YourLibrary.json from Spotify's data export and returns a
deduplicated list of liked tracks with Spotify IDs.

Usage as module:
    from parse_library import parse_liked_tracks
    tracks = parse_liked_tracks("~/Downloads/Spotify Account Data/YourLibrary.json")

Usage as CLI:
    python parse_library.py --path ~/Downloads/"Spotify Account Data"/YourLibrary.json
"""

import argparse
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_EXPORT_PATH = Path("~/Downloads/Spotify Account Data/YourLibrary.json").expanduser()

# Candidate field names in order of preference (Spotify export format varies by account)
_TRACK_NAME_FIELDS = ["track", "trackName"]
_ARTIST_NAME_FIELDS = ["artist", "artistName"]
_ALBUM_NAME_FIELDS = ["album", "albumName"]
_URI_FIELDS = ["uri", "trackUri"]


def _extract_track_id(uri: str) -> str | None:
    """Extract Spotify track ID from a Spotify URI (spotify:track:{id})."""
    if not uri or not isinstance(uri, str):
        return None
    parts = uri.split(":")
    if len(parts) == 3 and parts[0] == "spotify" and parts[1] == "track":
        track_id = parts[2].strip()
        if track_id:
            return track_id
    return None


def _get_field(obj: dict, candidates: list[str]) -> str | None:
    """Return the first non-empty value from a list of candidate field names."""
    for field in candidates:
        val = obj.get(field)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _detect_tracks_key(data: dict) -> str:
    """
    Detect which top-level key contains the list of track objects.

    Looks for a list of dicts that have URI-like fields.
    Raises ValueError if no suitable key is found.
    """
    if "tracks" in data and isinstance(data["tracks"], list):
        return "tracks"

    # Fallback: search for any list of dicts containing URI fields
    for key, value in data.items():
        if isinstance(value, list) and value:
            sample = value[0] if value else {}
            if isinstance(sample, dict):
                has_uri = any(f in sample for f in _URI_FIELDS)
                if has_uri:
                    logger.warning(
                        "Expected top-level key 'tracks' not found. "
                        "Using '%s' instead (contains URI-like fields).",
                        key,
                    )
                    return key

    raise ValueError(
        f"Cannot find track data in export file. "
        f"Top-level keys found: {list(data.keys())}. "
        f"Expected a 'tracks' key with a list of track objects."
    )


def parse_liked_tracks(export_path: str | Path) -> list[dict]:
    """
    Parse a Spotify data export YourLibrary.json and return deduplicated liked tracks.

    Args:
        export_path: Path to YourLibrary.json from Spotify data export.

    Returns:
        List of dicts with keys: spotify_id, name, artist_name, album_name.
        Sorted by artist_name. Duplicates removed (first occurrence kept).

    Raises:
        FileNotFoundError: If export_path does not exist.
        ValueError: If file structure is unrecognizable.
    """
    export_path = Path(export_path).expanduser().resolve()

    if not export_path.exists():
        raise FileNotFoundError(f"Spotify export file not found: {export_path}")

    logger.info("Loading Spotify export from %s", export_path)

    with open(export_path, encoding="utf-8") as f:
        data = json.load(f)

    tracks_key = _detect_tracks_key(data)
    raw_tracks = data[tracks_key]

    logger.info("Found %d raw track entries under key '%s'", len(raw_tracks), tracks_key)

    seen_ids: dict[str, dict] = {}  # spotify_id -> first occurrence
    malformed_count = 0

    for raw in raw_tracks:
        if not isinstance(raw, dict):
            malformed_count += 1
            logger.warning("Skipping non-dict entry: %r", raw)
            continue

        track_name = _get_field(raw, _TRACK_NAME_FIELDS)
        artist_name = _get_field(raw, _ARTIST_NAME_FIELDS)
        album_name = _get_field(raw, _ALBUM_NAME_FIELDS) or ""
        uri = _get_field(raw, _URI_FIELDS)
        spotify_id = _extract_track_id(uri) if uri else None

        label = track_name or repr(raw)

        if not artist_name:
            malformed_count += 1
            logger.warning("Skipping track '%s' — missing artist name", label)
            continue

        if not spotify_id:
            malformed_count += 1
            logger.warning(
                "Skipping track '%s' by '%s' — missing or invalid Spotify URI: %r",
                label,
                artist_name,
                uri,
            )
            continue

        if spotify_id in seen_ids:
            # Duplicate — skip, will count below
            continue

        seen_ids[spotify_id] = {
            "spotify_id": spotify_id,
            "name": track_name or "",
            "artist_name": artist_name,
            "album_name": album_name,
        }

    duplicate_count = len(raw_tracks) - malformed_count - len(seen_ids)
    if duplicate_count > 0:
        logger.info("Removed %d duplicate track IDs (kept first occurrence)", duplicate_count)

    tracks = sorted(seen_ids.values(), key=lambda t: t["artist_name"].lower())
    return tracks


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Parse a Spotify data export YourLibrary.json into deduplicated liked tracks."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to YourLibrary.json (overrides SPOTIFY_EXPORT_PATH env var and default path)",
    )
    args = parser.parse_args()

    export_path_str = (
        args.path
        or os.environ.get("SPOTIFY_EXPORT_PATH")
        or str(DEFAULT_EXPORT_PATH)
    )

    try:
        export_path = Path(export_path_str).expanduser().resolve()
    except Exception as e:
        print(f"ERROR: Invalid path '{export_path_str}': {e}")
        raise SystemExit(1)

    try:
        tracks = parse_liked_tracks(export_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)

    # Compute summary stats
    unique_artists = len({t["artist_name"] for t in tracks})

    # Count originals to derive skipped/duplicate counts
    with open(export_path, encoding="utf-8") as f:
        raw_data = json.load(f)
    try:
        tracks_key = _detect_tracks_key(raw_data)
        raw_count = len(raw_data[tracks_key])
    except ValueError:
        raw_count = 0

    parsed_count = len(tracks)
    total_skipped = raw_count - parsed_count

    print()
    print("=" * 50)
    print("Spotify Library Parse Summary")
    print("=" * 50)
    print(f"  Raw entries in export:    {raw_count:>6}")
    print(f"  Unique tracks parsed:     {parsed_count:>6}")
    print(f"  Entries skipped/removed:  {total_skipped:>6}  (malformed + duplicates)")
    print(f"  Unique artists:           {unique_artists:>6}")
    print("=" * 50)


if __name__ == "__main__":
    main()
