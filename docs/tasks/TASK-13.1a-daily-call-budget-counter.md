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
- `connectors/open_meteo/ingest.py`: `client.fetch_weather()` przyjmuje
  `on_attempt` (callback wołany przez klienta przy KAŻDEJ realnej próbie HTTP,
  sukces czy porażka — LucTroosh review [P1]: liczenie tylko po sukcesie
  zaniżało realne zużycie limitu pod retry), który woła
  `record_fetch_call(units=ESTIMATED_BILLABLE_UNITS_PER_CALL)` — jednostki
  wyliczone z realnej reguły rozliczeniowej Open-Meteo (pricing page), nie
  z flat "1 request = 1 jednostka".

## Non-goals

- Pełna per-run telemetria z §44 (duration, validation errors, duplicate
  rate) — to reszta TASK-13.1 z BACKLOG.md, osobny, większy task.
- GIOŚ/IMGW — GIOŚ ma już własny per-minutowy throttling
  (`_throttle_list_endpoint`), bez udokumentowanego dziennego limitu w
  Source Registry; IMGW nie ma udokumentowanego limitu w ogóle. Dodać, gdy
  faktycznie się pojawi udokumentowany dzienny limit dla innego źródła
  (YAGNI) — `rate_budget.py` jest już źródło-agnostyczny, gotowy do
  ponownego użycia.
- Idealnie precyzyjna liczba jednostek rozliczeniowych Open-Meteo — pricing
  page (https://open-meteo.com/en/pricing, zweryfikowane) opisuje regułę tylko
  dla ≤2 tygodni/jednej lokalizacji ("więcej niż 10 zmiennych lub >2 tygodnie =
  wielokrotność wywołań"); dokładny wzór dla dłuższych zakresów nie jest
  opublikowany. `ESTIMATED_BILLABLE_UNITS_PER_CALL` (ingest.py) liczy z tej
  reguły przez zaokrąglenie w górę (`ceil(liczba_zmiennych / 10)`) — celowo
  konserwatywne (nigdy nie zaniża) oszacowanie, nie dokładna wartość.

## Acceptance Criteria

- [x] Jeden wiersz per (source_id, day), inkrementowany, nie duplikowany
      (test: `test_record_fetch_call_increments_same_day`).
- [x] Osobny wiersz per dzień i per źródło (testy: `..._separate_row_per_day`,
      `..._separate_row_per_source`).
- [x] `check_daily_budget()` loguje WARNING dokładnie przy ≥70%, cicho
      poniżej (testy: `test_check_daily_budget_*`).
- [x] `ingest_geo_area()` liczy KAŻDĄ realną próbę HTTP (sukces i porażkę,
      przez `on_attempt` w `client.fetch_weather()`), ważoną
      `ESTIMATED_BILLABLE_UNITS_PER_CALL` jednostek per próba — nie liczbę
      requestów 1:1 (LucTroosh review [P1]: sam sukces nie mówił, ile
      prawdziwych prób HTTP faktycznie poszło pod retry) (testy:
      `test_ingest_geo_area_records_a_daily_fetch_call`,
      `..._records_every_attempt_even_on_final_failure`).
- [x] Inkrement atomowy (`UPDATE ... RETURNING`), odporny na lost update przy
      współbieżnych wywołaniach tego samego dnia (LucTroosh review [P2])
      (testy: `test_record_fetch_call_units_param_increments_by_that_amount`,
      `..._returns_what_is_actually_persisted`).
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
