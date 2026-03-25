from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.country import CountryComparison, CountryDetail, CountryListItem
from app.services import country_service

router = APIRouter(prefix="/api/countries", tags=["countries"])


@router.get("", response_model=list[CountryListItem])
async def list_countries(db: AsyncSession = Depends(get_db)):
    return await country_service.get_country_list(db)


@router.get("/{country_id}", response_model=CountryDetail)
async def get_country(country_id: int, db: AsyncSession = Depends(get_db)):
    country = await country_service.get_country_detail(db, country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return country


@router.get("/{country_id}/comparison", response_model=CountryComparison)
async def get_country_comparison(country_id: int, db: AsyncSession = Depends(get_db)):
    comparison = await country_service.get_country_comparison(db, country_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return comparison
