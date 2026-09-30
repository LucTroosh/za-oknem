# TASK 7.7 + 7.8 — `outdoor` w dashboardzie i `OutdoorCard` (§55/§56/§58)

## Goal

Pokazać użytkownikowi wynik silnika z TASK-7.6 (ADR-016): backend dokłada blok
`outdoor` do każdego obszaru w `GET /api/v1/dashboard/latest` (7.7), a mobile
pokazuje go jako kartę w Home per lokalizacja (7.8). Wartość DERIVED, nie dane
bezpieczeństwa (rule #10).

## Scope

- `apps/api/app/api/v1/dashboard.py`: `_outdoor_block()` + mapowanie wejść;
  `tests/test_dashboard.py`.
- `apps/mobile/app/outdoor.ts` (+ `outdoor.test.ts`): czysty moduł formatujący;
  `apps/mobile/components/OutdoorCard.tsx` (poza `app/`, żeby expo-router nie
  zrobił z niego trasy); w `app/index.tsx` tylko import, pole typu, `loadedAt`
  i jeden `<OutdoorCard>`.

## Acceptance Criteria

1. Każdy obszar ma `outdoor` (także bez pogody i bez stacji: wtedy `UNKNOWN`
   + `missing[]`, nigdy brak pola / ciche GOOD).
2. Liczone wyłącznie z wierszy już pobranych przez `dashboard_latest()` —
   zero nowych zapytań, zero wywołań zewnętrznych API (rule #14); kolejność
   zapytań (areas, stations, weather, forecasts, alerts) bez zmian.
3. Jednostki: wejście trafia do silnika tylko, gdy zapisana `unit` jest DOKŁADNIE
   oczekiwana (`°C`, `mm`, `km/h`, `""` dla UV, `m`, `µg/m³`); inna jednostka =
   wejście pominięte (`None`) → `missing[]`, bez konwersji.
4. Freshness każdego wejścia = per-param `freshness` z dashboardu (rule #8);
   nieświeże nie wpływa na ocenę (robi to silnik).
5. `level`, `reasons[]`, `missing[]` dosłownie z `OutdoorResult` — backend nie
   klasyfikuje drugi raz.
6. Mobile: etykiety PL, poziom czytelny bez koloru (tekst + ikona ✓ ! ✕ ?);
   tekst przyczyn to samo formatowanie wartości/progu/jednostki z danych;
   `UNKNOWN` → „Brak oceny — brak danych: …”; brak pola `outdoor` (starszy
   backend) → karta się nie renderuje, bez wyjątku; nieznany/zły poziom → UNKNOWN.
7. Backend zwraca `valid_until` = najwcześniejszy moment, w którym użyteczne
   wejście (FRESH/RECENT, tylko te faktycznie podane silnikowi) staje się STALE
   (`observed_at` + `RECENT_MAX_AGE` air 6 h / weather 8 h); `null`, gdy żadne
   wejście nie zasilało oceny. Ekran sam się nie odświeża, więc po `valid_until`
   (zegar urządzenia) karta przestaje twierdzić ocenę → „Brak oceny — dane mogły
   się zestarzeć” (lekcja PR #59/#61; Codex PR #68: stały limit od odebrania
   odpowiedzi mylił się dla odczytów tuż przed wygaśnięciem). Bez poprawnego
   `valid_until`: zapasowy limit 1 h od odebrania odpowiedzi.
8. Bez nowych zależności, bez migracji, bez `response_model` (TASK-2.1).

## Tests

- `test_dashboard.py`: pełne dobre dane → GOOD; payload `reasons[]` z silnika;
  niezgodna jednostka (PM2.5 80 w mg/m³ nie daje POOR, nie jest konwertowana);
  jedno PM wystarcza, brak drugiego raportowany `blocking=false`; STALE wiatr →
  UNKNOWN; brak danych → UNKNOWN.
- `outdoor.test.ts`: formatowanie przyczyn (gt/gte/lt/lte, jednostka pusta,
  przecinek), listy braków, null przy braku pola, UNKNOWN, nieznany poziom,
  śmieciowe dane, `valid_until` (granica, długi termin, zapasowy limit).

## Non-goals

- Preferencje/profil użytkownika (TASK-12.4: kiedy pokazywać kartę, dla kogo
  istotna, wrażliwość progów) — karta jest dziś zawsze widoczna; punktem
  wpięcia pozostaje `rules` w `evaluate()` i ewentualny warunek renderu.
- `response_model` dashboardu (TASK-2.1), prognoza godzinowa „kiedy wyjść”,
  zmiana progów, `basis` progów w payloadzie (zostaje w tabeli `RULES`/ADR-016).
- Rozróżnienie w `missing[]` „brak” vs „niezgodna jednostka” (silnik ma tylko
  MISSING/STALE/INVALID; zmiana kontraktu silnika poza zakresem).

## Dependencies

TASK-7.6 (ADR-016), TASK-4.1 (PM2.5/PM10), TASK-5.x (pola pogody, per-param
freshness z PR #56), ADR-004/ADR-012 (freshness).

## Data Contract

`areas[].outdoor`:
`{level: GOOD|MODERATE|POOR|UNKNOWN, reasons: [{code, param, value, threshold,
comparison: gt|gte|lt|lte, unit, level: MODERATE|POOR}], missing: [{group,
params[], status: MISSING|STALE|INVALID, core, blocking}], valid_until: ISO|null}`.
Mapowanie: GIOŚ `PM2.5`/`PM10` → `pm25`/`pm10` (tylko stacja w zasięgu 50 km,
ADR-006); pola Open-Meteo po nazwie `param_code`. Klient traktuje pole jako
opcjonalne.

## Security

Brak nowych sekretów/uprawnień/zapytań zewnętrznych. Ocena nie zastępuje
ostrzeżeń IMGW (komunikat na karcie); LLM nie uczestniczy (rule #10).

## Architecture Impact

Brak zmiany kontraktu silnika, więc ADR-016 bez zmian. Dashboard dostaje jeden
dodatkowy blok per obszar liczony w pamięci z już załadowanych wierszy.
