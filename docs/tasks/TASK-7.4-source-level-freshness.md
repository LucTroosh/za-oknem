# TASK 7.4 — Source-level freshness / UNAVAILABLE (ADR-012)

## Goal

Odróżnić „źródło potwierdza pustą listę” od „źródło milczy” (rule #8, stan
UNAVAILABLE) — wymagane, zanim użytkownik zobaczy „brak ostrzeżeń”.

## Scope

- ADR-012 (`docs/architecture/ADR-012-source-level-freshness.md`).
- Model `SourceStatus` + migracja `0008_source_status.py`.
- `app/source_status.py`: `record_source_run()` (upsert) i
  `source_freshness()` (FRESH/RECENT/STALE z `last_success_at` wg progów
  domeny, UNAVAILABLE bez udanego pobrania).
- `scheduler._run_job_safely`: zapis każdego przebiegu (sukces / błąd z
  komunikatem); job pominięty (`run_gios` bez `GIOS_STATION_IDS`) nic nie
  zapisuje; błąd zapisu nie przerywa schedulera (rule #1).
- `/alerts/latest` i blok `alerts` w `/dashboard/latest`: `source_status` per
  źródło ostrzeżeń (dziś `imgw_warningshydro`).
- Mobile: `summarizeAlerts()` — „Brak aktywnych ostrzeżeń: <źródła>” tylko gdy
  wszystkie źródła FRESH/RECENT; inaczej „Ostrzeżenia chwilowo niedostępne
  (ostatnia aktualizacja …)” albo dopisek „lista może być nieaktualna”.

## Non-goals

- `source_status` dla `air`/`weather`/`hydro` w agregacie — tam per-wiersz
  freshness już pokazuje wiek danych; pusta lista nie jest tam komunikatem
  bezpieczeństwa. Rozszerzyć, gdy UI zacznie pokazywać „brak danych” jako
  stan (TASK-7.3), tym samym modelem.
- Granularność per element dla jobów izolujących błędy per gmina/stację
  (ADR-012 Consequences).

## Acceptance Criteria

- [x] Brak udanego pobrania → UNAVAILABLE; tylko porażki → UNAVAILABLE;
      porażka po sukcesie zachowuje `last_success_at`; stary sukces → STALE
      (`test_source_status.py`).
- [x] Scheduler zapisuje sukces/porażkę, pominięty job nic, błąd zapisu nie
      rzuca (`TestSourceStatusRecording`).
- [x] `/alerts/latest` zwraca `source_status` (pusta lista + świeży sukces =
      FRESH; stary sukces = STALE) (`test_alerts.py`).
- [x] Mobile nigdy nie pokazuje „brak ostrzeżeń” przy STALE/UNAVAILABLE/braku
      statusów (`alerts.test.ts`).
- [x] Migracja Alembic (rule #4); `ruff check` czyste; CI.

## Dependencies

PR #58 (TASK-7.2, blok `alerts` w agregacie) — ten PR jest na nim oparty.

## Data Contract

Nowa tabela `source_status`. Addytywne pole `source_status` w
`/alerts/latest` i w `alerts` z `/dashboard/latest`.

## Security

`last_error` tylko w bazie (diagnostyka), nigdy w API.

## Architecture Impact

ADR-012 (Accepted).
