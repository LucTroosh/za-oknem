"""add weather_snapshots table

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.String(length=150), nullable=False),
        sa.Column("geo_area_id", sa.Integer(), sa.ForeignKey("geo_areas.id"), nullable=False),
        sa.Column("param_code", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_id", "source_record_id", name="uq_weather_snapshot_source_record"
        ),
    )
    op.create_index("ix_weather_snapshots_source_id", "weather_snapshots", ["source_id"])
    op.create_index("ix_weather_snapshots_geo_area_id", "weather_snapshots", ["geo_area_id"])
    op.create_index("ix_weather_snapshots_param_code", "weather_snapshots", ["param_code"])


def downgrade() -> None:
    op.drop_table("weather_snapshots")
