from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict


class ArtistListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    spotify_id: Optional[str] = None
    country_id: Optional[int] = None
    genres: Optional[list[str]] = None
    popularity: Optional[int] = None
    image_url: Optional[str] = None


class TrackListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    spotify_id: str
    album_name: Optional[str] = None
    energy: Optional[float] = None
    danceability: Optional[float] = None
    valence: Optional[float] = None
    tempo: Optional[float] = None
    acousticness: Optional[float] = None


class ArtistDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    spotify_id: Optional[str] = None
    country_id: Optional[int] = None
    genres: Optional[list[str]] = None
    popularity: Optional[int] = None
    image_url: Optional[str] = None
    tracks: list[TrackListItem] = []
