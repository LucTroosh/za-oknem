"""add noise_measurements (GIOŚ historical noise measurements, ADR-032 / GIOS-04)

Additive only (rule #4).

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "noise_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id", sa.Integer(), sa.ForeignKey("dataset_snapshots.id"), nullable=False
        ),
        sa.Column("natural_key", sa.String(length=64), nullable=False),
        sa.Column("point_code", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("voivodeship", sa.String(length=30), nullable=False),
        sa.Column("powiat", sa.String(length=60), nullable=True),
        sa.Column("gmina", sa.String(length=100), nullable=True),
        sa.Column("locality", sa.String(length=120), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("period_label", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=500), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("value_db", sa.Float(), nullable=False),
        sa.Column("exceedance_db", sa.Float(), nullable=True),
        sa.Column("raw", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.UniqueConstraint("snapshot_id", "natural_key", name="uq_noise_snapshot_key"),
    )
    op.create_index("ix_noise_measurements_snapshot_id", "noise_measurements", ["snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_noise_measurements_snapshot_id", table_name="noise_measurements")
    op.drop_table("noise_measurements")
