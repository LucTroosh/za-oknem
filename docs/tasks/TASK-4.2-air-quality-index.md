# TASK 4.2 — Europejski Indeks Jakości Powietrza (EAQI, EEA)

## Goal

Indeks ogólny oraz indeksy cząstkowe per zanieczyszczenie w `GET /api/v1/air/latest`,
`dashboard_latest()` i na mobile (Home), liczone deterministycznie z naszych pomiarów
GIOŚ wg metodologii EEA. Decyzja i zweryfikowane progi: ADR-015 (opcja C).
Indeks „natywny” GIOŚ (opcja A/B) pozostaje odłożony — nie ma go w tym zadaniu.

## Scope

- `apps/api/app/air_index.py` — czysta funkcja `air_index(params, recent_max_age)`,
  stała `BANDS` (URL źródła w komentarzu), `level_for(param, value)`.
- `air.py`: nowe pole `index` per stacja (`AirIndex`, typowany `response_model`);
  `dashboard.py`: `air.index`. Bez dodatkowych zapytań.
- Mobile: `apps/mobile/app/aqi.ts` (+ `aqi.test.ts`), `components/AirIndexBadge.tsx`,
  minimalna zmiana `index.tsx`.
- ADR-015 (Accepted), wpis `eea_eaqi` w `docs/data/source-registry.md`.

## Acceptance Criteria

1. Progi dosłownie z EEA (5 zanieczyszczeń × 6 pasm, µg/m³, godzinowo), URL + data w
   kodzie i ADR; test porównuje `BANDS` z niezależnie wpisaną tabelą.
2. Indeks ogólny = najgorszy z cząstkowych; `dominant` wskazuje, które zanieczyszczenie.
3. Brak danych nigdy nie daje „dobrego”: bez minimalnego zestawu ((PM2.5 lub PM10) + NO2
   + O3) wynik Good/Fair = `level: null` („brak indeksu”); Moderate+ stoi jako dolne
   ograniczenie z `complete=false`.
4. Wejście STALE/UNAVAILABLE, inna jednostka niż `µg/m³`, NaN/inf/ujemne → pominięte i
   raportowane w `missing` (MISSING|STALE|UNIT|INVALID); bez konwersji.
5. CO i C6H6 poza indeksem (tylko wartości).
6. `valid_until` = najwcześniejsze wygaśnięcie wejścia; mobile po nim nie twierdzi indeksu.
7. Etykieta tekstowa + numer pasma (x/6) + ikona, nie tylko kolor; brak pola w odpowiedzi
   (starszy backend) → brak odznaki, bez wyjątku.
8. Bez migracji (indeks obliczany, nie przechowywany — uzasadnienie w ADR-015).

## Tests

- `apps/api/tests/test_air_index.py` (czysty, także pod gołym `python3`): granice tuż
  pod/na/nad dla każdego zanieczyszczenia i pasma, monotoniczność, najgorszy z cząstkowych,
  minimalny zestaw, stale, jednostka, wartości niepoprawne, CO/C6H6, `valid_until`,
  siatka „pogorszenie wejścia nie poprawia wyniku”.
- `tests/test_air.py`, `tests/test_dashboard.py`: pole `index` w odpowiedziach,
  `response_model`.
- `apps/mobile/app/aqi.test.ts`: etykiety, kroki, degradacja, wygasanie.

## Non-goals

Indeks GIOŚ (`aqindex/getIndex`, własne progi GIOŚ), CAQI, historia indeksu, rekomendacje
zdrowotne, wpływ indeksu na `outdoor` (ADR-016 ma własne progi PM), LLM (rule #10).
`ROADMAP.md`/`BACKLOG.md` aktualizuje koordynator po merge.

## Dependencies

TASK-4.1 (DONE: 7 parametrów w `measurements`). ADR-015.

## Data Contract

Wynik POCHODNY (rule #7: nie Measurement), bez własnej tabeli. Blok:
`{level: GOOD|FAIR|MODERATE|POOR|VERY_POOR|EXTREMELY_POOR|null, complete, params:
{kod: poziom}, dominant: [kod], missing: {kod: status}, valid_until: ISO|null}`.
Kody angielskie wg EEA; etykiety PL w mobile to nasze tłumaczenie (ADR-015).

## Security

Brak nowych sekretów, brak wywołań zewnętrznych w runtime (rule #14). Indeks nie jest
daną bezpieczeństwa (rule #10) i nie zastępuje komunikatów GIOŚ/IMGW.

## Architecture Impact

Jeden nowy czysty moduł, dwa pola w kontrakcie API (addytywne), jeden komponent mobile.
Brak zmian schematu. ADR-015 (rule #12).
