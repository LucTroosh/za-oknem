"""GIOŚ provider index, separate from measurements and derived EEA index (ADR-033)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gios_provider_indices",
        sa.Column("station_id", sa.String(50), primary_key=True),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql")),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
        sa.Column("source_fetch_id", sa.Integer(), sa.ForeignKey("source_fetches.id")),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_succeeded", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_gios_provider_indices_source_fetch_id", "gios_provider_indices", ["source_fetch_id"]
    )


def downgrade() -> None:
    op.drop_table("gios_provider_indices")
