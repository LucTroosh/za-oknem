# ADR-019: Geo Engine = PostGIS (surowy SQL, bez geoalchemy2), point-in-polygon jako jedyna metoda przynależności administracyjnej

**Status:** Proposed (do zaakceptowania wraz z merge PR TASK-6.2)
**Data:** 2026-09-30

## Context

ADR-005 odłożył pełny model TERYT/gmina do Phase 6; ADR-006 świadomie nie wprowadzał
PostGIS „dopóki Phase 6 Geo Engine tego faktycznie nie zażąda"; ADR-002 wymaga, by Alert
Engine i Push dopasowywały do `geo_area_id` przez przynależność administracyjną
(point-in-polygon), nie dystans. BACKLOG TASK-6.2 (1)–(6) mówi wprost: import gmin z
granicami + PostGIS. Stack (CLAUDE.md) zakłada „PostgreSQL + PostGIS".

Stan repo zweryfikowany przed decyzją: `docker-compose.yml` i `.github/workflows/ci.yml`
używają JUŻ obrazu `postgis/postgis:16-3.4` (zmiana obrazu nie jest potrzebna), ale żadna
migracja nie tworzy rozszerzenia. Testy jednostkowe działają na SQLite (`conftest.py`).

## Problem

Jak wykonać deterministyczne, testowalne (rule #9) lat/lon → gmina dla ok. 2,5 tys.
wielokątów, bez psucia testów na SQLite, bez zbędnych zależności i bez rozjechania
`alembic check`?

## Options

**A. PostGIS, surowy SQL (`ST_Covers`) przez `text()`; kolumna `geometry(MultiPolygon,4326)`
zadeklarowana w migracji, w modelu cienki `TypeDecorator` (bez geoalchemy2).** Jedna
implementacja algorytmu (w bazie), indeks GiST, zero nowych zależności Pythona.

**B. PostGIS + `geoalchemy2` (+ ewentualnie `shapely`).** Wygodniejsze typy/ORM, ale nowa
zależność (rule: bez zależności bez uzasadnienia), której w tym środowisku nie da się nawet
zainstalować lokalnie do weryfikacji; ORM-owy typ geometrii nie jest nam potrzebny — nigdy
nie materializujemy geometrii w Pythonie.

**C. Bez PostGIS: geometrie w JSON/WKB, point-in-polygon w Pythonie (ray casting / shapely)
z bbox-prefiltrem.** Łatwe do testu na SQLite, ale: druga implementacja algorytmu do
utrzymania i weryfikacji (brzeg, dziury, wielopoligony, poprawność geometrii), ładowanie
~2,5 tys. wielokątów do pamięci procesu API, brak indeksu przestrzennego; sprzeczne z
zakresem (6) BACKLOG i stackiem.

## Decision

Opcja **A**.

- Migracja `0011`: `CREATE EXTENSION IF NOT EXISTS postgis`; `geo_areas` dostaje
  `teryt_code` (7 cyfr, unikalny), `boundary geometry(MultiPolygon,4326)` + indeks GiST
  `ix_geo_areas_boundary`, `weather_polling_active` (NOT NULL, server default true).
  Migracja nie wymaga danych: nowe kolumny są nullable/z defaultem, 7 zaseedowanych miast
  działa jak dotąd (polling włączony).
- **Rozdział ról (BACKLOG (4)):** „gmina do geo-matchingu" = każdy wiersz z `teryt_code` +
  `boundary`; „gmina z aktywnym pollingiem pogody" = `weather_polling_active`. `run_open_meteo`
  odpytuje wyłącznie te drugie. Nowo importowane gminy mają `false`. Dodatkowo
  `dashboard_latest` listuje tylko aktywne (do czasu TASK-6.2(8), inaczej import wyprodukowałby
  ~2,5 tys. obszarów w jednym requeście).
- **Semantyka resolvera** (`app/geo.py::resolve_gmina`): `ST_Covers` (punkt na granicy
  należy do wielokąta); na wspólnej granicy dwóch gmin wynik deterministyczny — najniższy
  `teryt_code`; dziura (eksklawa) nie należy do gminy otaczającej, tylko do gminy
  w dziurze, jeśli istnieje; poza wszystkimi wielokątami (np. poza Polską) — brak
  dopasowania (`None`), NIGDY „najbliższa gmina". Dystans (haversine, ADR-006) zostaje
  wyłącznie do dopasowania do stacji/punktów pomiarowych.
- **Zaseedowane miasta** dostają `teryt_code`+`boundary` przy imporcie przez
  point-in-polygon ich współrzędnych (nie po nazwie), zachowując `id`/`slug`, więc
  historia `weather_snapshots` zostaje podpięta.
- **alembic check:** `geometry` jest refleksjonowane jako `NullType`, a PostGIS tworzy
  tabelę `spatial_ref_sys`, której żaden model nie deklaruje. `migrations/env.py` dostaje
  `include_object` (pomija `spatial_ref_sys`) i `compare_type` (nie porównuje typu
  `MultiPolygon4326`). Kolumna `boundary` jest `deferred`, żeby `select(GeoArea)` nie
  ciągnęło wielokątów.
- **Testy:** logika algorytmu jest w SQL, więc testy brzegu/dziury/„poza Polską"/importera
  to zestaw `tests/test_postgis_geo.py` (marker `postgis`), uruchamiany na prawdziwej bazie
  z `DATABASE_URL` (w CI: service `postgis/postgis:16-3.4`, już po `alembic upgrade head`)
  i SKIPowany, gdy PostGIS nie jest osiągalny — testy na SQLite nie są ruszane (kolumna
  degraduje tam do TEXT). Endpoint jest testowany z podstawionym resolverem.
- **Prywatność (ADR-002):** `POST /api/v1/geo/resolve` przyjmuje współrzędne w body
  (nie w query stringu, więc nie trafiają do access logów), nie loguje ich, nie zapisuje
  i nie odsyła w odpowiedzi; zwraca tylko gminę. Błąd bazy daje 503 ze stałym komunikatem
  (bez parametrów zapytania; `hide_parameters=True` w engine), a 422 nie zawiera pola `input`.

## Consequences

- **CI:** bez zmian w `ci.yml` (obraz PostGIS już jest); `alembic upgrade head` i
  `alembic check` obejmują teraz rozszerzenie. Nie zweryfikowano lokalnie (brak
  PyPI/Dockera w środowisku autora) — pierwszy realny dowód to CI tego PR.
- **Dev / prod:** `docker-compose.yml` już na PostGIS. Produkcja (Ubuntu + Docker na VPS)
  musi używać obrazu z PostGIS, a rola migrująca — mieć prawo `CREATE EXTENSION` (PostGIS
  nie jest „trusted"); na zarządzanym Postgresie trzeba to włączyć z góry.
- **Backup:** `pg_dump` zapisze `CREATE EXTENSION postgis`; instancja `restore_test.sh`
  musi mieć PostGIS (opisane w `infrastructure/scripts/README.md`). Manifest już liczy
  `geo_areas`. Niezweryfikowane na realnym dumpie.
- **Downgrade 0011** usuwa kolumny i wiersze `teryt-*` niereferencjonowane przez inne
  tabele (przerywa błędem, jeśli któreś są referencjonowane), ale zostawia rozszerzenie
  (niedestrukcyjnie).
- **Koordynacja migracji:** 0011 wskazuje `down_revision = "0009"` (head na main w chwili
  PR); 0010 zajmuje inny PR — drugi z mergowanych przepina `down_revision`.
- **Dane:** repo nie zawiera granic. Zaimportowanie realnych gmin wymaga pliku od
  człowieka i zatwierdzenia licencji (source-registry: `prg_gminy`, status DISCOVERY).
  Do tego czasu resolver zwraca `None` (nie da się tego odróżnić od „poza Polską" —
  akceptowalne, bo nic nie jest jeszcze produkcyjnie zależne od resolvera).
- **Poza tym ADR:** odkrywanie stacji GIOŚ per gmina (BACKLOG (7)) i zawężenie dashboardu
  do wybranej lokalizacji (8) — osobne zadania (patrz `docs/tasks/TASK-6.2-geo-engine-foundation.md`).
