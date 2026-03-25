from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.artist import ArtistDetail, ArtistListItem
from app.services import country_service

router = APIRouter(prefix="/api/artists", tags=["artists"])


@router.get("", response_model=list[ArtistListItem])
async def list_artists(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await country_service.get_artist_list(db, q)


@router.get("/{artist_id}", response_model=ArtistDetail)
async def get_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    artist = await country_service.get_artist_detail(db, artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist
