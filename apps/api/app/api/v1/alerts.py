from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert

router = APIRouter()


@router.get("/alerts/latest")
def latest_alerts(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14). Currently-valid alerts only
    (valid_until in the future) - no geo-filtering to the user's location yet
    (ADR-009 non-goal), the client filters by `areas` itself for now."""
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
            }
            for row in rows
        ]
    }
