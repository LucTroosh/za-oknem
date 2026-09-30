# TASK 7.2 (część hydrologiczna) — Stany wody na ekranie Home (mobile)

## Goal

Pokazać na Home stany wody IMGW (`GET /api/v1/hydro/latest`) tak, żeby ekran
nie udawał lokalnego kontekstu, którego jeszcze nie mamy, i nigdy nie mówił
„wszystko w porządku” na podstawie starych lub brakujących danych (rule #8).

## Decyzja produktowa (zdecydowana w tym tasku)

Endpoint zwraca WSZYSTKIE wodowskazy w kraju, a geo-matching hydro to Phase 9
(TASK-9.5). Lista setek stacji bez lokalizacji byłaby bezużyteczna, więc sekcja
„Stany wody — cała Polska” pokazuje **tylko stacje w stanie WARNING/ALARM**:
ALARM przed WARNING, limit 5 pozycji + „i N więcej”. Po TASK-9.5 etykieta znika,
a lista zawęża się do okolicy użytkownika.

## Scope

- Mobile: `apps/mobile/app/hydro.ts` (czysta logika) + `hydro.test.ts`;
  w `index.tsx` osobny komponent `HydroSection` z własnym fetchem i własnymi
  stanami loading/error, podpięty jako `ListFooterComponent` (hydro i dashboard
  nie psują się nawzajem — rule #1; hydro nie jest w agregacie wg §55).
- Backend (minimalnie, addytywnie): `/hydro/latest` dostaje `attribution`
  (`IMGW_ATTRIBUTION`, dosłownie z source-registry) i `source_status`
  (ADR-012, wzorzec `alerts_source_status`). CLI ingest `imgw_hydro` zapisuje
  `source_status` jak scheduler (wymóg ADR-012 dla każdego punktu wejścia).
- Komunikaty:
  - lista WARNING/ALARM (z adnotacją „może być nieaktualna”, gdy źródło nie jest
    FRESH/RECENT),
  - „Brak stacji w stanie ostrzegawczym lub alarmowym” — WYŁĄCZNIE gdy źródło
    jest FRESH/RECENT **i** co najmniej jedna stacja ma aktualny odczyt;
    dopisek o liczbie stacji bez progów IMGW (UNKNOWN nie jest „OK”),
  - w przeciwnym razie „dane niedostępne lub nieaktualne” z czasem ostatniej
    udanej aktualizacji.
- Świeżość liczona na urządzeniu względem `Date.now()` (wstrzykiwane `now`
  w testach): ekran nie odświeża się sam, więc etykieta z momentu pobrania
  starzeje się lokalnie (gorsza z: wartość serwera, wiek `observed_at` /
  `last_success_at`; progi 2h/6h jak w `hydro.py`). Timer 60 s przelicza etykiety
  bez refetchu; pull-to-refresh odświeża też hydro.

## Acceptance Criteria

- [x] Nagłówek „Stany wody — cała Polska”; tylko WARNING/ALARM, ALARM pierwsze, limit + licznik „i N więcej”.
- [x] Per stacja: nazwa (z rzeką, jak w API), poziom, progi IMGW, status jako tekst
      (nie tylko kolor), `observed_at` z etykietą świeżości.
- [x] Atrybucja IMGW z API (nie zahardkodowana na kliencie).
- [x] „Brak stanów…” nigdy przy STALE/UNAVAILABLE/pustej liście/starych odczytach.
- [x] Brak pól w odpowiedzi = degradacja bez wyjątku.
- [x] Awaria hydro nie psuje reszty ekranu i odwrotnie.
- [x] Klient niczego nie klasyfikuje (rule #10) — statusy z backendu.

## Tests

- `hydro.test.ts`: sortowanie/limit, none-confirmed tylko przy zdrowym źródle
  i bieżącym odczycie, stale/never-fetched/pusta lista, starzenie względem `now`,
  UNKNOWN, brak pól, nieznany status.
- `test_hydro.py`: `attribution`, `source_status` (UNAVAILABLE/FRESH/STALE),
  schemat wymaga nowych pól. `test_imgw_hydro_ingest.py`: CLI zapisuje
  `source_status` (sukces i porażka).

## Non-goals

- Geo-matching hydro do lokalizacji (Phase 9, TASK-9.5) — do tego czasu etykieta „cała Polska” jest obowiązkowa.
- Ekran szczegółów stacji, wykresy, pełna lista stacji.
- Alert Engine z progów (status pozostaje pochodną odczytu, nie Alertem — rule #7).

## Dependencies

ADR-008, ADR-012, TASK-7.1 (wzorzec source transparency), część alertowa TASK-7.2.

## Data Contract

`GET /api/v1/hydro/latest`: dodane pola `attribution: str` i
`source_status: {freshness: FRESH|RECENT|STALE|UNAVAILABLE, last_success_at: str|null}`;
`stations` bez zmian. Zmiana addytywna, bez migracji.

## Security

Brak nowej powierzchni (publiczny odczyt z naszej bazy, rule #14); LLM nie
uczestniczy (rule #10).

## Architecture Impact

Brak nowej decyzji — realizacja ADR-008/ADR-012; bez nowego ADR.
