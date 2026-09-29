# TASK 5.2 — GET /api/v1/dashboard/latest (nearest-station join)

## Goal

Dać mobile jeden endpoint do jednego widoku per lokalizacja (PM2.5 + pogoda razem),
bez czekania na pełny Phase 6 Geo Engine i bez zgadywania dopasowania (rule #9).

## Scope

- ADR-006: decyzja o zakresie (nearest-station join, nie pełny TERYT).
- `app/geo.py`: `haversine_km` (stdlib `math`, deterministyczne).
- `GET /api/v1/dashboard/latest`: per `geo_area` — pogoda (zawsze, jeśli jest snapshot)
  + PM2.5 z najbliższej stacji GIOŚ (tylko w promieniu `MAX_MATCH_DISTANCE_KM = 50`).
- Mobile: `index.tsx` przepięty na ten endpoint, `api.ts` jako wspólny fetch wrapper.

## Acceptance Criteria

- [x] `haversine_km` zwraca poprawne odległości (zweryfikowane: Kłodzko-Warszawa
      ~362.65 km, obliczone i sprawdzone, nie zgadywane).
- [x] `/dashboard/latest` nie dołącza stacji spoza progu (test:
      `test_dashboard_no_air_when_nearest_station_too_far`).
- [x] `/dashboard/latest` wybiera najbliższą z wielu stacji (test:
      `test_dashboard_picks_nearest_of_multiple_stations`).
- [x] Endpoint czyta wyłącznie z naszej bazy (rule #14) — trzy niezależne zapytania,
      join w Pythonie.
- [x] Mobile pokazuje PM2.5 + temperaturę w jednym wierszu per lokalizacja.
- [x] Istniejące `/air/latest` i `/weather/latest` bez zmian (rule #7).

## Tests

`apps/api/tests/test_geo.py`, `apps/api/tests/test_dashboard.py`,
`apps/mobile/app/api.test.ts`.

## Non-goals

- Dopasowanie dowolnych współrzędnych użytkownika do gminy (Phase 6).
- TERYT, point-in-polygon, granice administracyjne.
- Konfigurowalny próg odległości (stała, udokumentowana — nie ma dziś potrzeby na
  więcej).

## Dependencies

TASK-5.1 (weather vertical slice) — potrzebuje `GeoArea`/`WeatherSnapshot`.

## Data Contract

`GET /api/v1/dashboard/latest` → `{"areas": [{geo_area_id, slug, name, latitude,
longitude, air: {station_id, station_name, pm25, unit, observed_at, freshness,
distance_km} | null, weather: {observed_at, freshness, params} | null}]}`.

## Security

Brak zmian.

## Architecture Impact

ADR-006 (nowa, jawnie ograniczona w zakresie decyzja — nie Phase 6).
