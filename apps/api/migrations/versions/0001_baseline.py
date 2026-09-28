"""baseline (no domain models yet)

Revision ID: 0001
Revises:
Create Date: 2026-09-28

"""
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally empty: Phase 0 sets up the migration chain, domain models
    # (measurements, sources, geo_areas, ...) arrive in Phase 2/3.
    pass


def downgrade() -> None:
    pass
