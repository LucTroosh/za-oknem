"""forecasts.granularity: daily | hourly (ADR-030)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-02

Every existing row is a daily forecast, so the server default backfills them correctly.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "forecasts",
        sa.Column("granularity", sa.String(length=10), nullable=False, server_default="daily"),
    )
    op.create_check_constraint(
        "ck_forecast_granularity", "forecasts", "granularity IN ('daily', 'hourly')"
    )
    # The daily retention purge filters granularity + a valid_until range.
    op.create_index(
        "ix_forecasts_granularity_valid_until", "forecasts", ["granularity", "valid_until"]
    )


def downgrade() -> None:
    # Hourly rows have no place in the old (daily-only) schema: drop them first.
    op.execute("DELETE FROM forecasts WHERE granularity = 'hourly'")
    op.drop_index("ix_forecasts_granularity_valid_until", table_name="forecasts")
    op.drop_constraint("ck_forecast_granularity", "forecasts", type_="check")
    op.drop_column("forecasts", "granularity")
