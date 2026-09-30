# TASK 5.4 — Punkt rosy, widoczność, UV index (§5 Master Planu)

## Goal

Domknąć ostatnie trzy pola MVP z §5 (punkt rosy, widoczność, UV index),
świadomie odłożone w TASK-5.1/PR #41, ponieważ Open-Meteo dokumentuje je
tylko pod `hourly`, nie pod `current` (patrz komentarz w
`connectors/open_meteo/client.py`).

## Scope

- `connectors/open_meteo/client.py`: nowa stała `HOURLY_PARAMS =
  "dew_point_2m,visibility,uv_index"`, dołączona do tego samego zapytania
  co `current`/`daily` (jedno wywołanie HTTP, ta sama zasada co ADR-010).
- `connectors/open_meteo/parser.py`: nowa `normalize_hourly_current(...)` —
  znajduje w `hourly.time` indeks godziny odpowiadającej `current.time`
  (obcięty w dół do pełnej godziny — `current` bywa co 15 min, `hourly`
  zawsze co godzinę) i zwraca WeatherSnapshot-ready dict per parametr, tym
  samym `observed_at` co reszta current (spójny freshness).
- `connectors/open_meteo/ingest.py`: wywołanie w OSOBNYM `try/except`
  względem `normalize()`/`normalize_forecast()` (rule #1, wzorzec z
  TASK-5.3) — błąd w nowych polach (np. Open-Meteo nie zwróci `hourly` dla
  jakiegoś punktu) nie może skasować już sprawdzonych current/forecast.
- `api/v1/weather.py`, `api/v1/dashboard.py`: ŻADNYCH zmian — oba czytają
  `WeatherSnapshot` po `param_code` z bazy bez zaszytej listy pól, więc nowe
  parametry pojawią się w odpowiedzi automatycznie.

## Non-goals

- Mobile UI (`apps/mobile/app/index.tsx`) — ekran dziś renderuje tylko
  `temperature_2m` explicite; pokazanie nowych pól to osobny task (i ten
  plik jest w tej chwili modyfikowany w nie-zmergowanym PR #49, więc
  dotykanie go tutaj tylko zwiększyłoby ryzyko konfliktu).
- Weryfikacja żywym zapytaniem do api.open-meteo.com — sandbox ma to
  zablokowane przez robots.txt/proxy (patrz client.py); jak reszta
  connectora, opieramy się na oficjalnej dokumentacji i failujemy głośno
  przy nieoczekiwanym kształcie (rule #10 nie dotyczy pogody, ale zasada
  "nie zgaduj kształtu" tak).

## Acceptance Criteria

- [x] `HOURLY_PARAMS` dociągane w tym samym requeście co `current`/`daily`.
- [x] `normalize_hourly_current()` wybiera właściwy indeks godziny (test na
      `current.time` z niezerowymi minutami, np. `18:15`, dopasowany do
      `hourly.time` zawierającego `18:00`).
- [x] Brakujący/zły kształt `hourly` rzuca `OpenMeteoParseError`, izolowany
      w `ingest.py` tak, by nie skasować już zebranych current/forecast
      (test w `test_open_meteo_ingest.py`).
- [x] `source_record_id` nowych rekordów deterministyczny i idempotentny
      (ten sam wzorzec `geo_area_id:param_code:observed_at`).
- [x] `ruff check`/`ruff format --check` czyste.

## Dependencies

Brak (niezależne od PR #45/#47/#49 — inne pliki).

## Data Contract

`WeatherSnapshot` (bez zmian schematu) z nowymi `param_code`:
`dew_point_2m`, `visibility`, `uv_index`.

## Security

Brak nowej powierzchni — ten sam publiczny, bezpłatny endpoint Open-Meteo.

## Architecture Impact

Brak — rozszerzenie istniejącego connectora, żadnej nowej tabeli/serwisu.
