"""Real active schema captured 2026-10-03; timezone remains a separate publication gate."""

from datetime import datetime, timedelta
from typing import Any

from app.connectors.imgw_weather.parser import number, source_time

# The only dict shape actually confirmed live (2026-09-29) as "zero active
# warnings". Any other dict - a rate-limit notice, a service diagnostic, a
# typo'd variant - must fail loudly instead of silently being read as "no
# warnings" (rule #10; Codex review, PR #38): a misread error response would
# otherwise look like a valid empty snapshot to callers.
NO_WARNINGS_MESSAGE = "Brak ostrzeżeń meteorologicznych"


class ImgwWarningsMeteoParseError(Exception):
    """Raised when the payload doesn't match the expected top-level shape."""


def parse_warnings(payload: Any) -> list[dict[str, Any]]:
    """Accepts either a list of warnings, or the confirmed-live "no active
    warnings" message-dict shape. Anything else is an unrecognized shape -
    fail loud (rule #10), don't guess."""
    if isinstance(payload, dict):
        # Whole-dict equality, not just the "message" key: an extra field (an
        # "error" flag alongside the right text, say) means this isn't the
        # verified shape either, and must fail loud rather than be read as a
        # valid empty snapshot (rule #10; Codex review, PR #38).
        if payload == {"message": NO_WARNINGS_MESSAGE}:
            return []
        raise ImgwWarningsMeteoParseError(f"unrecognized dict shape: {payload!r}")
    if isinstance(payload, list):
        return payload
    raise ImgwWarningsMeteoParseError(f"expected list or message-dict, got {type(payload)!r}")


def normalize(warning: dict, *, fetched_at: datetime, timezone: str | None) -> dict:
    try:
        if not isinstance(warning, dict):
            raise ValueError("invalid warning shape")
        required = (
            "id",
            "nazwa_zdarzenia",
            "stopien",
            "prawdopodobienstwo",
            "obowiazuje_od",
            "obowiazuje_do",
            "opublikowano",
            "tresc",
            "komentarz",
            "biuro",
            "teryt",
        )
        if any(key not in warning for key in required):
            raise ValueError("missing warning field")
        for field in ("id", "nazwa_zdarzenia", "tresc", "biuro"):
            if not isinstance(warning[field], str) or not warning[field].strip():
                raise ValueError("invalid warning text")
        if len(warning["id"]) > 50 or warning["stopien"] not in ("1", "2", "3"):
            raise ValueError("invalid id or official degree")
        probability = number(warning["prawdopodobienstwo"])
        if probability is None or not 0 <= probability <= 100:
            raise ValueError("invalid probability")
        codes = warning["teryt"]
        if (
            not isinstance(codes, list)
            or not codes
            or any(not isinstance(c, str) or len(c) != 4 or not c.isdigit() for c in codes)
        ):
            raise ValueError("invalid county codes")
        start = source_time(warning["obowiazuje_od"], timezone)
        end = source_time(warning["obowiazuje_do"], timezone)
        issued = source_time(warning["opublikowano"], timezone)
        if start >= end or issued > fetched_at + timedelta(minutes=5):
            raise ValueError("invalid warning interval or future issue time")
        if warning["komentarz"] is not None and not isinstance(warning["komentarz"], str):
            raise ValueError("invalid comment")
        return {
            "source_id": "imgw_warningsmeteo",
            "source_record_id": warning["id"],
            "external_id": warning["id"],
            "event_type": warning["nazwa_zdarzenia"],
            "severity_raw": warning["stopien"],
            "probability_pct": probability,
            "issuing_office": warning["biuro"],
            "description": warning["tresc"],
            "comment": warning["komentarz"],
            "areas": [{"teryt": code} for code in dict.fromkeys(codes)],
            "valid_from": start,
            "valid_until": end,
            "published_at": issued,
            "fetched_at": fetched_at,
        }
    except (ValueError, KeyError, TypeError) as exc:
        raise ImgwWarningsMeteoParseError(str(exc)) from exc
