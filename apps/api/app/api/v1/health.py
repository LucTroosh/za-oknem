from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Data contract per TASK-0.1: {"status": "ok"}. Liveness only — is the
    process up, not "is it ready to serve traffic" (that's /health/ready)."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness: can we actually reach Postgres? For orchestration (don't route
    traffic here until this is true) — additive, doesn't change /health's contract."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc
    return {"status": "ok"}
