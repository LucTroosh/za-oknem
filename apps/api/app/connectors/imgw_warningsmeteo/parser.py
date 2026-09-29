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
        if payload.get("message") == NO_WARNINGS_MESSAGE:
            return []
        raise ImgwWarningsMeteoParseError(f"unrecognized dict shape: {payload!r}")
    if isinstance(payload, list):
        return payload
    raise ImgwWarningsMeteoParseError(f"expected list or message-dict, got {type(payload)!r}")
