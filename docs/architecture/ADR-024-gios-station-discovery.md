# ADR-024: Katalog stacji GIOŚ jako byt + przypisanie obszar → stacja (nearest z limitem)

**Status:** Proposed (do zaakceptowania wraz z merge PR TASK-6.2 (7))
**Data:** 2026-10-01

## Context

`run_gios` pobierał stacje wyłącznie z env `GIOS_STATION_IDS` (ADR-007) — ręczna lista,
niezależna od tego, które obszary są faktycznie obsługiwane. ADR-006 ustalił regułę dla
air: **nearest station, `MAX_MATCH_DISTANCE_KM` = 50 km (inclusive), brak dopasowania = brak
danych** (haversine); ADR-019 zostawia dystans wyłącznie do dopasowania do stacji/punktów
pomiarowych (przynależność administracyjna = point-in-polygon, nie dla stacji). Rejestr
(`gios`): `/station/findAll` aktualizuje się raz do roku, limit 2 zapytania/min, regulamin
≤ 2×/h.

## Problem

Jak deterministycznie (reguła #9) wyznaczać stacje GIOŚ do pollingu i do odpowiedzi API
dla obszaru (`geo_areas`), bez nowego źródła prawdy, bez zwiększania liczby requestów do
GIOŚ (reguła #16) i bez łamania `GIOS_STATION_IDS`?

## Options

**A. Tabela przypisań `area → station` w bazie.** Stan do utrzymania i unieważniania przy
każdej zmianie katalogu lub współrzędnych obszaru; przypisanie jest czystą funkcją danych,
więc to duplikat.

**B. Katalog stacji w bazie (`gios_stations`) + przypisanie liczone czystą funkcją
`geo.select_stations` (nearest w limicie, tie-break po id).** Brak stanu pochodnego.

**C. PostGIS `ST_Distance` na geography.** Druga implementacja dystansu obok haversine
(ADR-006) i nie da się jej testować na SQLite; katalog to setki punktów — nie potrzeba indeksu.

## Decision

Opcja **B**.

- Migracja `0013`: `gios_stations` (`station_id` unikalny, nazwa, lat/lon, `raw` = stacja
  dokładnie jak z GIOŚ, `fetched_at`, `source_fetch_id` → provenance w `source_fetches`,
  payload objęty retencją `gios` = 14 dni).
- **Reguła:** `geo.select_stations(lat, lon, stations, max_km=50, limit=1)` — czysta funkcja;
  dystans zaokrąglony do 1 m, remis rozstrzyga `station_id` (id cyfrowe numerycznie, potem
  tekstowe), więc kolejność wejścia nie ma wpływu. Brak stacji w limicie = pusta lista =
  „brak danych dla obszaru” — NIGDY najbliższa poza limitem. Zwraca `distance_km` i `method`
  (`nearest_station`). Limit 50 km zostaje stałą z ADR-006 (przeniesioną do `app/geo.py`).
- **Polling:** `GIOS_STATION_IDS` ustawione = jedyny źródłowy zestaw (override, zachowanie
  bez zmian, bez katalogu). Puste = stacje przypisane do aktywnych obszarów
  (`polling_areas`) z katalogu w bazie. Brak aktywnych obszarów albo brak stacji w zasięgu =
  job pominięty (`False`, ADR-012), bez requestów.
- **Katalog:** `ensure_catalog` przechodzi `station/findAll` tylko gdy tabela jest pusta lub
  starsza niż 24 h (rejestr: aktualizacja roczna; scheduler nadal 1×/h dla danych, więc liczba
  requestów katalogu SPADA względem dzisiejszego `find_stations` co godzinę przy env).
  Błąd odświeżenia → ostatni katalog (reguła #1), brak katalogu → błąd runu. Stacja
  niewymieniona już przez GIOŚ jest usuwana; wymieniona, ale niepoprawna, zachowuje poprzedni wiersz.
- **API (tylko dodawanie pól):** `dashboard.air` dostaje `assignment_method` (obok istniejących
  `station_id`, `distance_km`); `GET /air/latest?geo_area_id=N` zwraca tylko przypisaną stację
  z `distance_km` + `assignment_method` (brak stacji = `[]`, nieznany obszar = 404; bez
  parametru odpowiedź bez zmian). API wybiera spośród stacji, które mają pomiary, tą samą regułą,
  ale tylko spośród aktualnego katalogu (+ ewentualny override env), o ile katalog już istnieje —
  stacja usunięta z katalogu przez GIOŚ nie zostaje przypisana na zawsze przez stare pomiary.
- **source_health:** `gios` jest „monitored”, gdy jest env, istnieje przypisanie albo (pusty katalog)
  istnieje aktywny obszar — nieudane pierwsze odkrycie ma być widoczne, nie wyglądać na wyłączone źródło.

## Consequences

- Dodanie obszaru z `weather_polling_active` automatycznie włącza GIOŚ dla najbliższej stacji
  (po następnym odświeżeniu katalogu / przy istniejącym katalogu od razu w kolejnym runie).
- Każda polling'owana stacja = 1× `station/sensors` (2/min) + do 7× `getData` na run; liczba
  stacji rośnie z liczbą aktywnych obszarów, a throttle 30 s/stację wydłuża run. Przy
  setkach aktywnych obszarów trzeba będzie cache'ować listę sensorów (poza zakresem; dziś 7 miast).
- Jeśli najbliższa stacja w katalogu nie ma pomiarów (zamknięta/bez czujników), API nie
  „przeskakuje” do dalszej: wybiera spośród stacji z danymi w limicie, a polling dalej
  odpytuje najbliższą z katalogu i liczy ją jako nieudaną (widać w source_health).
- Przynależność administracyjna (alerty, push) nadal wyłącznie point-in-polygon (ADR-019).
- Niezweryfikowane na żywym `findAll` (API 403 ze środowiska autora): test na fixturze
  o kształcie z istniejących testów; pierwszy realny dowód to pierwszy run po wdrożeniu.
