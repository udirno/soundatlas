from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.artist import Artist


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    spotify_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    artist_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("artists.id"), nullable=True
    )
    album_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Audio features — all nullable (endpoint availability uncertain)
    energy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    danceability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tempo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acousticness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    instrumentalness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speechiness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liveness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    artist: Mapped[Optional["Artist"]] = relationship("Artist", back_populates="tracks")
