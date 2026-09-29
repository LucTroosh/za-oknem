"""Parse / validate / normalize raw IMGW hydro-warning payloads into
Alert-ready dicts. Field names verified against a live response 2026-09-29
(ADR-009) - Polish keys, values are strings including numeric-looking ones.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# Not independently verified against a live cross-check with a known UTC offset
# event - assumed Polish local time on the strength of being the same institute
# and convention as GIOŚ/imgw_hydro (ADR-008/ADR-009). Revisit if ever shown wrong.
IMGW_TZ = ZoneInfo("Europe/Warsaw")


class ImgwWarningsHydroParseError(Exception):
    """Raised when the payload or a warning record doesn't match the expected shape."""


def parse_warnings(payload: Any) -> list[dict[str, Any]]:
    """Accepts either a list of warnings, or the known "no active warnings"
    message-dict shape (confirmed live for the sibling warningsmeteo endpoint,
    not independently confirmed for this one - ADR-009 handles both rather than
    guessing which applies here). The exact wording isn't confirmed for THIS
    endpoint, so this only enforces the one thing that is verified - a single
    "message" key with a string value - and rejects anything with extra fields
    (a diagnostic/rate-limit response, say) rather than silently reading it as
    a confirmed empty snapshot (rule #10; same gap Codex review caught on the
    sibling warningsmeteo connector, PR #38). Any other shape - fail loud,
    don't guess."""
    if isinstance(payload, dict):
        if set(payload.keys()) == {"message"} and isinstance(payload["message"], str):
            return []
        raise ImgwWarningsHydroParseError(f"unrecognized dict shape: {payload!r}")
    if isinstance(payload, list):
        return payload
    raise ImgwWarningsHydroParseError(f"expected list or message-dict, got {type(payload)!r}")


def _parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IMGW_TZ)


def _required_str(warning: dict[str, Any], key: str) -> str:
    """`str(None)` would silently store the literal text "None" as if it were
    real data (Codex review, PR #37) - a required field must be an actual value,
    not just present (rule #1/#10)."""
    value = warning[key]
    if value is None:
        raise ImgwWarningsHydroParseError(f"required field '{key}' is null")
    return str(value)


def normalize(warning: dict[str, Any], *, fetched_at: datetime) -> dict[str, Any]:
    """Raises ImgwWarningsHydroParseError on anything missing/malformed - a bad
    warning record must not silently produce a wrong alert (rule #1/#10)."""
    try:
        external_id = _required_str(warning, "numer")
        published_at = _parse_datetime(warning["opublikowano"])
        valid_from = _parse_datetime(warning["data_od"])
        valid_until = _parse_datetime(warning["data_do"])
        probability_raw = warning.get("prawdopodobieństwo")
        areas = warning["obszary"]
        if not isinstance(areas, list):
            raise ImgwWarningsHydroParseError(f"'obszary' is not a list: {areas!r}")

        record = {
            "source_id": "imgw_warningshydro",
            "source_record_id": f"{external_id}:{published_at.isoformat()}",
            "external_id": external_id,
            "event_type": _required_str(warning, "zdarzenie"),
            # Kept exactly as reported, never reinterpreted (rule #10, ADR-009) -
            # hydro drought uses a different scale ("-1") than typical meteo
            # warnings, and it isn't this codebase's place to normalize that.
            "severity_raw": _required_str(warning, "stopień"),
            "probability_pct": float(probability_raw) if probability_raw is not None else None,
            "issuing_office": _required_str(warning, "biuro"),
            "description": _required_str(warning, "przebieg"),
            "comment": str(warning["komentarz"]) if warning.get("komentarz") else None,
            "areas": areas,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "published_at": published_at,
            "fetched_at": fetched_at,
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ImgwWarningsHydroParseError(f"malformed warning payload: {exc}") from exc
    return record
