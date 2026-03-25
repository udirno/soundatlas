from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict


class SearchArtistHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    spotify_id: Optional[str] = None
    genres: Optional[list[str]] = None
    image_url: Optional[str] = None
    score: float


class SearchTrackHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    spotify_id: Optional[str] = None
    album_name: Optional[str] = None
    score: float
    in_library: bool


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    artists: list[SearchArtistHit] = []
    tracks: list[SearchTrackHit] = []
