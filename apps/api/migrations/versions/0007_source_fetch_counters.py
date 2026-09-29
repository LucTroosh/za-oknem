"""add source_fetch_counters table (ADR-001/ADR-003/ADR-004 daily call budget)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_fetch_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("source_id", "day", name="uq_source_fetch_counter_day"),
    )
    op.create_index("ix_source_fetch_counters_source_id", "source_fetch_counters", ["source_id"])
    op.create_index("ix_source_fetch_counters_day", "source_fetch_counters", ["day"])


def downgrade() -> None:
    op.drop_table("source_fetch_counters")
