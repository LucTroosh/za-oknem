# ADR-026: Wybór lokalizacji w API — `/areas`, `dashboard?geo_area_id=`, `POST /geo/locate` (nearest active area z limitem)

**Status:** Proposed (do zaakceptowania wraz z merge PR TASK-6.2 (8))
**Data:** 2026-10-01

## Context

TASK-6.2 (8): po imporcie ~2,5 tys. gmin `/dashboard/latest` nie może zwracać „wszystkiego”,
a klient (TASK-12.2/12.3) potrzebuje (a) listy obszarów do wyboru ręcznego, (b) zawężenia
dashboardu do jednego obszaru, (c) drogi GPS/współrzędne → obszar. Obowiązują: ADR-019
(przynależność administracyjna = point-in-polygon; poza gminami `None`, „NIGDY najbliższa
gmina”; dystans tylko do stacji/punktów pomiarowych), ADR-002 (współrzędne tylko w body POST,
bez logowania/zapisu/echa), reguła #11 (brak background location i kont), #14 (API czyta tylko
z bazy), #8 (stare/brak danych widoczne).

## Problem

Co ma zwrócić klientowi punkt, którego resolver nie przypisał do żadnej gminy (poza Polską
albo — dziś — brak zaimportowanych granic), i jak pokazać obszar bez aktywnego pollingu,
bez łamania ADR-019?

## Options

**A. Zmienić `/geo/resolve`, by zwracał „najbliższą gminę”.** Wprost sprzeczne z ADR-019
(psuje geo-matching alertów/push przy nieregularnych granicach).

**B. Nowy `POST /geo/locate` = drabina: point-in-polygon → najbliższy AKTYWNY obszar w
limicie (jawnie) → `out_of_range`; `/geo/resolve` bez zmian (wybrana).**
Fallback dotyczy geografii *danych* (jak nearest-station, ADR-006/025), nie przynależności
administracyjnej; alerty/push nadal używają wyłącznie `resolve_gmina`.

**C. Klient sam liczy najbliższe miasto z listy `/areas`.** Duplikacja reguły po stronie
mobile, brak testu deterministyczności po stronie serwera (reguła #9).

## Decision

Opcja **B**.

- `GET /api/v1/areas[?active_only=true]` — `geo_area_id, slug, name, teryt_code|null, latitude,
  longitude, weather_polling_active`. Domyślnie tylko obszary z aktywnym pollingiem (to samo,
  co dashboard bez parametru); `active_only=false` dodaje zaimportowane gminy bez pollingu.
  `limit` (domyślnie 3000, max 5000) tylko ogranicza odpowiedź; `Cache-Control: public,
  max-age=300` (lista rzadko się zmienia). Wyszukiwanie/paginacja to zakres TASK-12.2.
  `/geo/locate` i `/geo/resolve`: 422 bez `input`/`ctx` (zbiór `COORDINATE_PATHS`).
- `GET /api/v1/dashboard/latest?geo_area_id=N` — `areas` = jeden obszar; nieznany id = 404;
  bez parametru zachowanie jak dotąd (tylko aktywne). Obszar **bez aktywnego pollingu** jest
  zwracany (nie znika), z nowym polem `weather_polling_active=false`: `weather`/`forecast`
  null, `pollen` UNAVAILABLE; `air` wg stacji z katalogu GIOŚ w limicie 50 km (ADR-025:
  `select_stations` działa dla każdego obszaru, to uczciwe i użyteczne); `outdoor` liczony z
  dostępnych danych (silnik: brak rdzenia — temperatura/opad/wiatr — daje UNKNOWN, nie GOOD).
  Klient odróżnia „nikt nie zbiera danych pogodowych” od „zepsute źródło”. `geo_area_id` ma
  walidację 1..2147483647 (422), także w `/air/latest` i `/alerts/latest`; prognoza i pyłki
  są czytane tylko dla wybranego obszaru. `alerts` (krajowe),
  `local_alerts`, `outdoor`, `pollen` mają semantykę bez zmian, tylko dla jednego obszaru.
  Stare pomiary (np. po dezaktywacji) pokazują się ze swoją świeżością (STALE), nie znikają.
- `POST /api/v1/geo/locate` `{latitude, longitude}` → `{status: resolved|out_of_range, area|null,
  assignment_method: point_in_polygon|nearest_area|null, distance_km|null}`:
  1. `resolve_gmina` trafia → `point_in_polygon`, także gdy gmina nie ma aktywnego pollingu
     (odpowiedź administracyjna się nie zmienia; flaga `weather_polling_active` w `area`
     mówi klientowi, że dashboard będzie „brak danych”; aktywację załatwia TASK-12.2);
  2. `resolve_gmina` zwraca `None` → najbliższy **aktywny** obszar w
     `NEAREST_AREA_MAX_KM = 25 km` (inclusive, haversine od środka obszaru, dystans do 1 m,
     tie-break najniższe `geo_area_id`; ta sama czysta funkcja co dobór stacji,
     `geo.nearest_area` → `select_stations`) → `nearest_area` + `distance_km` (1 miejsce);
  3. brak takiego → `out_of_range`, `area: null` („poza zasięgiem”), nigdy dalszy obszar.
  25 km to decyzja produktowa (rząd wielkości miasta + przedmieścia), nie wynik pomiaru;
  zmiana = stała + test granicy. Nieaktywny obszar nigdy nie jest celem fallbacku.
- Prywatność (ADR-002) jak w `/geo/resolve`: POST, współrzędne nie są logowane, zapisywane
  ani odsyłane; błąd bazy = 503 ze stałym komunikatem; 422 bez `input`.
- Kontrakt: nowe modele w Pydantic, `openapi.json` + `schema.ts` zregenerowane (ADR-024).

## Consequences

- Dziś (bez granic PRG) `resolve_gmina` zawsze zwraca `None`, więc każdy punkt w ≤ 25 km od
  jednego z 7 miast dostaje `nearest_area` (jawnie, z dystansem), reszta `out_of_range`.
  Po imporcie granic punkt w Polsce dostaje gminę (`point_in_polygon`); fallback zostaje dla
  punktów poza gminami (granice morskie, zagranica).
- Gmina rozpoznana, ale nieaktywna, daje pusty dashboard z wyjaśnieniem — świadomie nie
  podmieniamy jej na sąsiednie miasto; mechanizm aktywacji pollingu to TASK-12.2.
- `/areas?active_only=false` zwraca do `limit` gmin bez paginacji (~2,5 tys. wierszy) — do
  czasu TASK-12.2 nieużywane przez klienta.
- **Znane ograniczenia (świadomie poza tym PR):** brak rate limitu na `/geo/locate` i `/areas`
  (TASK-14.2); brak `POST` w CORS (`allow_methods=["GET"]`) — klient to aplikacja natywna,
  web poza MVP.
- Parametr `geo_area_id` jest publiczny i wyliczalny (id seryjne): sam odczyt nie może
  aktywować pollingu ani liczyć się jako „aktywność” (zob. BACKLOG TASK-12.2).
