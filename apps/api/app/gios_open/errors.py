"""Error types of the GIOŚ open-data foundation. One base class so a connector can isolate a
whole source with a single `except GiosOpenError` (rule #1) and still tell the cases apart."""


class GiosOpenError(Exception):
    """Base class: anything that makes a fetch/paging/snapshot run unusable."""


class GiosOpenTransportError(GiosOpenError):
    """No usable HTTP answer (timeout, connection error, 429/5xx after the retries, other 4xx)."""


class GiosOpenSourceError(GiosOpenError):
    """The source answered HTTP 200 but with `wynik.status = BLAD`. Verified live 2026-10-03: a bad
    voivodeship value or a missing required filter returns exactly this. It is an ERROR, never an
    empty result, and it is not retried (a validation error would only repeat)."""

    def __init__(self, code: str | None, description: str | None, event_id: str | None = None):
        self.code = code
        self.description = description
        self.event_id = event_id
        super().__init__(f"source error {code}: {description} (event {event_id})")


class GiosOpenContractError(GiosOpenError):
    """The body is not an envelope we know (not JSON, no `dane`, unknown `wynik.status`, ...)."""


class GiosOpenPageLoopError(GiosOpenError):
    """A page repeated an earlier page (the pager is not advancing): the run must not finish."""


class GiosOpenPageOverlapError(GiosOpenError):
    """The same record (natural key) showed up on two pages: the data moved while we paged,
    or paging is not stable. The pass is not a consistent snapshot."""


class GiosOpenPageLimitError(GiosOpenError):
    """`max_pages` reached without a confirmed empty page: the result would be incomplete."""


class SnapshotLockedError(GiosOpenError):
    """Another run of the same service is in progress (one staging snapshot per service)."""


class SnapshotLostError(GiosOpenError):
    """This run's staging snapshot is no longer ours (its lock expired and another run took it
    over). It must not promote: the newer run owns the dataset."""
