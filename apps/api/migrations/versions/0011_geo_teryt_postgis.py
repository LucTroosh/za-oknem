"""PostGIS + TERYT/boundary columns on geo_areas (ADR-019, TASK-6.2)

Revision ID: 0011
Revises: 0009
Create Date: 2026-09-30

NOTE: 0010 belongs to another PR. This migration points at 0009 (the head on main at
PR time); whoever merges second must re-point `down_revision` to "0010".

Needs no data: the new columns are nullable/defaulted, so the 7 seeded cities keep
working exactly as before (weather_polling_active defaults to true). Boundaries and
TERYT codes arrive later via the importer (app.connectors.prg_gminy.ingest).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Requires a role allowed to create the extension (superuser / `postgres` in the
    # compose + CI image postgis/postgis:16-3.4) - see ADR-019 for managed Postgres.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.add_column("geo_areas", sa.Column("teryt_code", sa.String(length=7), nullable=True))
    op.create_unique_constraint("uq_geo_area_teryt_code", "geo_areas", ["teryt_code"])
    # Raw DDL: the geometry type is PostGIS's, not SQLAlchemy's (no geoalchemy2, ADR-019).
    op.execute("ALTER TABLE geo_areas ADD COLUMN boundary geometry(MultiPolygon,4326)")
    op.create_index("ix_geo_areas_boundary", "geo_areas", ["boundary"], postgresql_using="gist")
    op.add_column(
        "geo_areas",
        sa.Column(
            "weather_polling_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("geo_areas", "weather_polling_active")
    op.drop_index("ix_geo_areas_boundary", table_name="geo_areas")
    op.drop_column("geo_areas", "boundary")
    op.drop_constraint("uq_geo_area_teryt_code", "geo_areas", type_="unique")
    op.drop_column("geo_areas", "teryt_code")
    # The extension is deliberately left installed: dropping it is destructive for
    # anything else that started using it, and is harmless when unused.
