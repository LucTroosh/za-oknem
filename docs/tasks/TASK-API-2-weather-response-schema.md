# TASK API-2 — Typed response model dla `/api/v1/weather/*`

## Goal

Ten sam wzorzec co TASK-API-1 (`/air/latest`), zastosowany do
`GET /api/v1/weather/latest` i `GET /api/v1/weather/forecast` — oba dziś
`-> dict` bez `response_model`.

## Scope

- `api/v1/weather.py`: `WeatherParam`, `WeatherArea`,
  `WeatherLatestResponse`, `ForecastDay`, `ForecastArea`,
  `WeatherForecastResponse` (Pydantic), odzwierciedlające dokładnie
  dzisiejszy kształt dict. `response_model=` na obu dekoratorach.
- Żadnych zmian w `dashboard.py` (osobny task, plus dziś w nie-zmergowanym
  PR #49).

## Acceptance Criteria

- [x] `response_model` na obu endpointach.
- [x] Puste `areas: []` nadal poprawnie serializuje się (oba endpointy).
- [x] Istniejące testy `test_weather.py` przechodzą bez zmian oczekiwanego
      JSON-a.
- [x] Nowe testy dowodzące, że model faktycznie coś odrzuca (brakujące pole,
      zła wartość `source`), nie tylko dokumentuje.
- [x] `ruff check`/`ruff format --check` czyste.

## Dependencies

Brak (niezależne od PR #45/#47/#49/#50/#51 — inny plik).

## Data Contract

Bez zmian.

## Security

Brak nowej powierzchni.

## Architecture Impact

Brak.
