"""add alerts table

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-29

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.String(length=150), nullable=False),
        sa.Column("external_id", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("severity_raw", sa.String(length=20), nullable=False),
        sa.Column("probability_pct", sa.Float(), nullable=True),
        sa.Column("issuing_office", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("areas", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "source_record_id", name="uq_alert_source_record"),
    )
    op.create_index("ix_alerts_source_id", "alerts", ["source_id"])


def downgrade() -> None:
    op.drop_table("alerts")
