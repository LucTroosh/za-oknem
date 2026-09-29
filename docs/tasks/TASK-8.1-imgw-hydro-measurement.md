# TASK 8.1 — IMGW hydro (stan wody) vertical slice

## Goal

Druga Measurement vertical slice (obok GIOŚ): poziom wody na stacjach IMGW,
`GET /api/v1/hydro/latest`. Ostrzeżenia hydrologiczne/meteo świadomie odłożone
(ADR-008) — inny model danych (Alert, rule #7), nie ta sama decyzja.

## Scope

- ADR-008: licencja (analogiczna do ADR-003), zakres (tylko Measurement, nie
  Alert), założenie o częstotliwości (1h, niezweryfikowane).
- Connector `imgw_hydro`: `client.py` (jedno wywołanie, bez paginacji/throttlingu),
  `parser.py` (mapowanie na `Measurement`, brak odrzucania ujemnych wartości —
  fizycznie poprawne dla stanu wody), `ingest.py`.
- `GET /api/v1/hydro/latest` — ten sam kształt co `/air/latest`.
- Reużycie istniejącej tabeli `measurements` — zero nowej migracji.
- Wpięcie do `app/scheduler.py` (co 1h, bez gatingu — deterministyczne, cała lista
  stacji w jednym wywołaniu).

## Acceptance Criteria

- [x] `normalize()` poprawnie mapuje pola, zwraca `None` dla stacji bez aktualnego
      odczytu (test: `test_normalize_returns_none_when_no_current_reading`).
- [x] `normalize()` NIE odrzuca ujemnego stanu wody (test:
      `test_normalize_accepts_negative_water_level`) — w przeciwieństwie do PM2.5.
- [x] `client.fetch_stations()` odrzuca kształt inny niż lista (test:
      `test_fetch_stations_rejects_non_list_shape`) — ochrona przed
      `warningsmeteo`-podobnym `{"message": ...}` na tym endpoincie.
- [x] Jedna zepsuta stacja nie przerywa całego ingestu (test:
      `test_one_bad_station_does_not_abort_the_rest`) — rule #1.
- [x] `/hydro/latest` czyta wyłącznie z naszej bazy (rule #14).
- [x] `run_imgw_hydro()` w schedulerze nie wymaga żadnej konfiguracji (w
      przeciwieństwie do `GIOS_STATION_IDS`) — deterministyczne z definicji.

## Tests

`apps/api/tests/connectors/test_imgw_hydro_{client,parser,ingest}.py`,
`apps/api/tests/test_hydro.py`, `apps/api/tests/test_scheduler.py`
(`TestRunImgwHydro`).

## Non-goals

- `warningshydro`/`warningsmeteo` (Alert) — osobny ADR i model, patrz
  Source Registry `imgw_alerts` (status DISCOVERY).
- Geo-matching stacji hydro do `geo_areas`/dashboardu.
- `stan_alarmowy`/`stan_ostrzegawczy` jako Alert Engine input.

## Dependencies

Brak nowej migracji — reużywa modelu `Measurement` z Phase 4 (GIOŚ).

## Data Contract

`GET /api/v1/hydro/latest` → `{"stations": [{station_id, station_name, latitude,
longitude, water_level_cm, unit, observed_at, freshness, source}]}`.

## Security

Brak nowych sekretów. Brak klucza API (publiczny endpoint).

## Architecture Impact

ADR-008 (licencja analogiczna do ADR-003, zakres ograniczony do Measurement).
