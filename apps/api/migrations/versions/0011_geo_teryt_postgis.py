"""PostGIS + TERYT/boundary columns on geo_areas (ADR-019, TASK-6.2)

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-30

Needs no data: the new columns are nullable/defaulted, so the 7 seeded cities keep
working exactly as before (weather_polling_active defaults to true). Boundaries and
TERYT codes arrive later via the importer (app.connectors.prg_gminy.ingest).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
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


def _drop_imported_gminas() -> None:
    """Imported gminas (slug teryt-*) default to weather_polling_active=true once that
    column is re-added by a later upgrade, which would put ~2.5k rows into polling.
    So delete them on downgrade - but never a row some table still references (FK
    targets are read from the catalog, so tables added by later migrations, e.g.
    devices, are covered too) - and fail loudly if any remain."""
    conn = op.get_bind()
    quote = conn.dialect.identifier_preparer.quote
    refs = conn.execute(
        sa.text(
            "SELECT c.conrelid::regclass::text, a.attname FROM pg_constraint c "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1] "
            "WHERE c.contype = 'f' AND c.confrelid = 'geo_areas'::regclass"
        )
    ).all()
    unreferenced = "".join(
        f" AND NOT EXISTS (SELECT 1 FROM {table} r WHERE r.{quote(col)} = g.id)"
        for table, col in refs
    )
    conn.execute(sa.text(f"DELETE FROM geo_areas g WHERE left(g.slug, 6) = 'teryt-'{unreferenced}"))
    left = conn.execute(
        sa.text("SELECT count(*) FROM geo_areas WHERE left(slug, 6) = 'teryt-'")
    ).scalar()
    if left:
        raise RuntimeError(
            f"downgrade 0011 aborted: {left} imported gmina row(s) (slug 'teryt-*') are still "
            "referenced by other tables; remove those references first"
        )


def downgrade() -> None:
    _drop_imported_gminas()
    op.drop_column("geo_areas", "weather_polling_active")
    op.drop_index("ix_geo_areas_boundary", table_name="geo_areas")
    op.drop_column("geo_areas", "boundary")
    op.drop_constraint("uq_geo_area_teryt_code", "geo_areas", type_="unique")
    op.drop_column("geo_areas", "teryt_code")
    # The extension is deliberately left installed: dropping it is destructive for
    # anything else that started using it, and is harmless when unused.
