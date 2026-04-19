from __future__ import annotations

import math
from collections import Counter
from typing import Optional

from sqlalchemy import distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artist import Artist
from app.models.country import Country
from app.models.track import Track


def calculate_diversity_score(country_artist_counts: list[int]) -> float:
    """Shannon entropy normalized to [0, 1]."""
    total = sum(country_artist_counts)
    if total == 0:
        return 0.0
    # Filter to non-zero counts
    counts = [c for c in country_artist_counts if c > 0]
    n = len(counts)
    if n <= 1:
        return 0.0
    entropy = -sum((c / total) * math.log(c / total) for c in counts)
    max_entropy = math.log(n)
    return round(entropy / max_entropy, 4)


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Return global counts, diversity score, top genres, top countries."""
    # Query 1: Global counts — separate queries to avoid undercounting unmapped artists/tracks
    country_count = (await db.execute(
        select(func.count(func.distinct(Artist.country_id))).where(Artist.country_id.is_not(None))
    )).scalar_one()
    artist_count = (await db.execute(select(func.count(Artist.id)))).scalar_one()
    track_count = (await db.execute(select(func.count(Track.id)))).scalar_one()

    # Query 2: Per-country artist counts for diversity score
    per_country_stmt = (
        select(func.count(Artist.id).label("cnt"))
        .where(Artist.country_id.is_not(None))
        .group_by(Artist.country_id)
    )
    per_country_scalars = (await db.execute(per_country_stmt)).scalars().all()
    diversity_score = calculate_diversity_score(list(per_country_scalars))

    # Query 3: Top genres (global) — load all artists with genres, flatten, Counter, top 10
    artists_stmt = select(Artist.genres).where(Artist.genres.is_not(None))
    rows = (await db.execute(artists_stmt)).scalars().all()
    all_genres: list[str] = []
    for genres_list in rows:
        if genres_list:
            all_genres.extend(genres_list)
    top_genres = [
        {"genre": g, "count": c} for g, c in Counter(all_genres).most_common(10)
    ]

    # Query 4: Top countries by artist count — top 10
    top_countries_stmt = (
        select(
            Country.id,
            Country.name,
            Country.iso_alpha2,
            func.count(Artist.id).label("artist_count"),
        )
        .join(Artist, Artist.country_id == Country.id)
        .group_by(Country.id)
        .order_by(func.count(Artist.id).desc())
        .limit(10)
    )
    top_countries_rows = (await db.execute(top_countries_stmt)).all()
    top_countries = [
        {
            "id": row.id,
            "name": row.name,
            "iso_alpha2": row.iso_alpha2,
            "artist_count": row.artist_count,
        }
        for row in top_countries_rows
    ]

    return {
        "country_count": country_count,
        "artist_count": artist_count,
        "track_count": track_count,
        "diversity_score": diversity_score,
        "top_genres": top_genres,
        "top_countries": top_countries,
    }


async def get_genre_distribution(
    db: AsyncSession, country_id: Optional[int] = None
) -> dict:
    """Return global genre distribution and optionally per-country genre distribution."""
    # Global genres via raw SQL unnest
    global_stmt = text("""
        SELECT unnest(genres) AS genre, COUNT(*) AS count
        FROM artists
        WHERE genres IS NOT NULL
        GROUP BY genre
        ORDER BY count DESC
        LIMIT 20
    """)
    global_rows = (await db.execute(global_stmt)).all()
    global_genres = [{"genre": row.genre, "count": row.count} for row in global_rows]

    # Per-country genres if country_id provided
    country_genres: list[dict] = []
    if country_id is not None:
        country_stmt = text("""
            SELECT unnest(genres) AS genre, COUNT(*) AS count
            FROM artists
            WHERE country_id = :cid AND genres IS NOT NULL
            GROUP BY genre
            ORDER BY count DESC
            LIMIT 20
        """).bindparams(cid=country_id)
        country_rows = (await db.execute(country_stmt)).all()
        country_genres = [
            {"genre": row.genre, "count": row.count} for row in country_rows
        ]

    return {
        "global_genres": global_genres,
        "country_id": country_id,
        "country_genres": country_genres,
    }


async def get_feature_averages(
    db: AsyncSession, country_id: Optional[int] = None
) -> dict:
    """Return global audio feature averages and optionally per-country averages."""
    # Global averages
    global_stmt = select(
        func.avg(Track.energy).label("energy"),
        func.avg(Track.danceability).label("danceability"),
        func.avg(Track.valence).label("valence"),
        func.avg(Track.tempo).label("tempo"),
        func.avg(Track.acousticness).label("acousticness"),
    )
    global_row = (await db.execute(global_stmt)).one()
    global_averages = {
        "energy": global_row.energy,
        "danceability": global_row.danceability,
        "valence": global_row.valence,
        "tempo": global_row.tempo,
        "acousticness": global_row.acousticness,
    }

    # Per-country averages if country_id provided
    country_averages = None
    if country_id is not None:
        country_stmt = (
            select(
                func.avg(Track.energy).label("energy"),
                func.avg(Track.danceability).label("danceability"),
                func.avg(Track.valence).label("valence"),
                func.avg(Track.tempo).label("tempo"),
                func.avg(Track.acousticness).label("acousticness"),
            )
            .join(Artist, Track.artist_id == Artist.id)
            .where(Artist.country_id == country_id)
        )
        country_row = (await db.execute(country_stmt)).one()
        country_averages = {
            "energy": country_row.energy,
            "danceability": country_row.danceability,
            "valence": country_row.valence,
            "tempo": country_row.tempo,
            "acousticness": country_row.acousticness,
        }

    return {
        "global_averages": global_averages,
        "country_id": country_id,
        "country_averages": country_averages,
    }
