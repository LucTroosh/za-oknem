"""places registry + geo_areas.place_id / last_requested_at (ADR-029)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-01

Needs no data: `places` starts empty (filled by `app.connectors.geonames_places.ingest`),
the new geo_areas columns are nullable, so seeded cities and imported gminas are untouched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("admin1_code", sa.String(length=10), nullable=True),
        sa.Column("admin2_code", sa.String(length=20), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.String(length=50), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "source_record_id", name="uq_place_source_record"),
    )
    # varchar_pattern_ops: lets `normalized_name LIKE 'prefix%'` use the index under any
    # collation (deterministic prefix search without pg_trgm/unaccent, ADR-029).
    op.create_index(
        "ix_places_normalized_name",
        "places",
        ["normalized_name"],
        postgresql_ops={"normalized_name": "varchar_pattern_ops"},
    )
    op.add_column(
        "geo_areas", sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True)
    )
    op.add_column(
        "geo_areas", sa.Column("last_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_unique_constraint("uq_geo_area_place_id", "geo_areas", ["place_id"])


def downgrade() -> None:
    # Areas created from places lose their link; stop polling them, or nothing would ever
    # expire them again (expiry keys on place_id). Rows stay (snapshots reference them).
    op.execute("UPDATE geo_areas SET weather_polling_active = false WHERE place_id IS NOT NULL")
    op.drop_constraint("uq_geo_area_place_id", "geo_areas", type_="unique")
    op.drop_column("geo_areas", "last_requested_at")
    op.drop_column("geo_areas", "place_id")
    op.drop_index("ix_places_normalized_name", table_name="places")
    op.drop_table("places")
