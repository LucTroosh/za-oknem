from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint
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
