from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import DashboardStats, FeatureResponse, GenreResponse
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    """Return global stats: country count, artist count, track count, diversity score, top genres, top countries."""
    data = await analytics_service.get_dashboard_stats(db)
    return DashboardStats(**data)


@router.get("/genres", response_model=GenreResponse)
async def get_genres(
    country_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> GenreResponse:
    """Return global genre distribution and optional per-country genre distribution."""
    data = await analytics_service.get_genre_distribution(db, country_id)
    return GenreResponse(**data)


@router.get("/features", response_model=FeatureResponse)
async def get_features(
    country_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> FeatureResponse:
    """Return global audio feature averages and optional per-country averages."""
    data = await analytics_service.get_feature_averages(db, country_id)
    return FeatureResponse(**data)
