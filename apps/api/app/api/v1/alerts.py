from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert

router = APIRouter()

# ADR-009: scheduler polls this source every 1h (unverified real cadence, same
# assumption as hydro/ADR-008). fetched_at is when we last confirmed IMGW still
# reports this alert as active (ingest.py refreshes it on every reappearance),
# so its age - not the source's own valid_until, which can read year 9999 - is
# what tells a client whether our data is still trustworthy (rule #8).
FRESH_MAX_AGE = timedelta(hours=2)
RECENT_MAX_AGE = timedelta(hours=6)


def freshness(fetched_at: datetime) -> str:
    age = datetime.now(UTC) - fetched_at
    if age <= FRESH_MAX_AGE:
        return "FRESH"
    if age <= RECENT_MAX_AGE:
        return "RECENT"
    return "STALE"


@router.get("/alerts/latest")
def latest_alerts(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14). Currently-valid alerts only
    (valid_until in the future) - no geo-filtering to the user's location yet
    (ADR-009 non-goal), the client filters by `areas` itself for now. Every row
    carries `fetched_at`/`freshness` so a client can tell a genuinely-ongoing
    alert from one we simply haven't been able to refresh (rule #8) - an IMGW
    outage stops updating fetched_at long before any `valid_until` (up to year
    9999 for drought) would say so."""
    now = datetime.now(UTC)
    stmt = select(Alert).where(Alert.valid_until >= now).order_by(Alert.valid_until.desc())
    rows = db.execute(stmt).scalars().all()

    if not rows:
        return {"alerts": []}

    return {
        "alerts": [
            {
                "external_id": row.external_id,
                "source": row.source_id,
                "event_type": row.event_type,
                "severity_raw": row.severity_raw,
                "probability_pct": row.probability_pct,
                "issuing_office": row.issuing_office,
                "description": row.description,
                "comment": row.comment,
                "areas": row.areas,
                "valid_from": row.valid_from.isoformat(),
                "valid_until": row.valid_until.isoformat(),
                "published_at": row.published_at.isoformat(),
                "fetched_at": row.fetched_at.isoformat(),
                "freshness": freshness(row.fetched_at),
            }
            for row in rows
        ]
    }
