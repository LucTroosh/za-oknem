"""Deterministic alert -> area matching (rule #9, ADR-013). Pure functions, no DB.

What a source warning actually carries decides the granularity. IMGW hydro warnings
(`obszary`, verified live, ADR-009) name a voivodeship (`wojewodztwo`) and catchment codes
(`kod_zlewni`) - never TERYT, powiat or gmina. So the only administrative link available is
voivodeship NAME -> its 2-digit TERC code (a fixed official list) -> prefix of
`geo_areas.teryt_code` (ADR-019). Catchments cannot be mapped to gminas without a
catchment<->gmina dataset we do not have, so a match is voivodeship-wide by definition
and says so (`geo_match`), it never pretends to be finer.

Fail-safe (rule #10, safety data): what cannot be resolved is never silently dropped.
"""

from typing import Any, Literal

GeoMatch = Literal["voivodeship", "unresolved"]

# TERC voivodeship codes (GUS), keyed by the lowercase name as IMGW writes it.
VOIVODESHIP_TERYT: dict[str, str] = {
    "dolnośląskie": "02",
    "kujawsko-pomorskie": "04",
    "lubelskie": "06",
    "lubuskie": "08",
    "łódzkie": "10",
    "małopolskie": "12",
    "mazowieckie": "14",
    "opolskie": "16",
    "podkarpackie": "18",
    "podlaskie": "20",
    "pomorskie": "22",
    "śląskie": "24",
    "świętokrzyskie": "26",
    "warmińsko-mazurskie": "28",
    "wielkopolskie": "30",
    "zachodniopomorskie": "32",
}

# TERYT prefix lengths: voivodeship, powiat, gmina (7 incl. the rodzaj digit).
_CODE_LENGTHS = (2, 4, 7)


def teryt_covers(unit_code: str, area_code: str) -> bool:
    """True when `area_code` lies inside the administrative unit `unit_code`: the unit code
    is a prefix of the area code (woj 2 / powiat 4 / gmina 7 digits). Anything else - bad
    length, non-digits - is no match, so "1" never swallows "14...", "1465" is not "146"."""
    return (
        len(unit_code) in _CODE_LENGTHS
        and unit_code.isdigit()
        and area_code.isdigit()
        and area_code.startswith(unit_code)
    )


def alert_voivodeship_codes(areas: Any) -> tuple[set[str], bool]:
    """(resolved voivodeship TERYT codes, whether anything stayed unresolved) for an
    alert's raw `areas` JSON. An empty/odd list, an entry without a known voivodeship name
    all count as unresolved."""
    if not isinstance(areas, list) or not areas:
        return set(), True
    codes: set[str] = set()
    unresolved = False
    for entry in areas:
        name = entry.get("wojewodztwo") if isinstance(entry, dict) else None
        code = VOIVODESHIP_TERYT.get(name.strip().casefold()) if isinstance(name, str) else None
        if code is None:
            unresolved = True
        else:
            codes.add(code)
    return codes, unresolved


def match_alert(areas: Any, area_teryt: str | None) -> GeoMatch | None:
    """How an alert relates to an area with this TERYT code, or None = does not apply.
    - "voivodeship": the area lies in a voivodeship the alert names;
    - "unresolved": we cannot tell (area without TERYT - seed not yet linked to an imported
      boundary, ADR-019 - or an alert area we cannot map): shown, flagged, never hidden."""
    codes, unresolved = alert_voivodeship_codes(areas)
    if area_teryt and any(teryt_covers(code, area_teryt) for code in codes):
        return "voivodeship"
    if area_teryt is None or unresolved:
        return "unresolved"
    return None


def filter_alerts_for_area(alerts: list[dict], area_teryt: str | None) -> list[dict]:
    """Alerts (as built by `current_alerts`) that apply to an area, each copied with its
    `geo_match`. Order is preserved."""
    out = []
    for alert in alerts:
        match = match_alert(alert["areas"], area_teryt)
        if match is not None:
            out.append({**alert, "geo_match": match})
    return out
