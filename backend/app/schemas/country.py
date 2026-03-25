from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.artist import ArtistListItem, TrackListItem


class CountryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iso_alpha2: str
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    artist_count: int = 0
    track_count: int = 0
    top_genre: Optional[str] = None


class CountryDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iso_alpha2: str
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    artists: list[ArtistListItem] = []
    genre_breakdown: dict[str, int] = {}
    audio_feature_averages: dict[str, Optional[float]] = {}
    top_tracks: list[TrackListItem] = []


class CountryComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iso_alpha2: str
    country_averages: dict[str, Optional[float]]
    global_averages: dict[str, Optional[float]]
