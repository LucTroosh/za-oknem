# ADR-012: Source-level freshness (stan UNAVAILABLE)

- **Date:** 2026-09-30
- **Status:** Accepted

## Context

Rule #8 wymaga czterech stanów: FRESH / RECENT / STALE / UNAVAILABLE. Dziś
freshness jest liczona wyłącznie per wiersz (`observed_at` / `fetched_at`
rekordu) dla `/air`, `/hydro`, `/alerts`, `/weather` i agregatu
`/dashboard/latest`. ADR-009 świadomie odłożył przypadek, w którym **nie ma
wierszy**.

## Problem

Pusta lista jest niejednoznaczna. Dla `/alerts` (dane bezpieczeństwa)
`items: []` może znaczyć „IMGW potwierdza brak ostrzeżeń” albo „od dwóch dni
nie udało się pobrać IMGW”. Nie da się tego odróżnić z samych danych, bo przy
braku ostrzeżeń nie ma żadnego wiersza, którego `fetched_at` mógłby cokolwiek
powiedzieć. Pokazanie użytkownikowi „brak ostrzeżeń” w drugim przypadku to
fałszywe „wszystko w porządku”.

## Options

1. **Wyprowadzać stan z `max(fetched_at)` wierszy.** Nie działa dla pustej
   listy — dokładnie tego przypadku dotyczy problem.
2. **Pełny model surowego pobrania (`source_fetches`, TASK-3.1)** — źródło,
   endpoint, surowy payload, FK z rekordów. Rozwiązuje też ten problem, ale to
   duża zmiana (retencja payloadów, integracja z każdym connectorem) i wciąż
   nie ma jej w kolejce jako gotowej.
3. **Lekka tabela stanu źródła (`source_status`)** — jeden wiersz na źródło:
   `last_attempt_at`, `last_success_at`, `last_error`, aktualizowany przez
   scheduler po każdym przebiegu joba.

## Decision

Opcja 3.

- `source_status` w PostgreSQL (rule #2 — stan musi przetrwać restart), jeden
  wiersz per `source_id`, upsert po każdym przebiegu joba w schedulerze
  (`_run_job_safely`). Sukces = job zakończył się bez wyjątku; job, który się
  świadomie pomija (np. GIOŚ bez `GIOS_STATION_IDS`), nie zapisuje niczego.
- Freshness źródła liczona z `last_success_at` tymi samymi progami co
  freshness wierszy danej domeny (ADR-004); **UNAVAILABLE**, gdy nie ma
  żadnego udanego pobrania.
- Kontrakt: listy, w których pusty wynik ma znaczenie (dziś: ostrzeżenia),
  niosą `source_status` per źródło. Klient **nie może** pokazać pustej listy
  jako „brak ostrzeżeń”, jeśli którekolwiek źródło tej listy ma stan STALE lub
  UNAVAILABLE — wtedy pokazuje stan „niedostępne” z czasem ostatniej udanej
  aktualizacji.
- `last_error` jest tylko do diagnostyki operacyjnej, nie trafia do API.

## Consequences

- Rozróżnienie „potwierdzone zero” vs „źródło milczy” dla ostrzeżeń,
  wymagane przed pokazaniem stanu „brak ostrzeżeń” komukolwiek.
- Sukces joba jest sygnałem na poziomie całego przebiegu. Joby, które
  izolują błędy per element (Open-Meteo per gmina, GIOŚ per stacja — rule #1),
  mogą zakończyć się „sukcesem” mimo częściowych błędów; dla nich per-wiersz
  freshness pozostaje źródłem prawdy, a `source_status` mówi tylko, że
  scheduler działa. `ponytail:` — rozbicie per element, jeśli kiedyś będzie
  potrzebne dla tych domen.
- Pollen (TASK-8.x) i woda/kąpieliska (TASK-11.x) muszą reużyć ten sam model,
  nie definiować własnego.
- TASK-3.1 (`source_fetches`) może w przyszłości zastąpić tę tabelę jako
  źródło `last_success_at`; kontrakt API się wtedy nie zmienia.
