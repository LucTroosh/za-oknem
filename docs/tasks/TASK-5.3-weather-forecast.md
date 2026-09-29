# TASK 5.3 — Forecast (§30 Master Planu)

## Goal

Dodać model `Forecast`, odrębny od `Measurement`/`WeatherSnapshot` (rule #7),
i wystawić prognozę dzienną pogody z Open-Meteo pod `GET /api/v1/weather/forecast`.
Domyka ostatni TODO z Phase 5 (Weather) w ROADMAP.md.

## Scope

- `app/models.py`: nowy model `Forecast` (`geo_area_id`, `param_code`, `value`,
  `unit`, `model`, `forecast_reference_time`, `valid_from`, `valid_until`,
  `fetched_at`) + migracja `0006_forecasts.py`. ADR-010.
- `connectors/open_meteo/client.py`: `fetch_current()` → `fetch_weather()`,
  dołącza `daily=...` do TEGO SAMEGO zapytania co `current` (jedno wywołanie
  HTTP, nie dwa).
- `connectors/open_meteo/parser.py`: nowa `normalize_forecast()` — mapuje
  równoległe tablice `daily`/`daily_units` na listę rekordów Forecast, jeden
  per (dzień, param). `forecast_reference_time` = nasz `fetched_at`
  zaokrąglony w dół do 3-godzinnego okna (ADR-004/ADR-010) — nie surowy fetch,
  żeby reruny w tym samym cyklu były idempotentne (rule #40).
- `connectors/open_meteo/ingest.py`: `ingest_geo_area()` przechowuje teraz
  oba typy rekordów z jednego fetcha; parsowanie `current` i `daily` odbywa
  się w niezależnych `try/except` (błąd w jednym nie kosztuje danych z
  drugiego — rule #1, wzorzec z TASK-9.3).
- `api/v1/weather.py`: nowy `GET /api/v1/weather/forecast` — najświeższa
  prognoza per (geo_area, dzień, param), tylko dni, które jeszcze nie minęły.

## Acceptance Criteria

- [x] `Forecast` to osobna tabela od `Measurement`/`WeatherSnapshot`, bez
      pól z jednych mylonych z drugimi (rule #7).
- [x] `normalize_forecast()` zwraca jeden rekord per (dzień, param) z
      poprawnym `valid_from`/`valid_until` (test:
      `test_normalize_forecast_sets_valid_from_and_until`).
- [x] `forecast_reference_time` jest zaokrąglone do 3h okna, nie surowym
      `fetched_at` (test: `test_normalize_forecast_bucket_reference_time_to_3h_cycle`).
- [x] Dwa fetche w tym samym oknie 3h dają identyczny `source_record_id`
      (idempotencja, rule #40) — test:
      `test_normalize_forecast_two_fetches_in_same_cycle_get_same_source_record_id`.
      Dwa fetche w RÓŻNYCH oknach dają różny — test:
      `test_normalize_forecast_different_cycles_get_different_source_record_id`.
- [x] `model` = dokładna, udokumentowana wartość domyślna Open-Meteo (`"auto"`),
      nie wymyślona etykieta (test: `test_normalize_forecast_model_is_open_meteo_default`).
- [x] Błąd w bloku `current` nie blokuje zapisania poprawnego `daily` i
      odwrotnie (testy: `test_ingest_geo_area_stores_forecast_even_when_current_block_is_broken`,
      `test_ingest_geo_area_stores_current_even_when_daily_block_is_broken`).
- [x] `GET /api/v1/weather/forecast` grupuje po lokalizacji i dniu, dni
      posortowane rosnąco (test: `test_weather_forecast_days_are_sorted_ascending`).
- [x] Osierocona prognoza (usunięty `geo_area`) nie pojawia się w odpowiedzi
      (test: `test_weather_forecast_skips_row_for_deleted_geo_area`).

## Tests

`apps/api/tests/connectors/test_open_meteo_{parser,ingest}.py`,
`apps/api/tests/test_weather.py`.

## Non-goals

- Prognoza godzinowa (`hourly`) — tylko dzienna na start.
- Wykorzystanie historii prognoz w UI (dane są append-only i zachowane, ale
  nic jeszcze ich nie czyta poza "najświeższa prognoza per dzień").
- Zmiana cyklu fetchowania (ADR-004) — forecast korzysta z tego samego
  uruchomienia co current, bez nowego joba w schedulerze.

## Dependencies

Migracja `0006_forecasts.py`. ADR-010. Bez zmian w `open_meteo` scheduler joba
(`run_open_meteo` już wywołuje `ingest_geo_area`, które teraz robi więcej).

## Data Contract

`GET /api/v1/weather/forecast` → `{"areas": [{"geo_area_id", "slug", "name",
"latitude", "longitude", "model", "source": "open_meteo", "days": [{"valid_from",
"valid_until", "forecast_reference_time", "params": {param_code: {"value", "unit"}}}]}]}`.

## Security

Brak zmian — te same dane z tego samego już-zaufanego publicznego API (Open-Meteo).

## Architecture Impact

ADR-010 — nowy typ danych (`Forecast`) w modelu, zgodnie z rule #12.
