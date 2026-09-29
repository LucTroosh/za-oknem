# TASK 13.1a — Licznik dziennych wywołań + alert 70% (ADR-001/ADR-003/ADR-004)

## Goal

ADR-001, ADR-003 i ADR-004 (wszystkie Accepted) wprost wymagają: "licznik
dziennych wywołań per źródło w bazie, alert przy 70% dziennego limitu" —
konkretnie dla Open-Meteo: 10 000/dzień (ADR-003). Żaden dotychczasowy task
tego nie implementował (potwierdzone: brak tabeli/licznika w kodzie). Bez
tego rosnący zbiór aktywnych gmin (przyszłe TASK-6.2) może po cichu
wyczerpać limit i zostawić pogodę stale dla wszystkich, zanim ktokolwiek to
zauważy (dokładnie ryzyko, które TASK-13.1 z BACKLOG.md nazywa).

**Uwaga:** to podzbiór (mniejszy, natychmiast wykonalny kawałek) pełnego
TASK-13.1 z `docs/tasks/BACKLOG.md` (który obejmuje też pełną per-run
telemetrię z §44 Master Planu — duration, records processed, validation
errors, itd.). Nazwany `13.1a`, żeby nie kolidować z tamtym numerem, gdy
BACKLOG.md wyląduje na `main` (dziś nie-zmergowany PR #45).

## Scope

- `app/models.py`: nowy model `SourceFetchCounter` (source_id, day, count) +
  migracja `0007_source_fetch_counters.py`. Postgres, nie Redis (rule #2 —
  licznik musi przetrwać restart schedulera).
- `app/rate_budget.py` (nowy moduł): `record_fetch_call()` (increment-or-insert
  per (source_id, day)) + `check_daily_budget()` (log WARNING przy ≥70%
  limitu — brak zewnętrznego monitoringu jeszcze, TASK-13.2 zablokowany na
  koncie, więc log to uczciwe MVP, nie no-op).
- `connectors/open_meteo/ingest.py`: wywołanie po każdym udanym
  `client.fetch_weather()` (nie liczone przy `OpenMeteoApiError` — nie da
  się stwierdzić, która próba retry faktycznie dotarła do serwera, więc
  wykluczone z tego dolnego oszacowania zamiast ryzykować przeszacowanie).

## Non-goals

- Pełna per-run telemetria z §44 (duration, validation errors, duplicate
  rate) — to reszta TASK-13.1 z BACKLOG.md, osobny, większy task.
- GIOŚ/IMGW — GIOŚ ma już własny per-minutowy throttling
  (`_throttle_list_endpoint`), bez udokumentowanego dziennego limitu w
  Source Registry; IMGW nie ma udokumentowanego limitu w ogóle. Dodać, gdy
  faktycznie się pojawi udokumentowany dzienny limit dla innego źródła
  (YAGNI) — `rate_budget.py` jest już źródło-agnostyczny, gotowy do
  ponownego użycia.
- Realna liczba "jednostek rozliczeniowych" Open-Meteo (ADR-003 wspomina,
  że nasze ~22 zmienne mogą liczyć się jako więcej niż 1 "API call" — nie
  jest to udokumentowane w sposób pozwalający to policzyć bez zgadywania).
  Ten licznik liczy surowe requesty HTTP — uczciwe dolne oszacowanie, nie
  precyzyjna wartość, jawnie opisane w kodzie.

## Acceptance Criteria

- [x] Jeden wiersz per (source_id, day), inkrementowany, nie duplikowany
      (test: `test_record_fetch_call_increments_same_day`).
- [x] Osobny wiersz per dzień i per źródło (testy: `..._separate_row_per_day`,
      `..._separate_row_per_source`).
- [x] `check_daily_budget()` loguje WARNING dokładnie przy ≥70%, cicho
      poniżej (testy: `test_check_daily_budget_*`).
- [x] `ingest_geo_area()` liczy wywołanie tylko po udanym fetchu, nie przy
      `OpenMeteoApiError` (testy: `test_ingest_geo_area_records_a_daily_fetch_call`,
      `..._does_not_record_a_call_on_api_failure`).
- [x] `ruff check`/`ruff format --check` czyste.

## Dependencies

Brak (niezależne od PR #45/#47/#49/#50/#51/#52/#53/#54 — inne pliki; drobny
konflikt merge'owy z PR #50 w `ingest.py` jest oczekiwany i trywialny do
rozwiązania przy mergu, bo oba dodają kod w tym samym miejscu niezależnie).

## Data Contract

Nowa tabela `source_fetch_counters` — bez zmian w istniejących kontraktach.

## Security

Brak nowej powierzchni.

## Architecture Impact

Nowy typ trwałych danych (licznik), ale bez nowej decyzji architektonicznej
— realizuje explicit, już zaakceptowane wymaganie z ADR-001/ADR-003/ADR-004,
więc nie wymaga nowego ADR (rule #12 dotyczy zmian architektury, nie
implementacji już podjętej decyzji).
