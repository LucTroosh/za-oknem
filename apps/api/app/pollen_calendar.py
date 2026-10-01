"""Pollen calendar: static REFERENCE data (typical season per taxon for Poland), ADR-023.

Rule #7: a SeasonalCalendar is neither a Measurement nor a Forecast - it says what is
typically in season on a given date, nothing about today's actual concentration. It lives
in a validated JSON file in the repo (no DB, no network - rule #14), and the API labels it
`kind: "seasonal_calendar"`.

A season boundary is a (month, decade) pair: decade 1 = days 1-10, 2 = 11-20, 3 = 21-end.
Seasons never wrap the year (validated), which keeps comparisons plain tuple comparisons.
"""

import calendar
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

DATA_FILE = Path(__file__).parent / "data" / "pollen_calendar.json"
UPCOMING_DAYS = 30  # "upcoming" = season start within this many days

Point = tuple[int, int]  # (month 1-12, decade 1-3)


def _check_point(p: Point) -> Point:
    if not (1 <= p[0] <= 12 and 1 <= p[1] <= 3):
        raise ValueError(f"bad (month, decade): {p}")
    return p


class Range(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: Point
    end: Point

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        _check_point(self.start)
        _check_point(self.end)
        if self.start > self.end:
            raise ValueError("range start after end (year-wrapping seasons are not supported)")
        return self

    def contains(self, p: Point) -> bool:
        return self.start <= p <= self.end


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citation: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    license: str = Field(min_length=1)
    checked_at: date


class Taxon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z_]+$")
    name_pl: str = Field(min_length=1)
    category: Literal["tree", "grass", "weed", "fungal_spore"]
    season: Range
    peak: Range
    source_ids: list[str] = Field(min_length=1)  # every taxon must cite a source
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def _peak_inside_season(self) -> Self:
        if not (self.season.contains(self.peak.start) and self.season.contains(self.peak.end)):
            raise ValueError(f"{self.key}: peak outside season")
        return self


class NotCovered(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    name_pl: str
    reason: str


class PollenCalendar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    kind: Literal["seasonal_calendar"]
    valid_for_region: Literal["PL"]
    reviewed_at: date
    attribution: str
    disclaimer: str
    sources: dict[str, Source]
    taxa: list[Taxon] = Field(min_length=1)
    not_covered: list[NotCovered]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        keys = [t.key for t in self.taxa] + [n.key for n in self.not_covered]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate taxon key")
        for t in self.taxa:
            missing = [s for s in t.source_ids if s not in self.sources]
            if missing:
                raise ValueError(f"{t.key}: unknown source_ids {missing}")
        return self


@lru_cache(maxsize=1)
def load_calendar() -> PollenCalendar:
    return PollenCalendar.model_validate(json.loads(DATA_FILE.read_text(encoding="utf-8")))


def point_of(d: date) -> Point:
    """(month, decade) of a date; day 31 and Feb 29 fall into decade 3."""
    return (d.month, min((d.day - 1) // 10 + 1, 3))


def point_start(year: int, p: Point) -> date:
    return date(year, p[0], 10 * (p[1] - 1) + 1)


def point_end(year: int, p: Point) -> date:
    last = calendar.monthrange(year, p[0])[1]
    return date(year, p[0], min(10 * p[1], last) if p[1] < 3 else last)


class ActiveTaxon(BaseModel):
    key: str
    name_pl: str
    category: str
    phase: Literal["start", "peak", "end"]
    peak: bool
    season_start: date
    season_end: date
    peak_start: date
    peak_end: date
    note: str
    source_ids: list[str]


class UpcomingTaxon(BaseModel):
    key: str
    name_pl: str
    category: str
    starts_on: date
    days_until: int
    season_end: date
    note: str
    source_ids: list[str]


def select(cal: PollenCalendar, d: date) -> tuple[list[ActiveTaxon], list[UpcomingTaxon]]:
    """Taxa in season on `d` (with phase) and taxa whose season starts within UPCOMING_DAYS."""
    p = point_of(d)
    y = d.year
    active: list[ActiveTaxon] = []
    upcoming: list[UpcomingTaxon] = []
    for t in cal.taxa:
        if t.season.contains(p):
            phase: Literal["start", "peak", "end"] = (
                "peak" if t.peak.contains(p) else "start" if p < t.peak.start else "end"
            )
            active.append(
                ActiveTaxon(
                    key=t.key,
                    name_pl=t.name_pl,
                    category=t.category,
                    phase=phase,
                    peak=phase == "peak",
                    season_start=point_start(y, t.season.start),
                    season_end=point_end(y, t.season.end),
                    peak_start=point_start(y, t.peak.start),
                    peak_end=point_end(y, t.peak.end),
                    note=t.note,
                    source_ids=t.source_ids,
                )
            )
            continue
        # Next start: this year, else next year (late December -> January/February starts).
        for yy in (y, y + 1):
            start = point_start(yy, t.season.start)
            if start > d:
                break
        if start - d <= timedelta(days=UPCOMING_DAYS):
            upcoming.append(
                UpcomingTaxon(
                    key=t.key,
                    name_pl=t.name_pl,
                    category=t.category,
                    starts_on=start,
                    days_until=(start - d).days,
                    season_end=point_end(start.year, t.season.end),
                    note=t.note,
                    source_ids=t.source_ids,
                )
            )
    upcoming.sort(key=lambda u: u.days_until)
    return active, upcoming
