# TASK 13.1 — Source health / stale monitoring (część operatorska)

## Goal

Operator widzi jednym wywołaniem, które źródło jest zdrowe, a które milczy, bez
zaglądania do bazy i bez czekania na skargę z aplikacji. Po cichu nieaktualne
źródło to dokładnie ryzyko z rule #8; dziś stan źródła (ADR-012) jest widoczny
tylko wewnątrz odpowiedzi `/alerts` i `/hydro`.

## Scope

- `app/source_health.py`: rejestr `SOURCES` (dokładnie źródła zapisujące
  `source_status`: `open_meteo`, `gios`, `imgw_hydro`, `imgw_warningshydro`),
  `collect_source_health()`, `sanitize_error()`, `log_health_transitions()`.
- `GET /api/v1/health/sources`: per źródło `freshness`
  (FRESH/RECENT/STALE/UNAVAILABLE), `last_attempt_at`, `last_success_at`,
  `last_error` (zsanityzowany), `daily_budget {used, limit, used_pct}` (tylko
  źródła z udokumentowanym limitem dziennym, dziś Open-Meteo, licznik z 13.1a).
  Zawsze HTTP 200; `/health` i `/health/ready` bez zmian.
- Scheduler (ADR-007) po każdym ticku ocenia zdrowie i loguje **raz na zmianę
  stanu**: STALE → WARNING, UNAVAILABLE → ERROR, powrót → INFO. Stan poprzedni
  w pamięci procesu (jak reszta schedulera); po restarcie źródło już zepsute
  zostaje zalogowane raz. GIOŚ świadomie wyłączony (brak `GIOS_STATION_IDS`)
  nie jest monitorowany w logach.

## Progi per źródło (rule #16, ADR-004)

Nie ma nowej stałej: każde źródło używa funkcji freshness swojej domeny
(ta sama, której używa jego endpoint danych, więc widoki nie mogą się rozjechać)
na `last_success_at`:

| źródło | cykl | progi FRESH / RECENT |
|---|---|---|
| open_meteo | 3h (ICON, zweryfikowane w registry) | 4h / 8h |
| gios | 1h (pomiary, zweryfikowane) | 2h / 6h |
| imgw_hydro | NIEZNANY (registry), robocze 1h (ADR-008) | 2h / 6h |
| imgw_warningshydro | NIEZNANY, robocze 1h, safety-critical (ADR-009) | 2h / 6h |

Dla obu źródeł IMGW progi to założenie robocze, nie zweryfikowany cykl.
Źródło bez żadnego udanego pobrania = UNAVAILABLE. Sukces w przyszłości
(zegar innego hosta) czyta się jako STALE (istniejące `source_freshness`);
endpoint niczego nie zapisuje, więc nie ma strażnika zapisu opartego na jednym zegarze.

## Czym jest "sukces" źródła

Health wynika z `source_status`, więc wymaga, by job nie raportował sukcesu przy
całkowitej awarii. Dlatego (ponad ADR-012): `ingest_geo_area()` i `ingest_station()`
zwracają `None` (nie `0`) gdy pobranie się nie udało (Open-Meteo także gdy żaden
blok nie dał się sparsować), a `run_open_meteo()`/`run_gios()` rzucają, gdy zawiodły
WSZYSTKIE obszary/stacje (albo `GIOS_STATION_IDS` nie pasuje do żadnej stacji).
Częściowa awaria nadal liczy się jako run (rule #1). Nieobjęte: awaria pojedynczych
parametrów wewnątrz stacji GIOŚ (izolacja per param) - per-row freshness zostaje
tam źródłem prawdy.

## Acceptance Criteria

- [x] Raport zawiera każde z 4 źródeł; nieznane źródło nie jest wymyślane.
- [x] Nigdy nie pobrane lub tylko nieudane = UNAVAILABLE.
- [x] Progi per źródło z domeny, test na różnych wiekach.
- [x] Budżet dzienny tylko tam, gdzie jest limit; 0 gdy brak wywołań dziś.
- [x] `last_error` bez sekretów/query stringów, max 200 znaków.
- [x] Awaria oceny jednego źródła nie psuje raportu pozostałych (rule #1).
- [x] Log raz na przejście stanu, nie co tick; scheduler nigdy nie pada przez monitoring.
- [x] `/api/v1/health` bez zmian.

## Tests

`tests/test_source_health.py`, `tests/test_scheduler.py::TestCheckSourceHealth`.

## Non-goals

- Trwała historia runów i telemetria §44 (duration, records processed,
  validation errors, duplicate/stale rate): wymaga nowej tabeli i ADR-018,
  **pozostaje do zrobienia w ramach TASK-13.1**.
- Zewnętrzny monitoring/Sentry (TASK-13.2, 15.3), dashboard/mobile.
- Autoryzacja endpointu (brak mechanizmu auth w MVP); endpoint nie ujawnia
  sekretów, ale warto ograniczyć go w Caddy przy wdrożeniu (TASK-15.3).

## Dependencies

ADR-012 (`source_status`), TASK-13.1a (`source_fetch_counters`), ADR-004, ADR-007.

## Data Contract

`{"generated_at": iso, "sources": [{"source_id", "freshness", "last_attempt_at",
"last_success_at", "last_error", "daily_budget": {"used","limit","used_pct"} | null}]}`

## Security

Tylko nasza baza (rule #14). `last_error` zsanityzowany: query stringi
wycięte, wartości po `key/token/secret/password/authorization/bearer` zastąpione,
limit 200 znaków. Brak danych użytkowników.

## Architecture Impact

Brak nowej tabeli, migracji ani zależności; ADR-018 niepotrzebny. ADR-012
dopisuje jedyny wyjątek od "last_error nie trafia do API".
