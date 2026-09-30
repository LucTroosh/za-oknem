# TASK 5.5 — Prognoza widoczna dla użytkownika (§5, §30 Master Planu)

## Goal

TASK-5.3 skończył się na `GET /api/v1/weather/forecast`, którego nic nie
konsumowało — `dashboard_latest()` i ekran Home czytały tylko current-weather.
Prognoza (MVP field §5) była więc w bazie i API, ale niewidoczna.

## Scope

- `api/v1/weather.py`: logika wyboru najświeższej prognozy per (gmina, dzień,
  parametr) wydzielona do `forecasts_by_area(db)` — jedno miejsce, używane przez
  `/weather/forecast` (bez zmiany odpowiedzi) i przez dashboard.
- `api/v1/dashboard.py`: nowy blok `forecast` per gmina — `source`,
  `attribution`, `fetched_at`, `freshness` (z realnego `fetched_at`, jak w
  `/weather/forecast`), `days` (`valid_from`, `valid_until`, `params`); `null`,
  gdy brak prognozy.
- Mobile (`index.tsx`, `forecast.ts`): linia „Prognoza: śr 19°/9° …” dla 3
  najbliższych dni + freshness + atrybucja z czasem pobrania.

## Non-goals

- Osobny ekran pogody / prognoza godzinowa — MVP to prognoza dzienna (ADR-010).
- Dni w strefie Europe/Warsaw — Open-Meteo jest odpytywane z `timezone=UTC`,
  więc dzień to doba UTC; blisko północy etykieta może się przesunąć o dzień
  (`ponytail:` w `forecast.ts`). Zmiana wymaga zmiany zapytania w connectorze.

## Acceptance Criteria

- [x] `dashboard_latest()` zwraca `forecast` z atrybucją i freshness
      (`test_dashboard_includes_forecast_with_source_transparency`).
- [x] `forecast: null`, gdy brak wierszy (`test_dashboard_forecast_null_when_no_forecast_rows`).
- [x] `/weather/forecast` bez zmian zachowania (istniejące testy `test_weather.py`).
- [x] Mobile nie wymyśla wartości: dzień bez max/min jest pomijany, brak linii
      gdy żaden dzień nie ma obu (`forecast.test.ts`).
- [x] `ruff check` czyste; CI: pytest, eslint, tsc, vitest.

## Dependencies

TASK-5.3 (PR #46). Dotyka `dashboard.py`/`index.tsx` jak PR #56 (inne miejsca
plików — ewentualny konflikt trywialny).

## Data Contract

Rozszerzenie odpowiedzi `/api/v1/dashboard/latest` o pole `forecast`
(addytywne, bez zmian istniejących pól). Bez zmian schematu bazy.

## Security

Brak nowej powierzchni — ten sam publiczny odczyt z naszej bazy (rule #14).

## Architecture Impact

Brak — realizacja już przyjętego ADR-010; bez nowego ADR.
