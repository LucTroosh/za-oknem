from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Data contract per TASK-0.1: {"status": "ok"}. No DB/Redis check yet —
    that's a real design decision (liveness vs readiness) for when connectors exist."""
    return {"status": "ok"}
