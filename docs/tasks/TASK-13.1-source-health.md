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
  `last_error` (zsanityzowany), `monitored`, `daily_budget {used, limit, used_pct}` (tylko
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

Health wynika z `source_status`, więc job nie może raportować sukcesu przy awarii.
Polityka jest jedna (`source_status.run_failure_reason`, używana przez scheduler
i CLI): porażka gdy nic nie wróciło, zero udanych elementów albo odsetek
nieudanych ponad próg. Progi: IMGW hydro 2% (~900 stacji, jedna zepsuta stacja
nie może dawać wiecznego STALE; ID odrzuconych w `logger.warning` co run),
Open-Meteo i GIOŚ 50% (małe zbiory). Ostrzeżenia IMGW zostają ścisłe (ADR-012).
`ingest_geo_area()`/`ingest_station()` zwracają `None` przy porażce elementu
(GIOŚ: także gdy każdy parametr z sensorem padł albo stacja nie ma żadnego
monitorowanego sensora; Open-Meteo: fetch padł lub żaden z 3 bloków się nie
sparsował). `last_error` niesie ostatnią przyczynę. Brak `geo_areas` = skip w
schedulerze i `monitored: false` w raporcie (bez alarmu).

Ręczne CLI zapisuje `source_status` tylko dla pełnego przebiegu: hydro zawsze,
open_meteo bez `--slug`, gios gdy `--station-id` = dokładnie `GIOS_STATION_IDS`
(podzbiór nie mówi nic o stanie źródła).

Znane ograniczenia (bez kodu): sukces = transport, nie świeżość danych (GIOŚ
"nic nowego" przy zamrożonym feedzie to sukces; per-row freshness to łapie);
Open-Meteo: awaria 1-2 z 3 bloków w każdym obszarze nadal daje sukces;
`source_health.py` importuje funkcje freshness z routerów API i `DAILY_CALL_LIMIT`
z connectora (wspólny moduł progów odłożony, zbyt duży diff jak na ten PR).

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
"last_success_at", "last_error", "monitored": bool,
"daily_budget": {"used","limit","used_pct"} | null}]}`; `monitored=false` = źródło
świadomie wyłączone (GIOŚ bez `GIOS_STATION_IDS`, Open-Meteo bez `geo_areas`),
nie awaria - klient nie powinien alarmować.

## Security

Tylko nasza baza (rule #14). `last_error` sanityzowany: userinfo URL, query
stringi, IP i host:port maskowane, tokeny typu `sk-...`/długie opaque ciągi
maskowane; od pierwszego słowa kluczowego poświadczeń (token, secret, password,
authorization, bearer, api key, `key=`, credential, signature, cookie) reszta
komunikatu jest ucinana. Typ wyjątku, kody HTTP ("401 Unauthorized"),
"KeyError: 'current'" i liczby zostają. Limit 200 znaków.

## Architecture Impact

Brak nowej tabeli, migracji ani zależności; ADR-018 niepotrzebny. ADR-012
dopisuje jedyny wyjątek od "last_error nie trafia do API".
