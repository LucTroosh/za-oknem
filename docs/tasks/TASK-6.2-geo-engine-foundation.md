# TASK 6.2 — Geo Engine: fundament (PostGIS, model TERYT, importer, resolver)

Pierwszy z kilku małych PR-ów realizujących BACKLOG TASK-6.2. Ten PR dostarcza
infrastrukturę i kod; **nie zawiera danych** (patrz Blokada).

## Goal

Dowolne lat/lon → gmina przez point-in-polygon (rule #9, ADR-002), na PostGIS, z modelem
danych gotowym na pełny import gmin i bez wywracania pollingu pogody.

## Scope (ten PR) — punkty BACKLOG (1)-(6)

- ADR-019 (PostGIS, surowy SQL, bez `geoalchemy2`; CI/compose/backup).
- Migracja `0011`: `postgis`, `geo_areas.teryt_code`, `geo_areas.boundary` (GiST),
  `geo_areas.weather_polling_active` (4: rozdział geo-matching vs polling).
- `run_open_meteo` odpytuje tylko `weather_polling_active`; `dashboard_latest` listuje
  tylko aktywne (bufor do czasu zadania (8)).
- Importer `app/connectors/prg_gminy/` (parser + ingest, z LOKALNEGO GeoJSON, idempotentny,
  walidujący, z raportem i wpisem w `source_fetches`).
- `app/geo.py::resolve_gmina` + `POST /api/v1/geo/resolve` (5).
- Wpisy `prg_gminy`, `teryt` w `docs/data/source-registry.md` (DISCOVERY).

## Non-goals (osobne zadania)

- **(7) Odkrywanie stacji GIOŚ per aktywna gmina — ✅ zrobione w osobnym PR (ADR-025, migracja `0013`, `connectors/gios/discovery.py`, `geo.select_stations`)**; oryginalny opis: katalog stacji (`/station/findAll`,
  aktualizowany raz/rok wg registry) + dobór nearest-station per gmina + polling; dziś
  `run_gios` czyta `GIOS_STATION_IDS`.
- **(8) Zawężenie dashboardu do wybranej lokalizacji — ✅ zrobione w osobnym PR (ADR-026)**:
  `GET /dashboard/latest?geo_area_id=N` (404 dla nieznanego; obszar bez aktywnego pollingu =
  `weather_polling_active=false`, weather/forecast/pollen puste, air wg stacji z katalogu ≤ 50 km, outdoor UNKNOWN bez rdzenia; bez parametru jak dotąd), `GET /areas`,
  `POST /geo/locate` (point-in-polygon → najbliższy AKTYWNY obszar ≤ 25 km jawnie jako
  `nearest_area` z `distance_km` → `out_of_range`; `/geo/resolve` bez zmian, ADR-019).
  Oryginalny opis: parametr `geo_area_id` / `observed_area_code` w `GET /dashboard/latest`;
  usunięcie tymczasowego filtra `weather_polling_active` z tego PR-a (filtr zostaje tylko dla
  wywołania bez parametru, żeby import gmin nie wyprodukował ~2,5 tys. obszarów).
- Mechanizm *włączania* pollingu dla wybranej gminy (TASK-12.x / wygaszanie nieużywanych,
  BACKLOG ~l. 569-590): tu tylko kolumna i domyślne wartości; aktywować można ręcznie
  `UPDATE geo_areas SET weather_polling_active = true WHERE teryt_code = '...'`
  (z pilnowaniem budżetu Open-Meteo 10 000/dzień).
- `POST /api/v1/devices` z serwerowym resolve (TASK-12.5); Alert geo-matching (Phase 9).
- Brak zmian w CORS (`allow_methods=["GET"]`): klient to aplikacja natywna; web dev z
  przeglądarki wymagałby dodania `POST`.

## Blokada danych (Etap 0 — fakty, bez zgadywania)

- Granice gmin: GUGiK PRG, strona `geoportal.gov.pl` podaje pliki SHP/GML jednostek
  administracyjnych (`opendata.geoportal.gov.pl/prg/granice/00_jednostki_administracyjne.zip`),
  aktualizacja raz w roku (1 stycznia), licencja wg strony: „bezpłatnie i do dowolnego
  wykorzystania". **Nie ustalono:** formalnej licencji/atrybucji, rozmiaru, układu
  współrzędnych wprost, nazw atrybutów.
- **Pobranie z tego środowiska niemożliwe** (proxy: `CONNECT tunnel failed, response 403`
  dla `opendata.geoportal.gov.pl` i `eteryt.stat.gov.pl`; nie obchodzono). Nic nie
  zostało pobrane ani sprawdzone na próbce; nie wygenerowano żadnych geometrii gmin.
- Testy używają wyłącznie **syntetycznych** kwadratów (kody `99999xx`).

### Co musi dostarczyć człowiek

1. Zatwierdzić licencję PRG (Source Approval Gate, rule #15) i uzupełnić
   `commercial_use`/`attribution` w source-registry.
2. Pobrać `00_jednostki_administracyjne.zip`, wyciągnąć warstwę gmin i zamienić na GeoJSON
   w WGS84 (nazwa pliku warstwy nie została zweryfikowana — sprawdzić `ogrinfo`):
   `ogr2ogr -f GeoJSON -t_srs EPSG:4326 gminy.geojson <warstwa_gmin>.shp`
   (plik trzymać poza repo, np. `data/`; całość wczytywana jest do pamięci — jeśli plik
   jest bardzo duży, następny krok to import strumieniowy, GeoJSONSeq).
3. Sprawdzić: `python -m app.connectors.prg_gminy.ingest --file gminy.geojson --validate-only`
   (flagi `--teryt-field`/`--name-field`, jeśli atrybuty nazywają się inaczej), potem import
   bez `--validate-only`. Oczekiwane: ~2,5 tys. rekordów, 7-cyfrowy kod TERYT jako tekst.
4. Zweryfikować resolver na kilku znanych punktach (np. centrum Kłodzka; oczekiwany kod gminy sprawdzić w TERC/PRG — nie podaję go tu,
   bo nie został zweryfikowany).

## Acceptance Criteria

- [ ] `alembic upgrade head` + `alembic check` przechodzą na `postgis/postgis:16-3.4` (CI).
- [ ] Bez danych: 7 zaseedowanych miast nadal pollowanych, dashboard bez zmian (testy).
- [ ] Punkt w środku, na wspólnej granicy (deterministycznie najniższy TERYT), w dziurze
      (eksklawa vs brak), poza wielokątami = `None`, nie „najbliższa" (`test_postgis_geo.py`).
- [ ] Reimport tego samego pliku jest idempotentny; zaseedowane miasto w wielokącie dostaje
      TERYT zachowując `id`; nowe gminy mają `weather_polling_active = false`.
- [ ] Coroczny pełny snapshot: `--retire-missing` zeruje `boundary` gmin nieobecnych w pliku
      (wiersze nie są usuwane; tylko gdy brak odrzuconych rekordów; seedy bez TERYT nietknięte),
      więc resolver nie zwróci przestarzałej gminy (Codex, runda 1).
- [ ] Reimport odświeża nazwę; seed z kodem nieobecnym w nowym snapshocie (przenumerowana
      gmina) adoptuje nowy kod, zachowując `id`/polling (Codex, runda 2).
- [ ] `--retire-missing` ma bezpieczniki: odmowa (przed importem), gdy plik ma < 2000
      rekordów albo wycofałby > 3% gmin z granicą; `--force-retire` świadomie je omija;
      `--dry-run` tylko raportuje liczbę gmin do wycofania. Kody odrzuconych rekordów liczą
      się jako obecne w pliku (nie powodują re-adopcji seedów).
- [ ] CLI `open_meteo.ingest` i scheduler używają tej samej `polling_areas()`: bez `--slug`
      tylko `weather_polling_active`; jawny `--slug` działa dla dowolnego obszaru.
- [ ] Downgrade 0011 kasuje wiersze `teryt-*` niereferencjonowane przez żadną tabelę (FK z
      katalogu), a przy referencjach przerywa głośnym błędem — po ponownym upgrade nie
      wracają jako pollowane.
- [ ] Błąd bazy w `/geo/resolve` = 503 ze stałym komunikatem, bez współrzędnych w logu
      (`hide_parameters=True` w engine); 422 nie odsyła `input` ze współrzędnymi.
- [ ] CI: `REQUIRE_POSTGIS=1` (zestaw `postgis` failuje zamiast skipować), `set -o pipefail`
      przy `| tee` (wcześniej porażki alembic check/mypy/pytest mogły być maskowane).
- [ ] Update importowanej gminy (`teryt-*`) przelicza jej punkt reprezentatywny z nowej granicy;
      seedy zachowują własne współrzędne. Seed nigdy nie przejmuje kodu zajętego przez inny
      wiersz; drugi seed w tej samej gminie też nie — oba przypadki raportowane
      (`seed_conflicts`), bez wyjątku UNIQUE (Codex, runda 4).
- [ ] Import nie zmienia nazwy ani współrzędnych zaseedowanych miast; rekord, którego
      naprawa `ST_MakeValid` zmienia pole o > 1%, jest odrzucany. Sprzeczne flagi CLI
      (`--force-retire`/`--dry-run` bez `--retire-missing`, `--validate-only` z nim) = błąd
      argumentów (kod 2).
- [ ] Nieprawidłowy rekord (zły TERYT, nie-WGS84, niezamknięty pierścień, duplikat) jest
      odrzucany z powodem, reszta importowana; nieprawidłowa geometria naprawiana
      (`ST_MakeValid`) i policzona w raporcie.
- [ ] `/geo/resolve`: typowany `response_model`, 422 dla złych współrzędnych, brak
      współrzędnych w logach i w odpowiedzi, GET = 405.

## Tests

`tests/test_postgis_geo.py` (marker `postgis`, prawdziwy PostGIS, SKIP gdy niedostępny),
`tests/test_geo_resolve_api.py`, `tests/connectors/test_prg_gminy_parser.py`,
`tests/test_scheduler.py::test_skips_areas_without_active_weather_polling`.
**Uwaga:** autor nie mógł uruchomić pytest/alembic lokalnie (PyPI/Docker niedostępne) —
weryfikacją jest CI.

## Dependencies

ADR-002, ADR-005, ADR-006, TASK-3.1 (provenance), TASK-6.1 (scheduler). Brak nowych
zależności Pythona.

## Data Contract

`POST /api/v1/geo/resolve`, body `{"latitude": float[-90,90], "longitude": float[-180,180]}`
→ `{"area": {"geo_area_id", "teryt_code", "slug", "name"} | null}`. `null` = żadna
zaimportowana gmina nie pokrywa punktu (poza Polską lub brak importu).
`geo_areas`: `teryt_code` (7 znaków, UNIQUE, NULL dla niezlinkowanego seeda),
`boundary` (MultiPolygon EPSG:4326, NULL do importu), `weather_polling_active`.

## Security / Privacy

Współrzędne tylko w body POST, bez logowania, zapisu i echa (ADR-002). Importer czyta
lokalny plik podany przez operatora, bez sekretów i bez sieci. Migracja wymaga roli z
prawem `CREATE EXTENSION`.

## Architecture Impact

ADR-019 (PostGIS jako Geo Engine; doprecyzowuje ADR-005/ADR-006: nearest-distance zostaje
dla stacji, point-in-polygon dla przynależności administracyjnej). Migracja 0011 (po 0010_devices).
