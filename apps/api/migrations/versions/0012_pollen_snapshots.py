"""add pollen_snapshots (ADR-020, TASK-8.6)

Revision ID: 0012
Revises: 0009
Create Date: 2026-10-01

down_revision points at the real head of main at PR time (0009); PR #67 (0010) and
#70 (0011) are in flight, so the coordinator re-points it after they merge.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pollen_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.String(length=150), nullable=False),
        sa.Column("geo_area_id", sa.Integer(), sa.ForeignKey("geo_areas.id"), nullable=False),
        sa.Column("alder", sa.Float(), nullable=True),
        sa.Column("birch", sa.Float(), nullable=True),
        sa.Column("grass", sa.Float(), nullable=True),
        sa.Column("mugwort", sa.Float(), nullable=True),
        sa.Column("ragweed", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=30), nullable=False),
        sa.Column("forecast_reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_fetch_id", sa.Integer(), sa.ForeignKey("source_fetches.id"), nullable=True
        ),
        sa.UniqueConstraint(
            "source_id", "source_record_id", name="uq_pollen_snapshot_source_record"
        ),
    )
    op.create_index("ix_pollen_snapshots_source_id", "pollen_snapshots", ["source_id"])
    op.create_index("ix_pollen_snapshots_geo_area_id", "pollen_snapshots", ["geo_area_id"])
    op.create_index(
        "ix_pollen_snapshots_forecast_reference_time",
        "pollen_snapshots",
        ["forecast_reference_time"],
    )
    op.create_index("ix_pollen_snapshots_valid_at", "pollen_snapshots", ["valid_at"])
    op.create_index("ix_pollen_snapshots_source_fetch_id", "pollen_snapshots", ["source_fetch_id"])


def downgrade() -> None:
    op.drop_table("pollen_snapshots")
