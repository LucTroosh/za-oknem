#!/usr/bin/env python3
"""Smoke test: did the backend actually pull data for a city? Read-only, stdlib only.

    python3 infrastructure/scripts/smoke_data.py [slug] [base_url]
    python3 infrastructure/scripts/smoke_data.py wroclaw http://localhost:8000

Checks (per source, never one failure hiding the rest - rule #1): source health, then what the
mobile app would actually get for the city (air station + params, weather, hourly forecast,
pollen, alerts), then the places registry (search + nearest, needed for "Użyj mojej lokalizacji").
OK = data there and not stale; WARN = there but old / partial; FAIL = missing.
Exit code 1 when anything FAILs. It only reads our own API; no secrets, nothing is written.
"""

from __future__ import annotations  # macOS ships Python 3.9: no `X | None` at runtime

import json
import sys
import urllib.error
import urllib.request

SLUG = sys.argv[1] if len(sys.argv) > 1 else "wroclaw"
BASE = (sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000").rstrip("/")
results: list[tuple[str, str, str]] = []


def say(level: str, name: str, detail: str = "") -> None:
    results.append((level, name, detail))
    print(f"{level:5} {name}" + (f" - {detail}" if detail else ""))


def get(path: str, body: dict | None = None):
    req = urllib.request.Request(BASE + path)
    if body is not None:
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def safe(name: str, fn):
    try:
        return fn()
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        say("FAIL", name, f"{type(exc).__name__}: {exc}")
        return None


def level_for(freshness: str | None) -> str:
    return {"FRESH": "OK", "RECENT": "OK", "STALE": "WARN"}.get(freshness or "", "FAIL")


print(f"Backend: {BASE}   City: {SLUG}\n")

health = safe("health/sources", lambda: get("/api/v1/health/sources"))
if health:
    for s in health["sources"]:
        if not s.get("monitored"):
            continue
        say(level_for(s["freshness"]), f"source {s['source_id']}", f"{s['freshness']}; last success {s['last_success_at']}")

areas = safe("areas", lambda: get("/api/v1/areas"))
area = next((a for a in (areas or {}).get("areas", []) if a["slug"] == SLUG), None)
if areas is not None and area is None:
    say("FAIL", f"area '{SLUG}'", "not in /areas (did migrations run?)")
if area:
    dash = safe("dashboard", lambda: get(f"/api/v1/dashboard/latest?geo_area_id={area['geo_area_id']}"))
    d = (dash or {}).get("areas", [None])[0] if dash else None
    if d:
        air = d.get("air")
        if not air:
            say("FAIL", "air", f"no station with data (coverage: {d['coverage']['air']}) - run: docker compose exec api python -c \"from app.scheduler import run_gios; print(run_gios())\" (or wait for the scheduler)")
        else:
            params = air["params"]
            worst = min((p["freshness"] for p in params.values()), key=["FRESH", "RECENT", "STALE"].index) if params else None
            say(level_for(worst), "air", f"{air['station_name']} {air['distance_km']} km, coverage {air['coverage']}, params: {', '.join(sorted(params))}")
            if "PM2.5" not in params:
                say("WARN", "air PM2.5", "this station does not report PM2.5")
        w = d.get("weather")
        say("OK" if w and "temperature_2m" in w["params"] else "FAIL", "weather", f"{w['params']['temperature_2m']['value']} °C ({w['freshness']})" if w and "temperature_2m" in w["params"] else "no current weather")
        hours = ((d.get("forecast") or {}).get("hours")) or []
        say("OK" if len(hours) >= 6 else "WARN", "hourly forecast", f"{len(hours)} hours")
        p = d.get("pollen")
        say(level_for((p or {}).get("freshness")) if p and p.get("current") else "FAIL", "pollen", "CAMS values present" if p and p.get("current") else "no pollen - run: python -m app.connectors.open_meteo_pollen.ingest")
        local = d.get("local_alerts", [])
        say("OK", "local alerts", f"{len(local)} for this area (0 is fine when nothing is issued)")
        unresolved = [a for a in local if a.get("geo_match") == "unresolved"]
        if unresolved:
            say("WARN", "alert matching", f"{len(unresolved)} unresolved (area without TERYT/voivodeship?)")
    alerts = (dash or {}).get("alerts") if dash else None
    if alerts:
        say("OK" if alerts["source_status"] else "WARN", "alerts source", json.dumps(alerts["source_status"])[:120])

places = safe("places search", lambda: get("/api/v1/places?q=olesnica"))
if places is not None:
    say("OK" if places["places"] else "FAIL", "places registry", f"{len(places['places'])} hit(s) for 'olesnica'" if places["places"] else "empty - GeoNames not imported (needed for search and GPS)")
if area:
    near = safe("places/nearest", lambda: get("/api/v1/places/nearest", {"latitude": area["latitude"], "longitude": area["longitude"]}))
    if near is not None:
        say("OK" if near["status"] == "found" else "FAIL", "places/nearest (GPS)", near["place"]["label"] if near.get("place") else "out_of_range")

fails = sum(1 for r in results if r[0] == "FAIL")
warns = sum(1 for r in results if r[0] == "WARN")
print(f"\n{len(results)} checks: {fails} FAIL, {warns} WARN")
sys.exit(1 if fails else 0)
