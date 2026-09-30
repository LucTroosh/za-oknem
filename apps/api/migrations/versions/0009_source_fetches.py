"""add source_fetches + source_fetch_id provenance FK (ADR-014, TASK-3.1)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Existing rows keep source_fetch_id NULL (they predate raw ingestion) - no backfill.
LINKED_TABLES = ("measurements", "alerts", "weather_snapshots", "forecasts")


def upgrade() -> None:
    op.create_table(
        "source_fetches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parser_version", sa.String(length=30), nullable=False),
        sa.Column("validation_status", sa.String(length=20), nullable=False),
        sa.Column(
            "payload",
            sa.JSON(none_as_null=True).with_variant(
                postgresql.JSONB(none_as_null=True), "postgresql"
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_source_fetches_source_id", "source_fetches", ["source_id"])
    op.create_index("ix_source_fetches_fetched_at", "source_fetches", ["fetched_at"])
    for table in LINKED_TABLES:
        op.add_column(
            table,
            sa.Column(
                "source_fetch_id",
                sa.Integer(),
                sa.ForeignKey("source_fetches.id"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{table}_source_fetch_id", table, ["source_fetch_id"])


def downgrade() -> None:
    for table in LINKED_TABLES:
        op.drop_index(f"ix_{table}_source_fetch_id", table_name=table)
        op.drop_column(table, "source_fetch_id")
    op.drop_table("source_fetches")
