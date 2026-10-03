"""Paging for the new GIOŚ API (`numerStrony` from 0, `liczbaElementowNaStronie` up to 50).

The contract (02-development-contract.md) does NOT give a total: `liczbaRekordow` equalled the page
size in early samples (one noise probe saw the total; other operations unverified), so nothing
relies on it. A pass is complete only when a page comes back confirmed EMPTY; it is
guarded against the ways paging can lie:
- a page that repeats an earlier page (pager not advancing) -> GiosOpenPageLoopError;
- a record (natural key) on two pages (data moved while paging) -> GiosOpenPageOverlapError;
- `max_pages` reached with no empty page (our safety valve) -> GiosOpenPageLimitError.
A generator that finishes normally therefore means "complete pass"; any exception means the data
is NOT a snapshot and must not be promoted. A short page is NOT treated as the end (that would be
an optimization to adopt only once the live behaviour is confirmed, B-6).
"""

import hashlib
import json
from collections.abc import Callable, Iterator
from typing import Any

from app.config import settings
from app.gios_open.client import GiosOpenClient, Page
from app.gios_open.errors import (
    GiosOpenPageLimitError,
    GiosOpenPageLoopError,
    GiosOpenPageOverlapError,
)

PAGE_PARAM = "numerStrony"
SIZE_PARAM = "liczbaElementowNaStronie"


def page_hash(records: list[dict]) -> str:
    """Stable fingerprint of a page's content (also feeds the snapshot checksum)."""
    blob = json.dumps(
        records, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def iter_pages(
    client: GiosOpenClient,
    path: str,
    params: dict[str, Any] | None = None,
    *,
    page_size: int | None = None,
    max_pages: int | None = None,
    key_fn: Callable[[dict], Any] | None = None,
) -> Iterator[tuple[int, Page]]:
    """Yields `(page_number, page)` for every non-empty page; returns once an empty page is seen."""
    size = page_size if page_size is not None else settings.gios_open_page_size
    limit = max_pages if max_pages is not None else settings.gios_open_max_pages
    seen_hashes: dict[str, int] = {}
    seen_keys: dict[Any, int] = {}
    for number in range(limit):
        page = client.get_page(path, {**(params or {}), PAGE_PARAM: number, SIZE_PARAM: size})
        if not page.records:
            return  # confirmed empty page: the pass is complete
        digest = page_hash(page.records)
        if digest in seen_hashes:
            raise GiosOpenPageLoopError(
                f"page {number} repeats page {seen_hashes[digest]}: the pager is not advancing"
            )
        seen_hashes[digest] = number
        if key_fn is not None:
            for record in page.records:
                key = key_fn(record)
                if key in seen_keys:
                    raise GiosOpenPageOverlapError(
                        f"record {key!r} on page {number} was already on page {seen_keys[key]}"
                    )
                seen_keys[key] = number
        yield number, page
    raise GiosOpenPageLimitError(f"{limit} pages without an empty page: result would be incomplete")
