"""Add region column to countries

Revision ID: 002
Revises: 001
Create Date: 2026-03-24

NOTE: Run inside Docker:
    docker compose exec backend alembic upgrade head
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("countries", sa.Column("region", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("countries", "region")
