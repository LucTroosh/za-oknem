"""add forecasts table

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.String(length=150), nullable=False),
        sa.Column("geo_area_id", sa.Integer(), sa.ForeignKey("geo_areas.id"), nullable=False),
        sa.Column("param_code", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=30), nullable=False),
        sa.Column("forecast_reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "source_record_id", name="uq_forecast_source_record"),
    )
    op.create_index("ix_forecasts_source_id", "forecasts", ["source_id"])
    op.create_index("ix_forecasts_geo_area_id", "forecasts", ["geo_area_id"])
    op.create_index("ix_forecasts_param_code", "forecasts", ["param_code"])
    op.create_index("ix_forecasts_valid_from", "forecasts", ["valid_from"])


def downgrade() -> None:
    op.drop_table("forecasts")
