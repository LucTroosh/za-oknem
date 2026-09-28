"""add geo_areas table + seed (ADR-005)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-28

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Manually-chosen seed (ADR-005) — flat stand-in for full TERYT, not an exhaustive
# list. Kłodzko matches the existing GIOŚ station's coordinates for continuity.
_SEED_AREAS = [
    {"slug": "klodzko", "name": "Kłodzko", "latitude": 50.433493, "longitude": 16.65366},
    {"slug": "warszawa", "name": "Warszawa", "latitude": 52.2297, "longitude": 21.0122},
    {"slug": "krakow", "name": "Kraków", "latitude": 50.0647, "longitude": 19.9450},
    {"slug": "wroclaw", "name": "Wrocław", "latitude": 51.1079, "longitude": 17.0385},
    {"slug": "gdansk", "name": "Gdańsk", "latitude": 54.3520, "longitude": 18.6466},
    {"slug": "poznan", "name": "Poznań", "latitude": 52.4064, "longitude": 16.9252},
    {"slug": "lodz", "name": "Łódź", "latitude": 51.7592, "longitude": 19.4560},
]


def upgrade() -> None:
    geo_areas = op.create_table(
        "geo_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_geo_area_slug"),
    )
    op.create_index("ix_geo_areas_slug", "geo_areas", ["slug"])
    op.bulk_insert(geo_areas, _SEED_AREAS)


def downgrade() -> None:
    op.drop_table("geo_areas")
