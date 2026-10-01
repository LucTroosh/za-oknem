import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Response
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Device
from app.rate_limit import limit_device_writes

router = APIRouter()

# Random, client-generated, >=128 bits (UUIDv4 or 22+ base64url chars). Pseudonymous,
# NOT a secret: authorization is `X-Device-Secret` (ADR-017).
INSTALLATION_ID_PATTERN = r"^[A-Za-z0-9_-]{32,64}$"
# `ExponentPushToken[...]` (current) / `ExpoPushToken[...]` (legacy) - format only;
# whether Expo accepts the token is learned at send time (TASK-10.2).
EXPO_TOKEN_PATTERN = r"^Expo(nent)?PushToken\[[A-Za-z0-9_-]{1,200}\]$"
# TERYT powiat (4) / gmina (6-7 digits). Format only - no TERYT catalogue to check
# against yet (ADR-002/TASK-6.2).
TERYT_PATTERN = r"^\d{4,7}$"

InstallationId = Annotated[str, StringConstraints(pattern=INSTALLATION_ID_PATTERN)]


class DeviceIn(BaseModel):
    # forbid: coordinates (or anything unknown) are rejected, never silently stored (ADR-002).
    model_config = ConfigDict(extra="forbid")

    installation_id: InstallationId
    platform: Literal["android", "ios"]
    push_token: (
        Annotated[str, StringConstraints(max_length=255, pattern=EXPO_TOKEN_PATTERN)] | None
    ) = None
    observed_area_code: Annotated[str, StringConstraints(pattern=TERYT_PATTERN)] | None = None
    app_version: (
        Annotated[str, StringConstraints(max_length=32, pattern=r"^[0-9A-Za-z.+_-]+$")] | None
    ) = None


class DeviceOut(BaseModel):
    installation_id: str
    platform: Literal["android", "ios"]
    # The token itself is never echoed back.
    push_registered: bool
    observed_area_code: str | None
    app_version: str | None
    active: bool
    last_seen_at: datetime
    # Returned ONCE, on creation (201); null on every later call.
    device_secret: str | None


RETRYABLE_SQLSTATES = {"40P01", "40001"}  # deadlock_detected, serialization_failure


def _sqlstate(exc: OperationalError) -> str | None:
    # psycopg 3: `.sqlstate`; psycopg2: `.pgcode`
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _authorized(device: Device, secret: str | None) -> bool:
    return hmac.compare_digest(device.secret_hash, _hash_secret(secret or ""))


SecretHeader = Annotated[str | None, Header(alias="X-Device-Secret", max_length=128)]


@router.post(
    "/devices",
    response_model=DeviceOut,
    dependencies=[Depends(limit_device_writes)],
    responses={201: {"model": DeviceOut}},
)
def register_device(
    body: DeviceIn,
    response: Response,
    x_device_secret: SecretHeader = None,
    db: Session = Depends(get_db),
) -> DeviceOut:
    """Idempotent upsert by `installation_id` (ADR-017). New -> 201 + `device_secret`
    (shown once). Existing -> 200, requires the `X-Device-Secret` header (403 otherwise);
    only fields present in the body are changed (`push_token: null` clears it)."""
    response.headers["Cache-Control"] = "no-store"
    now = datetime.now(UTC)
    device = db.execute(
        select(Device).where(Device.installation_id == body.installation_id)
    ).scalar_one_or_none()
    new_secret: str | None = None
    if device is None:
        new_secret = secrets.token_urlsafe(32)
        device = Device(
            installation_id=body.installation_id,
            secret_hash=_hash_secret(new_secret),
            platform=body.platform,
            active=True,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        db.add(device)
        response.status_code = 201
    elif not _authorized(device, x_device_secret):
        raise HTTPException(status_code=403, detail="Invalid device credentials")

    try:
        if body.push_token is not None:
            # One token = one installation: a reinstall gets a new installation_id with the
            # same Expo token, which must not be pushed twice.
            db.execute(
                update(Device)
                .where(
                    Device.push_token == body.push_token,
                    Device.installation_id != device.installation_id,
                )
                .values(push_token=None)
            )
        for field in body.model_fields_set - {"installation_id", "platform"}:
            setattr(device, field, getattr(body, field))
        device.platform = body.platform
        device.active = True
        device.updated_at = now
        device.last_seen_at = now
        db.commit()
    except (IntegrityError, OperationalError) as exc:
        # 409 only for a real concurrency conflict: unique violation at INSERT/UPDATE, or
        # a Postgres deadlock / serialization failure (two installations swapping tokens).
        # Other OperationalErrors (disconnect, failover, timeout) are not the client's to
        # fix: roll back and re-raise like any other DB error.
        db.rollback()
        if isinstance(exc, OperationalError) and _sqlstate(exc) not in RETRYABLE_SQLSTATES:
            raise
        # If this was a first registration whose twin request won, its secret is gone
        # from our side of the race: a retry would get 403, so say so.
        raise HTTPException(
            status_code=409,
            detail="Conflict: retry; if the retry is 403, register a new installation_id",
        ) from None
    return DeviceOut(
        installation_id=device.installation_id,
        platform=body.platform,
        push_registered=device.push_token is not None,
        observed_area_code=device.observed_area_code,
        app_version=device.app_version,
        active=device.active,
        last_seen_at=device.last_seen_at,
        device_secret=new_secret,
    )


@router.delete(
    "/devices/{installation_id}",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(limit_device_writes)],
)
def unregister_device(
    installation_id: Annotated[str, Path(pattern=INSTALLATION_ID_PATTERN)],
    x_device_secret: SecretHeader = None,
    db: Session = Depends(get_db),
) -> Response:
    """Deactivate: drops the push token and observed area, keeps the row (hashed secret,
    timestamps) so a repeated DELETE stays idempotent. Unknown id and wrong secret are
    indistinguishable (404). Row purging is the retention task (TASK-14.2)."""
    device = db.execute(
        select(Device).where(Device.installation_id == installation_id)
    ).scalar_one_or_none()
    if device is None or not _authorized(device, x_device_secret):
        raise HTTPException(status_code=404, detail="Device not found")
    device.active = False
    device.push_token = None
    device.observed_area_code = None
    device.updated_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=204)
