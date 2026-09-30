from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Measurement(Base):
    """One normalized reading from a source connector.

    Master Plan §29/§30/§31: measurement != forecast != event — this table is
    measurements only. Freshness (FRESH/RECENT/STALE) is computed at read time
    from observed_at, not stored as a column (it would go stale itself).
    """

    __tablename__ = "measurements"
    __table_args__ = (
        # Same sensor + same timestamp = same reading. Re-running ingest must not
        # duplicate rows (§40 idempotency).
        UniqueConstraint("source_id", "source_record_id", name="uq_measurement_source_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    source_record_id: Mapped[str] = mapped_column(String(150))
    station_id: Mapped[str] = mapped_column(String(50), index=True)
    station_name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    param_code: Mapped[str] = mapped_column(String(20), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Alert(Base):
    """A source's own warning/alert (ADR-009). Not a Measurement (rule #7: never
    conflate the two) and not a Notification — an Alert can exist without one
    ever being pushed (Master Plan §32).

    `severity_raw` is kept exactly as the source reports it, unconverted to any
    scale of our own invention — rule #10: we are never the source of truth for
    safety data, only a pass-through of what the issuing authority said.
    """

    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_alert_source_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    source_record_id: Mapped[str] = mapped_column(String(150))
    external_id: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(200))
    severity_raw: Mapped[str] = mapped_column(String(20))
    probability_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    issuing_office: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Raw "obszary" list from the source (ADR-009: normalizing into a table is
    # premature until geo-matching to geo_areas is actually decided).
    areas: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GeoArea(Base):
    """Flat, manually-seeded location reference (ADR-005).

    Stand-in for the full TERYT/gmina model (Phase 6 Geo Engine) — deliberately
    minimal so Phase 5 (Weather) isn't blocked on it. Extending later is additive
    (add a TERYT column), not a rewrite.
    """

    __tablename__ = "geo_areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class WeatherSnapshot(Base):
    """One normalized weather reading for a geo_area (ADR-001 option C).

    Same shape as Measurement (one row per param_code) — snapshot only, mobile
    API never calls Open-Meteo on request (rule #14).
    """

    __tablename__ = "weather_snapshots"
    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_weather_snapshot_source_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    source_record_id: Mapped[str] = mapped_column(String(150))
    geo_area_id: Mapped[int] = mapped_column(ForeignKey("geo_areas.id"), index=True)
    param_code: Mapped[str] = mapped_column(String(30), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Forecast(Base):
    """A predicted future reading for a geo_area (§30 Master Plan, ADR-010).

    NOT a Measurement or a WeatherSnapshot (rule #7): valid_from/valid_until
    describe the period the forecast is FOR (a future day), never what was
    observed now. `forecast_reference_time` is when the model run behind this
    reading was generated — Open-Meteo's API doesn't expose that timestamp, so
    it's approximated as our own fetch time bucketed to the real update cadence
    (3h, ADR-004) rather than the raw fetch instant (see ADR-010 for why: this
    keeps re-running ingest within one cycle idempotent, and is an honestly
    documented approximation, not a fabricated one - rule #10 is about safety
    data, weather forecast is not that, but "don't invent precision we don't
    have" still applies).
    """

    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_forecast_source_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    source_record_id: Mapped[str] = mapped_column(String(150))
    geo_area_id: Mapped[int] = mapped_column(ForeignKey("geo_areas.id"), index=True)
    param_code: Mapped[str] = mapped_column(String(30), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(30))
    forecast_reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceFetchCounter(Base):
    """Daily outbound-call counter per source (ADR-001/ADR-003/ADR-004: "licznik
    dziennych wywołań per źródło w bazie, alert przy 70% dziennego limitu").

    Postgres, not Redis (rule #2: Redis is cache/short-lived state, this counter
    must survive a scheduler restart to mean anything). One row per
    (source_id, day) - `count` is NOT a raw outbound-request tally: `record_fetch_call()`
    takes a `units` argument, and each connector passes its own conservatively-rounded
    estimate of Open-Meteo's real billing units per call (see
    `ingest.ESTIMATED_BILLABLE_UNITS_PER_CALL`, derived from their published pricing
    rule), incremented once per real HTTP attempt (success or failure) by the
    connector itself.

    LucTroosh review: this docstring used to say "number of outbound HTTP requests" -
    stale the moment `units=` stopped defaulting to a 1:1 request:unit mapping, since
    one HTTP attempt is now persisted as `count += N` for N > 1. Still a conservative
    (rounded up) lower bound on real billing units, not an exact remaining-budget
    figure - upgrade if Open-Meteo ever publishes the precise per-variable formula.
    """

    __tablename__ = "source_fetch_counters"
    __table_args__ = (UniqueConstraint("source_id", "day", name="uq_source_fetch_counter_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class SourceStatus(Base):
    """Last scheduler run per source (ADR-012): lets an empty list be told apart
    from a source we haven't managed to fetch (rule #8 UNAVAILABLE). One row per
    source, upserted after each scheduler job run and each manual CLI ingest. Postgres, not Redis
    (rule #2) - "when did this last succeed" must survive a restart."""

    __tablename__ = "source_status"

    source_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Ops diagnostics only - never exposed through the API (ADR-012).
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
