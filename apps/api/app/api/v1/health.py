from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.source_health import collect_source_health

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


class DailyBudgetOut(BaseModel):
    used: int
    limit: int
    used_pct: float


class SourceHealthOut(BaseModel):
    source_id: str
    freshness: Literal["FRESH", "RECENT", "STALE", "UNAVAILABLE"]
    last_attempt_at: str | None
    last_success_at: str | None
    last_error: str | None  # sanitized + truncated (ADR-012, TASK-13.1)
    daily_budget: DailyBudgetOut | None
    # False: source deliberately off (e.g. GIOS without GIOS_STATION_IDS) - not a fault.
    monitored: bool


class SourcesHealthResponse(BaseModel):
    generated_at: str
    sources: list[SourceHealthOut]


@router.get("/health/sources", response_model=SourcesHealthResponse)
def sources_health(db: Session = Depends(get_db)) -> dict:
    """Operator view (TASK-13.1): per-source freshness, last attempt/success/error
    and daily call budget. Reads only our DB (rule #14). Always 200 - it reports
    problems, it must not itself look like an unhealthy service (/health is the
    liveness probe and is untouched)."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": collect_source_health(db),
    }
