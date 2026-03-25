"""
Service layer for country and artist data queries.
All functions are flat async functions (not a class).
Each takes AsyncSession as first param.
"""
import collections
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Artist, Country, Track


async def get_country_list(db: AsyncSession) -> list[dict]:
    """
    Return list of countries with artist_count, track_count, and top_genre.
    Uses two queries:
    1. Aggregate counts (fast)
    2. Relationship load for genre computation
    """
    # Query 1: counts via outerjoin
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
        .group_by(
            Country.id,
            Country.name,
            Country.iso_alpha2,
            Country.latitude,
            Country.longitude,
        )
        .order_by(func.count(Artist.id.distinct()).desc())
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()

    # Convert to mutable dicts; initialize top_genre as None
    country_dicts: list[dict] = [dict(r) | {"top_genre": None} for r in rows]
    country_index: dict[int, dict] = {d["id"]: d for d in country_dicts}

    # Query 2: load artists with genres to compute top_genre per country
    genre_stmt = select(Country).options(selectinload(Country.artists))
    genre_result = await db.execute(genre_stmt)
    countries_with_artists = genre_result.scalars().all()

    for country in countries_with_artists:
        if country.id not in country_index:
            continue
        all_genres: list[str] = []
        for artist in country.artists:
            all_genres.extend(artist.genres or [])
        if all_genres:
            most_common = collections.Counter(all_genres).most_common(1)
            country_index[country.id]["top_genre"] = most_common[0][0]

    return country_dicts


async def get_country_detail(db: AsyncSession, country_id: int) -> dict | None:
    """
    Return detailed country dict including artists, genre_breakdown,
    and audio_feature_averages. Returns None if country not found.
    """
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

    # Compute genre_breakdown — top 10
    all_genres: list[str] = []
    for artist in country.artists:
        all_genres.extend(artist.genres or [])
    genre_breakdown = dict(
        collections.Counter(all_genres).most_common(10)
    )

    # Compute audio_feature_averages for the five features
    features = ["energy", "danceability", "valence", "tempo", "acousticness"]
    feature_values: dict[str, list[float]] = {f: [] for f in features}

    for artist in country.artists:
        for track in artist.tracks:
            for feature in features:
                val = getattr(track, feature, None)
                if val is not None:
                    feature_values[feature].append(val)

    audio_feature_averages: dict[str, Optional[float]] = {}
    for feature in features:
        vals = feature_values[feature]
        audio_feature_averages[feature] = sum(vals) / len(vals) if vals else None

    return {
        "id": country.id,
        "name": country.name,
        "iso_alpha2": country.iso_alpha2,
        "latitude": country.latitude,
        "longitude": country.longitude,
        "artists": country.artists,  # ORM objects — Pydantic handles serialization
        "genre_breakdown": genre_breakdown,
        "audio_feature_averages": audio_feature_averages,
    }


async def get_country_comparison(db: AsyncSession, country_id: int) -> dict | None:
    """
    Return country audio feature averages vs global averages.
    Returns None if country not found.
    """
    features = ["energy", "danceability", "valence", "tempo", "acousticness"]

    # Verify the country exists
    country_stmt = select(Country).where(Country.id == country_id)
    country_result = await db.execute(country_stmt)
    country = country_result.scalar_one_or_none()

    if country is None:
        return None

    # Country-level averages via SQL AVG
    country_avg_stmt = select(
        func.avg(Track.energy).label("energy"),
        func.avg(Track.danceability).label("danceability"),
        func.avg(Track.valence).label("valence"),
        func.avg(Track.tempo).label("tempo"),
        func.avg(Track.acousticness).label("acousticness"),
    ).join(Artist, Track.artist_id == Artist.id).where(
        Artist.country_id == country_id
    )
    country_avg_result = await db.execute(country_avg_stmt)
    country_row = country_avg_result.mappings().one()

    # Global averages via SQL AVG
    global_avg_stmt = select(
        func.avg(Track.energy).label("energy"),
        func.avg(Track.danceability).label("danceability"),
        func.avg(Track.valence).label("valence"),
        func.avg(Track.tempo).label("tempo"),
        func.avg(Track.acousticness).label("acousticness"),
    )
    global_avg_result = await db.execute(global_avg_stmt)
    global_row = global_avg_result.mappings().one()

    # Convert Decimal/None to float/None
    def to_float(val) -> Optional[float]:
        return float(val) if val is not None else None

    country_averages = {f: to_float(country_row[f]) for f in features}
    global_averages = {f: to_float(global_row[f]) for f in features}

    return {
        "id": country.id,
        "name": country.name,
        "iso_alpha2": country.iso_alpha2,
        "country_averages": country_averages,
        "global_averages": global_averages,
    }


async def get_artist_list(db: AsyncSession, q: Optional[str] = None) -> list:
    """
    Return list of ORM Artist objects, optionally filtered by name.
    """
    stmt = select(Artist).options(selectinload(Artist.country)).order_by(Artist.name)

    if q is not None:
        stmt = stmt.where(Artist.name.ilike(f"%{q}%"))

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_artist_detail(db: AsyncSession, artist_id: int):
    """
    Return a single ORM Artist object with tracks and country loaded.
    Returns None if not found.
    """
    stmt = (
        select(Artist)
        .where(Artist.id == artist_id)
        .options(
            selectinload(Artist.tracks),
            selectinload(Artist.country),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
