"""add measurements table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.String(length=150), nullable=False),
        sa.Column("station_id", sa.String(length=50), nullable=False),
        sa.Column("station_name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("param_code", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_id", "source_record_id", name="uq_measurement_source_record"
        ),
    )
    op.create_index("ix_measurements_source_id", "measurements", ["source_id"])
    op.create_index("ix_measurements_station_id", "measurements", ["station_id"])
    op.create_index("ix_measurements_param_code", "measurements", ["param_code"])


def downgrade() -> None:
    op.drop_table("measurements")
