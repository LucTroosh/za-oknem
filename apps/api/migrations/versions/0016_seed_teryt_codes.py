"""TERYT codes for the 7 seeded cities (ADR-005 seed, ADR-013 alert matching)

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-02

Alert -> area matching (app/alert_geo.py) needs `geo_areas.teryt_code`: an area without one makes
EVERY alert `unresolved` ("cannot tell", shown but flagged), so a user in Wrocław saw dolnośląskie
warnings only under "do sprawdzenia". The code normally arrives with the PRG gmina import
(ADR-019, gate #15 still open), which links seeds by point-in-polygon. Until then the seeds get
their official 7-digit GUS TERYT gmina codes here (GUS "Wykaz identyfikatorów i nazw jednostek
podziału terytorialnego kraju"; every code below was confirmed against that register).

Safe with the later PRG import: a seed that already holds the right code is updated by code
(`WHERE teryt_code = :code`, seed name/coordinates are kept), a wrong code would simply be
re-adopted. Idempotent and guarded against the UNIQUE constraint: an existing row that already
holds the code (e.g. an imported `teryt-*` gmina) wins and the seed stays unlinked.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# slug (migration 0003) -> GUS TERYT gmina code. Kłodzko = gmina MIEJSKA (0208021); the rural
# gmina of the same name is 0208072 and is a different unit.
SEED_TERYT: dict[str, str] = {
    "klodzko": "0208021",
    "warszawa": "1465011",
    "krakow": "1261011",
    "wroclaw": "0264011",
    "gdansk": "2261011",
    "poznan": "3064011",
    "lodz": "1061011",
}


def upgrade() -> None:
    conn = op.get_bind()
    for slug, code in SEED_TERYT.items():
        conn.execute(
            sa.text(
                "UPDATE geo_areas SET teryt_code = :code "
                "WHERE slug = :slug AND teryt_code IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM geo_areas o WHERE o.teryt_code = :code)"
            ),
            {"slug": slug, "code": code},
        )


def downgrade() -> None:
    # Only seeds that were not adopted by a PRG import (no boundary) go back to unlinked.
    conn = op.get_bind()
    for slug, code in SEED_TERYT.items():
        conn.execute(
            sa.text(
                "UPDATE geo_areas SET teryt_code = NULL "
                "WHERE slug = :slug AND teryt_code = :code AND boundary IS NULL"
            ),
            {"slug": slug, "code": code},
        )
