"""IMGW station metadata; observations reuse Measurement (ADR-034)."""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imgw_weather_stations",
        sa.Column("source_id", sa.String(50), primary_key=True),
        sa.Column("station_id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("elevation_m", sa.Float()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("imgw_weather_stations")
