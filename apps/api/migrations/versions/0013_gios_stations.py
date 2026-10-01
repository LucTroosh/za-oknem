"""add gios_stations (cached GIOŚ station catalog, ADR-024)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gios_stations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("station_id", sa.String(length=50), nullable=False),
        sa.Column("station_name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("raw", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fetch_id", sa.Integer(), sa.ForeignKey("source_fetches.id")),
        sa.UniqueConstraint("station_id", name="uq_gios_station_id"),
    )
    op.create_index("ix_gios_stations_source_fetch_id", "gios_stations", ["source_fetch_id"])


def downgrade() -> None:
    op.drop_index("ix_gios_stations_source_fetch_id", table_name="gios_stations")
    op.drop_table("gios_stations")
