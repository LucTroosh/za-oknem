"""Two national JSON requests; bounded retries, no per-user upstream fetch."""

import random
import time
import zlib
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

BASE = "https://danepubliczne.imgw.pl/api/data/"


def fetch(dataset: str) -> list[dict]:
    if dataset not in ("synop", "meteo"):
        raise ValueError("unsupported dataset")
    last: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.get(BASE + dataset, timeout=httpx.Timeout(15, connect=5))
            response.raise_for_status()
            raw = response.json()
            if not isinstance(raw, list) or not raw or any(not isinstance(r, dict) for r in raw):
                raise ValueError("expected nonempty station list")
            return raw
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
            if attempt < 2:
                time.sleep(2**attempt + random.random())
    raise RuntimeError(f"IMGW {dataset} fetch failed") from last


@contextmanager
def job_lock(db: Session, source: str) -> Iterator[bool]:
    """Dedicated connection keeps the advisory lock across provenance/batch commits."""
    if db.get_bind().dialect.name != "postgresql":
        yield True  # unit tests only; production is PostgreSQL
        return
    key = zlib.crc32(("za-oknem:" + source).encode())
    with db.get_bind().engine.connect() as connection:
        locked = connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
        try:
            yield bool(locked)
        finally:
            if locked:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
