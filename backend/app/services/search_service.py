from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artist import Artist
from app.models.track import Track
from app.models.user_track import UserTrack

SIMILARITY_THRESHOLD = 0.15  # Lower than default 0.3 — music names are short/unusual


async def fuzzy_search(db: AsyncSession, q: str, limit: int = 20) -> dict:
    """Fuzzy search artists and tracks using PostgreSQL pg_trgm similarity."""
    # Handle edge cases
    if not q or not q.strip():
        return {"query": q or "", "artists": [], "tracks": []}

    q = q.strip()

    # Artist search query
    artist_stmt = (
        select(
            Artist.id,
            Artist.name,
            Artist.spotify_id,
            Artist.genres,
            Artist.image_url,
            func.similarity(Artist.name, q).label("score"),
        )
        .where(func.similarity(Artist.name, q) > SIMILARITY_THRESHOLD)
        .order_by(func.similarity(Artist.name, q).desc())
        .limit(limit)
    )

    # Correlated EXISTS subquery to determine if track is in user's library
    in_library_subq = (
        select(literal(True))
        .where(UserTrack.track_id == Track.id)
        .exists()
        .correlate(Track)
    )

    # Track search query with in_library signal
    track_stmt = (
        select(
            Track.id,
            Track.name,
            Track.spotify_id,
            Track.album_name,
            func.similarity(Track.name, q).label("score"),
            in_library_subq.label("in_library"),
        )
        .where(func.similarity(Track.name, q) > SIMILARITY_THRESHOLD)
        .order_by(func.similarity(Track.name, q).desc())
        .limit(limit)
    )

    artist_result = await db.execute(artist_stmt)
    track_result = await db.execute(track_stmt)

    artist_rows = artist_result.mappings().all()
    track_rows = track_result.mappings().all()

    return {
        "query": q,
        "artists": [dict(r) for r in artist_rows],
        "tracks": [dict(r) for r in track_rows],
    }
