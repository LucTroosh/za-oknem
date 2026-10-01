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
- Zapis wykonuje **każdy punkt wejścia ingestu** źródła, które wystawia
  `source_status` — scheduler i ręczne CLI (`python -m app.connectors.…ingest`),
  bo operator może używać tylko jednej z tych ścieżek. Niepełny snapshot
  (odrzucone rekordy) to porażka, nie sukces.
- Freshness źródła liczona z `last_success_at` tymi samymi progami co
  freshness wierszy danej domeny (ADR-004); **UNAVAILABLE**, gdy nie ma
  żadnego udanego pobrania.
- Kontrakt: listy, w których pusty wynik ma znaczenie (dziś: ostrzeżenia),
  niosą `source_status` per źródło. Klient **nie może** pokazać pustej listy
  jako „brak ostrzeżeń”, jeśli którekolwiek źródło tej listy ma stan STALE lub
  UNAVAILABLE — wtedy pokazuje stan „niedostępne” z czasem ostatniej udanej
  aktualizacji.
- `last_error` jest tylko do diagnostyki operacyjnej, nie trafia do API mobilnego
  (`/alerts`, `/hydro`, `/dashboard`). Jedyny wyjątek: operatorski
  `GET /api/v1/health/sources` (TASK-13.1) zwraca go zsanityzowanego (bez query
  stringów i userinfo URL; komunikat z czymkolwiek przypominającym poświadczenia
  redukowany do typu wyjątku; max 200 znaków).

## Consequences

- Rozróżnienie „potwierdzone zero” vs „źródło milczy” dla ostrzeżeń,
  wymagane przed pokazaniem stanu „brak ostrzeżeń” komukolwiek.
- Sukces joba oznacza, że źródło dało dane, nie tylko że nic nie wyrzuciło wyjątku
  (TASK-13.1). Joby izolujące błędy per element stosują jedną politykę
  (`source_status.run_failure_reason`): run jest porażką, gdy nic nie wróciło,
  żaden element się nie udał albo odsetek nieudanych przekracza próg źródła;
  poniżej progu to (częściowy) sukces.
  - IMGW hydro (~900 stacji): próg **2%** odrzuconych stacji. Jedna na stałe
    uszkodzona stacja nie może trzymać całego `/hydro` w STALE/UNAVAILABLE
    (rule #1). ID odrzuconych stacji trafiają do `logger.warning` w każdym runie,
    a provenance zapisuje partial.
  - Open-Meteo (gminy) i GIOŚ (stacje): małe, jawnie skonfigurowane zbiory,
    więc próg **50%** (awaria większości = awaria źródła; przy 1-2 elementach
    jedna porażka z dwóch jeszcze nie).
  - **Ostrzeżenia IMGW zostają ścisłe**: jakikolwiek odrzucony rekord to
    porażka, bo odrzucony rekord może być właśnie aktywnym alertem (fałszywe
    „brak ostrzeżeń" jest groźniejsze niż STALE).
  Znane ograniczenia: Open-Meteo traktuje obszar jako porażkę tylko gdy padł
  fetch albo wszystkie 3 bloki (awaria 1-2 bloków w każdym obszarze nadal daje
  „sukces"); sukces oznacza transport, nie świeżość danych (GIOŚ "nic nowego"
  przy zamrożonym feedzie jest sukcesem; tu pomaga per-wiersz freshness).
  `ponytail:` rozbicie per blok i detekcja zamrożonego feedu, jeśli kiedyś potrzebne.
- Pollen (TASK-8.x) i woda/kąpieliska (TASK-11.x) muszą reużyć ten sam model,
  nie definiować własnego.
- TASK-3.1 (`source_fetches`) może w przyszłości zastąpić tę tabelę jako
  źródło `last_success_at`; kontrakt API się wtedy nie zmienia.
