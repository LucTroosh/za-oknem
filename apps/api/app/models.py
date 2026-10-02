from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.geometry import MultiPolygon4326


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
    # ADR-014: which raw payload produced this row. NULL = row predates TASK-3.1, or
    # the provenance write failed (best-effort, rule #1) - never a broken link.
    source_fetch_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_fetches.id"), nullable=True, index=True
    )


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
    # ADR-014: which raw payload produced this row. NULL = row predates TASK-3.1, or
    # the provenance write failed (best-effort, rule #1) - never a broken link.
    source_fetch_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_fetches.id"), nullable=True, index=True
    )


class GeoArea(Base):
    """Location reference: the 7 seeded cities (ADR-005) plus imported gminy (ADR-019).

    Two separate concerns live on one row (BACKLOG TASK-6.2 (4)):
    - geo-matching: every gmina with `teryt_code` + `boundary` (point-in-polygon, rule #9);
    - weather polling: only rows with `weather_polling_active` (Open-Meteo 10k/day budget).
    """

    __tablename__ = "geo_areas"
    __table_args__ = (
        # Matches migration 0003 (unique constraint + plain index); the old model said
        # `unique=True, index=True` (one unique index) and `alembic check` flagged the drift -
        # unnoticed while CI's `| tee` swallowed the exit code.
        UniqueConstraint("slug", name="uq_geo_area_slug"),
        UniqueConstraint("teryt_code", name="uq_geo_area_teryt_code"),
        UniqueConstraint("place_id", name="uq_geo_area_place_id"),
        Index("ix_geo_areas_boundary", "boundary", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # 7-digit TERYT id of the gmina (TERC, incl. rodzaj digit). NULL = seed row not yet
    # linked to an imported boundary.
    teryt_code: Mapped[str | None] = mapped_column(String(7))
    # Gmina boundary, EPSG:4326 MultiPolygon (PostGIS). deferred: ~2.5k large polygons
    # must never ride along with `select(GeoArea)` (dashboard, weather, scheduler).
    boundary: Mapped[str | None] = mapped_column(MultiPolygon4326(), deferred=True)
    # Default True keeps today's behaviour for the seeded cities; the importer creates
    # new gminas with False (ADR-019).
    weather_polling_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    # ADR-029: the place (locality) this area was activated from; NULL for seeded cities and
    # imported gminas. `last_requested_at` = last activation request - the only signal for
    # idle expiry (a plain dashboard read is public/enumerable and never counts, ADR-026).
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True)
    last_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Place(Base):
    """A named locality (ADR-029): the list a user picks from. Imported from a local file
    (rule #2: PostgreSQL is the source of truth, never queried from an external geocoder on
    request, rule #14). Reference data, not a Measurement/Forecast/Event (rule #7).

    `normalized_name` = lowercase, diacritics folded (`app.places.normalize_name`): prefix
    search is a plain btree `LIKE 'q%'` (varchar_pattern_ops), no extension needed.
    `kind` = the GeoNames feature code (PPL, PPLA, PPLC, ...). Admin codes are the source's
    raw codes (GeoNames, not TERYT)."""

    __tablename__ = "places"
    __table_args__ = (
        UniqueConstraint("source", "source_record_id", name="uq_place_source_record"),
        Index(
            "ix_places_normalized_name",
            "normalized_name",
            postgresql_ops={"normalized_name": "varchar_pattern_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))
    admin1_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    admin2_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # GeoNames' names for those codes (admin1CodesASCII / admin2Codes): voivodeship in
    # English, powiat as "Powiat xyz"; `app.places.place_label` renders them for the UI.
    admin1_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    admin2_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50))
    source_record_id: Mapped[str] = mapped_column(String(50))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GiosStation(Base):
    """Cached GIOŚ station catalog (`/station/findAll`, ADR-025): the station as an
    entity, so area -> station assignment and polling never need a catalog walk on the
    hot path. `raw` is the station dict exactly as GIOŚ returned it (what
    `ingest_station` consumes); `fetched_at` + `source_fetch_id` are its provenance."""

    __tablename__ = "gios_stations"
    __table_args__ = (UniqueConstraint("station_id", name="uq_gios_station_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[str] = mapped_column(String(50))
    station_name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_fetch_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_fetches.id"), nullable=True, index=True
    )


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
    # ADR-014: which raw payload produced this row. NULL = row predates TASK-3.1, or
    # the provenance write failed (best-effort, rule #1) - never a broken link.
    source_fetch_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_fetches.id"), nullable=True, index=True
    )


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
        CheckConstraint("granularity IN ('daily', 'hourly')", name="ck_forecast_granularity"),
        # ADR-030: the daily retention purge (granularity + valid_until range).
        Index("ix_forecasts_granularity_valid_until", "granularity", "valid_until"),
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
    # ADR-014: which raw payload produced this row. NULL = row predates TASK-3.1, or
    # the provenance write failed (best-effort, rule #1) - never a broken link.
    source_fetch_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_fetches.id"), nullable=True, index=True
    )
    # ADR-030: "daily" (one row per day, append-only history, ADR-010) or "hourly" (the next
    # 48 h; only the newest model run is kept). A column, not a param_code convention: both
    # granularities carry `weather_code`, and a daily and an hourly row for 00:00 would
    # otherwise collide on (param, valid_from).
    granularity: Mapped[str] = mapped_column(String(10), default="daily", server_default="daily")


class PollenSnapshot(Base):
    """One hourly MODELLED pollen concentration for a geo_area (ADR-001 option C,
    ADR-020). NOT a Measurement (rule #7): values come from the CAMS European
    air-quality forecast model, never from a pollen trap, and the source itself calls
    them unvalidated/experimental. Hence `model` and `forecast_reference_time`.

    One row per (geo_area, valid_at, forecast run), with the five MVP species (Master
    Plan §6) as explicit columns, grains/m3. NULL = the model gave no value for that
    species/hour (typically outside its pollen season) - never 0, which is a real
    modelled concentration. The source's own unit string is kept in `unit`.
    """

    __tablename__ = "pollen_snapshots"
    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_pollen_snapshot_source_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    source_record_id: Mapped[str] = mapped_column(String(150))
    geo_area_id: Mapped[int] = mapped_column(ForeignKey("geo_areas.id"), index=True)
    alder: Mapped[float | None] = mapped_column(Float, nullable=True)  # olcha
    birch: Mapped[float | None] = mapped_column(Float, nullable=True)  # brzoza
    grass: Mapped[float | None] = mapped_column(Float, nullable=True)  # trawy
    mugwort: Mapped[float | None] = mapped_column(Float, nullable=True)  # bylica
    ragweed: Mapped[float | None] = mapped_column(Float, nullable=True)  # ambrozja
    unit: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(30))
    forecast_reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # ADR-014: which raw payload produced this row. NULL = the provenance write failed
    # (best-effort, rule #1) - never a broken link.
    source_fetch_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_fetches.id"), nullable=True, index=True
    )


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


class SourceFetch(Base):
    """One raw fetch from an external source (ADR-014, Master Plan §33-34): what
    exactly the source returned when we stored a value. Not a Measurement/Forecast/
    Event/Alert (rule #7) - it is the provenance record those rows point at via
    `source_fetch_id`.

    `payload` is the decoded JSON response (PostgreSQL JSONB; plain JSON on SQLite in
    tests). Retention (ADR-014) sets it to SQL NULL after the source's window; the
    row itself (endpoint, parser_version, validation_status, fetched_at) is kept.
    SQL NULL therefore means "purged"; a source that answered with a JSON `null`
    body is stored as the JSON literal `null` (JSON's default for Python None), so
    the two stay distinguishable (`payload IS NULL` vs `payload = 'null'`).
    """

    __tablename__ = "source_fetches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), index=True)
    endpoint: Mapped[str] = mapped_column(String(500))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    parser_version: Mapped[str] = mapped_column(String(30))
    # pending | valid | partial | invalid (app.provenance)
    validation_status: Mapped[str] = mapped_column(String(20))
    payload: Mapped[Any | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )


class Device(Base):
    """One app installation registered for push (ADR-017, Master Plan §66). No user
    account (rule #11): the row is keyed by a client-generated pseudonymous
    `installation_id`, and every later change is authorized by a server-generated
    `device_secret` of which only the SHA-256 hash is stored.

    Location is `observed_area_code` (TERYT, ADR-002) only - never GPS coordinates.
    `push_token` is NULL when the user declined notifications or after unregistering.
    Not a Notification or a preference (rule #7): sending is TASK-10.2, per-device
    preferences are TASK-10.3a.
    """

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # sha256 hex of the device secret (high-entropy random token, so no slow KDF needed)
    secret_hash: Mapped[str] = mapped_column(String(64))
    platform: Mapped[str] = mapped_column(String(10))
    push_token: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    observed_area_code: Mapped[str | None] = mapped_column(String(7), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
