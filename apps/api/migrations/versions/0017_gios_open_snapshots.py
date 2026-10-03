"""add dataset_snapshots + ingest_quarantine (GIOŚ open-data foundation, ADR-032)

Additive only (rule #4): two new tables, no change to existing ones.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("filters_key", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("schema_hash", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("source_fetch_id", sa.Integer(), sa.ForeignKey("source_fetches.id")),
    )
    op.create_index(
        "ix_dataset_snapshots_source_fetch_id", "dataset_snapshots", ["source_fetch_id"]
    )
    # The run lock (one staging snapshot per service) and "one active snapshot per dataset" live in
    # the database, so two workers cannot both win.
    op.create_index(
        "uq_dataset_snapshot_staging",
        "dataset_snapshots",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("status = 'staging'"),
    )
    op.create_index(
        "uq_dataset_snapshot_active",
        "dataset_snapshots",
        ["source_id", "operation", "filters_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "ingest_quarantine",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("dataset_snapshots.id")),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("raw", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ingest_quarantine_snapshot_id", "ingest_quarantine", ["snapshot_id"])
    op.create_index("ix_ingest_quarantine_source_id", "ingest_quarantine", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_ingest_quarantine_source_id", table_name="ingest_quarantine")
    op.drop_index("ix_ingest_quarantine_snapshot_id", table_name="ingest_quarantine")
    op.drop_table("ingest_quarantine")
    op.drop_index("uq_dataset_snapshot_active", table_name="dataset_snapshots")
    op.drop_index("uq_dataset_snapshot_staging", table_name="dataset_snapshots")
    op.drop_index("ix_dataset_snapshots_source_fetch_id", table_name="dataset_snapshots")
    op.drop_table("dataset_snapshots")
