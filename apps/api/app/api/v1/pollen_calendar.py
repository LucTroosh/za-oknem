"""GET /api/v1/pollen/calendar - typical pollen seasons for a date (ADR-023).

Static reference data from a repo file (rule #14: no external call). Explicitly NOT a
measurement and NOT a forecast (rule #7) - see `kind` and `disclaimer`.
"""

from datetime import UTC, datetime
from datetime import date as Date  # the response field `date` shadows the name in the class
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.pollen_calendar import (
    UPCOMING_DAYS,
    ActiveTaxon,
    NotCovered,
    Source,
    UpcomingTaxon,
    load_calendar,
    select,
)

router = APIRouter()

WARSAW = ZoneInfo("Europe/Warsaw")
MIN_YEAR, MAX_YEAR = 2000, 2100  # date arithmetic stays far from date.max/min


COVERAGE_WARNING = "Lista nie obejmuje wszystkich alergenów; brak wpisu NIE oznacza braku pylenia."
EMPTY_ACTIVE_MESSAGE = (
    "Żaden z ujętych taksonów nie jest w typowym sezonie, ale to NIE znaczy, że nic nie pyli: "
    "kalendarz nie obejmuje wszystkich alergenów, a rzeczywiste pylenie zależy od pogody."
)


class PollenCalendarOut(BaseModel):
    date: Date
    kind: Literal["seasonal_calendar"]  # NOT a measurement, NOT a forecast
    region: Literal["PL"]
    active: list[ActiveTaxon]
    active_message: str | None  # set when `active` is empty: that is NOT "nothing pollinates"
    upcoming: list[UpcomingTaxon]
    upcoming_within_days: int
    coverage_complete: Literal[False]  # the list never covers all allergens
    coverage_warning: str
    not_covered: list[NotCovered]
    sources: dict[str, Source]
    attribution: str
    disclaimer: str
    reviewed_at: Date


@router.get("/pollen/calendar", response_model=PollenCalendarOut)
def pollen_calendar(
    on: Date | None = Query(
        None, alias="date", description="YYYY-MM-DD; default: today (Europe/Warsaw)"
    ),
) -> PollenCalendarOut:
    d = on or datetime.now(UTC).astimezone(WARSAW).date()
    if not MIN_YEAR <= d.year <= MAX_YEAR:
        raise HTTPException(422, f"date year must be {MIN_YEAR}-{MAX_YEAR}")
    cal = load_calendar()
    active, upcoming = select(cal, d)
    return PollenCalendarOut(
        date=d,
        kind=cal.kind,
        region=cal.valid_for_region,
        active=active,
        active_message=None if active else EMPTY_ACTIVE_MESSAGE,
        upcoming=upcoming,
        upcoming_within_days=UPCOMING_DAYS,
        coverage_complete=False,
        coverage_warning=COVERAGE_WARNING,
        not_covered=cal.not_covered,
        sources=cal.sources,
        attribution=cal.attribution,
        disclaimer=cal.disclaimer,
        reviewed_at=cal.reviewed_at,
    )
