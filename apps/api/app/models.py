from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
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
        UniqueConstraint(
            "source_id", "source_record_id", name="uq_weather_snapshot_source_record"
        ),
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
