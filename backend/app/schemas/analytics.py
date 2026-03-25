from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    country_count: int
    artist_count: int
    track_count: int
    diversity_score: float
    top_genres: list[dict[str, Any]] = []
    top_countries: list[dict[str, Any]] = []


class GenreDistribution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    genre: str
    count: int


class FeatureAverages(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    energy: Optional[float] = None
    danceability: Optional[float] = None
    valence: Optional[float] = None
    tempo: Optional[float] = None
    acousticness: Optional[float] = None


class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    global_genres: list[GenreDistribution] = []
    country_id: Optional[int] = None
    country_genres: list[GenreDistribution] = []


class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    global_averages: FeatureAverages
    country_id: Optional[int] = None
    country_averages: Optional[FeatureAverages] = None
