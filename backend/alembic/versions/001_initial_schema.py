"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension FIRST (required for trgm indexes)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create countries table
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("iso_alpha2", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso_alpha2"),
    )
    op.create_index("ix_countries_iso_alpha2", "countries", ["iso_alpha2"])

    # Create artists table
    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("spotify_id", sa.String(length=50), nullable=True),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("genres", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("popularity", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "mb_resolution_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("mb_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spotify_id"),
    )
    op.create_index("ix_artists_spotify_id", "artists", ["spotify_id"])
    op.create_index("ix_artists_mb_resolution_status", "artists", ["mb_resolution_status"])
    # GIN index on genres array for array containment queries
    op.execute("CREATE INDEX ix_artists_genres_gin ON artists USING gin (genres)")
    # Trigram GIN index on artist name for fuzzy search
    op.execute("CREATE INDEX ix_artists_name_trgm ON artists USING gin (name gin_trgm_ops)")

    # Create tracks table
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("spotify_id", sa.String(length=50), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=True),
        sa.Column("album_name", sa.String(length=500), nullable=True),
        # Audio features — all nullable
        sa.Column("energy", sa.Float(), nullable=True),
        sa.Column("danceability", sa.Float(), nullable=True),
        sa.Column("valence", sa.Float(), nullable=True),
        sa.Column("tempo", sa.Float(), nullable=True),
        sa.Column("acousticness", sa.Float(), nullable=True),
        sa.Column("instrumentalness", sa.Float(), nullable=True),
        sa.Column("speechiness", sa.Float(), nullable=True),
        sa.Column("liveness", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spotify_id"),
    )
    op.create_index("ix_tracks_spotify_id", "tracks", ["spotify_id"])
    # Trigram GIN index on track name for fuzzy search
    op.execute("CREATE INDEX ix_tracks_name_trgm ON tracks USING gin (name gin_trgm_ops)")

    # Create user_tracks table
    op.create_table(
        "user_tracks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_tracks_track_id", "user_tracks", ["track_id"])
    op.create_index("ix_user_tracks_artist_id", "user_tracks", ["artist_id"])

    # Create ai_query_log table
    op.create_table(
        "ai_query_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ai_query_log")
    op.drop_table("user_tracks")
    op.drop_table("tracks")
    op.drop_table("artists")
    op.drop_table("countries")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
