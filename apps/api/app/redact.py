"""Keeps the Open-Meteo API key out of exception text and logs (rule #3, ADR-022).

httpx puts the full URL, query included, into HTTPStatusError messages and into its own
INFO request log - with a commercial plan that URL carries `apikey=`. `redact()` masks
both the `apikey=` parameter (any value) and the configured key itself; the filter below
applies it to the `httpx` logger."""

import logging
import re

from app.config import settings

_APIKEY = re.compile(r"(apikey=)[^&\s'\")]*", re.IGNORECASE)


def redact(text: str) -> str:
    text = _APIKEY.sub(r"\1[redacted]", text)
    key = settings.open_meteo_api_key
    return text.replace(key, "[redacted]") if key else text


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = redact(record.getMessage()), None
        return True


# Idempotent: one filter instance per process, whatever number of imports.
_httpx_logger = logging.getLogger("httpx")
if not any(isinstance(f, _RedactFilter) for f in _httpx_logger.filters):
    _httpx_logger.addFilter(_RedactFilter())
