"""Parse raw IMGW meteo-warning payloads.

Only the top-level shape (list of warnings vs. the confirmed-live empty
message-dict) is verified so far - normalize() (per-record field mapping into
an Alert) is intentionally NOT implemented yet. Unlike warningshydro, no
active meteo warning has been observed live during development, so the real
per-record field names aren't confirmed - only reverse-engineered guesses from
unofficial third-party scrapers exist, and rule #10/#15 rule out shipping a
field mapping for safety data that hasn't been checked against the real thing.
Revisit once a live warning can be captured (see Source Registry
`imgw_warningsmeteo`, status DISCOVERY).
"""

from typing import Any


class ImgwWarningsMeteoParseError(Exception):
    """Raised when the payload doesn't match the expected top-level shape."""


def parse_warnings(payload: Any) -> list[dict[str, Any]]:
    """Accepts either a list of warnings, or the confirmed-live "no active
    warnings" message-dict shape ({"message": "Brak ostrzeżeń
    meteorologicznych"}, verified live 2026-09-29). Anything else is an
    unrecognized shape - fail loud (rule #10), don't guess."""
    if isinstance(payload, dict):
        if "message" in payload:
            return []
        raise ImgwWarningsMeteoParseError(f"unrecognized dict shape: {payload!r}")
    if isinstance(payload, list):
        return payload
    raise ImgwWarningsMeteoParseError(f"expected list or message-dict, got {type(payload)!r}")
