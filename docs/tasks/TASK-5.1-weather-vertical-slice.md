# TASK 5.1 — Weather (Open-Meteo) vertical slice

> Retroaktywny dokument — implementacja (PR #13-#22) powstała jako płaska nocna
> checklista, nie task-po-tasku. Ten plik domyka proces zgodnie z CLAUDE.md (rule
> #13), nie zmienia niczego w kodzie.

## Goal

Rozszerzyć vertical slice o pogodę (Open-Meteo), zgodnie z ADR-001 opcją C: snapshot
w bazie per lokalizacja, mobile czyta wyłącznie z naszej bazy.

## Scope

- ADR-005 (`geo_areas` jako płaski seed, nie pełny TERYT — Phase 6 osobno).
- Modele `GeoArea` + `WeatherSnapshot` + migracje Alembic (schema + seed 7 lokalizacji).
- Connector `open_meteo` (`client.py`/`parser.py`/`ingest.py`), kontrakt fetch/parse/
  validate/normalize jak GIOŚ.
- `GET /api/v1/weather/latest`.
- Mobile: sekcja "Pogoda" (później zastąpiona przez TASK-5.2's dashboard).

## Acceptance Criteria

- [x] `geo_areas` i `weather_snapshots` istnieją, migracje przechodzą (`alembic
      upgrade head`, zweryfikowane w CI z realnym Postgresem od PR #20).
- [x] `python -m app.connectors.open_meteo.ingest` zapisuje snapshoty, izoluje
      błędy per geo_area (rule #1).
- [x] `GET /api/v1/weather/latest` czyta wyłącznie z bazy (rule #14).
- [x] Testy: client (mocked httpx), parser (walidacja kształtu), ingest (SQLite +
      mocki), endpoint (fake session).
- [x] `docs/data/source-registry.md`: `open_meteo` → IMPLEMENTED.

## Tests

`apps/api/tests/connectors/test_open_meteo_{client,parser,ingest}.py`,
`apps/api/tests/test_weather.py`.

## Non-goals

- Pełny TERYT/Geo Engine (Phase 6) — jawnie odłożone, ADR-005.
- Scheduler (fetch co 3h jest udokumentowany w source-registry, ale nie
  zaimplementowany — nadal ręczny CLI).
- Pyłki/CAMS (Phase 8).

## Dependencies

Phase 4 (GIOŚ vertical slice) — używa tego samego kontraktu connectora i tego
samego wzorca testów.

## Data Contract

`GET /api/v1/weather/latest` → `{"areas": [{geo_area_id, slug, name, latitude,
longitude, observed_at, freshness, params: {param_code: {value, unit}}, source}]}`.

## Security

Brak nowych sekretów — Open-Meteo nie wymaga klucza API.

## Architecture Impact

Zgodne z ADR-001 (opcja C) i ADR-005 (nowa, ograniczona w zakresie decyzja
o `geo_areas`). Bez odejścia od Master Planu.
