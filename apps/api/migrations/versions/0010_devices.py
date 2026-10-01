"""add devices table (ADR-017, TASK-10.1 device registration)

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=10), nullable=False),
        sa.Column("push_token", sa.String(length=255), nullable=True),
        sa.Column("observed_area_code", sa.String(length=7), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_devices_installation_id", "devices", ["installation_id"], unique=True)
    op.create_index("ix_devices_push_token", "devices", ["push_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_devices_push_token", table_name="devices")
    op.drop_index("ix_devices_installation_id", table_name="devices")
    op.drop_table("devices")
