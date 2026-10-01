# ADR-029: Rejestr miejscowości (`places`) niezależny od PRG, aktywacja obszaru z budżetem i TTL, jawny `coverage`

**Status:** Proposed (do zaakceptowania wraz z merge PR „any-locality")
**Data:** 2026-10-01

## Context

Decyzja właściciela (nie do dyskusji): użytkownik ma móc wybrać **dowolną miejscowość w
Polsce** — nie 7 miast i nie tylko gminy z PRG — i zobaczyć, co dzieje się w okolicy. Dane
czytamy dokładnie tam, gdzie się da; gdzie nie — UI/API uczciwie mówi „stan dla obszaru w
promieniu ~50 km / ~100 km” (z nazwą najbliższej stacji i odległością).

Stan przed decyzją: wybór lokalizacji w API (ADR-026) opiera się na `geo_areas`: 7 miast +
(po imporcie granic PRG, który jest zablokowany licencją/plikiem od człowieka, ADR-019)
gminy bez pollingu. Brak rejestru nazw miejscowości z współrzędnymi, brak mechanizmu
aktywacji pollingu dla wybranego miejsca (BACKLOG TASK-12.2 go wymaga, nie definiuje),
stacja GIOŚ jest przypisywana tylko w ≤ 50 km (ADR-006/025), więc większość wsi nie ma
„powietrza”, a dashboard nie mówi, jak daleko jest stacja.

## Problem

1. Skąd wziąć wiarygodne, darmowe nazwy + współrzędne wszystkich miejscowości PL, bez
   zależności od PRG i bez geokodera wołanego z mobile (reguły #2, #14, #17)?
2. Jak pozwolić „dowolnej miejscowości” mieć dane pogodowe bez przepalenia budżetu
   Open-Meteo (10 000 jedn./dobę, ADR-003/022) i bez kont (reguła #11)?
3. Jak pokazać powietrze z odległej stacji tak, by nie udawało pomiaru „u mnie” i nie
   wpływało na werdykt „Na dwór” jako pewne (reguły #8, #10)?

## Options (źródło miejscowości)

**A. GeoNames, zrzut `PL` (`PL.zip`/`PL.txt`).** TSV w WGS84, rząd dziesiątek tysięcy miejscowości (liczba niezweryfikowana)
(PPL*), z populacją (przydatna do sortowania), kodami admin. Licencja: strona GeoNames
(`geonames.org/about.html`, `/export`, odczytane 2026-10-01 przez WebFetch): „This work is licensed
under a Creative Commons Attribution 4.0 License”, darmowy download, użycie komercyjne dozwolone
z podaniem źródła („give credit to GeoNames … with a link or another reference”), dane „as is”
bez gwarancji dokładności/aktualności/kompletności. Wada: dane społecznościowe, nazwy
jednostek admin tylko jako kody (nie TERYT).

**B. TERYT SIMC + PRNG (GUGiK).** Urzędowe. PRNG (`geoportal.gov.pl`, odczytane 2026-10-01):
„free of charge and can be used for any purpose”, formaty GML/SHP/XLSX, układ **EPSG:2180**,
aktualizowany na bieżąco. SIMC (GUS) bez współrzędnych, wymaga rejestracji (registry: `teryt`,
licencja niezweryfikowana). Wady: brak populacji (gorsze sortowanie), brak CSV/GeoJSON, trzeba
repr. EPSG:2180→4326 i parsować GML/SHP bez dostępnej tu zależności, dwa źródła do złączenia,
formalna licencja PRNG poza stroną nieznana (podobnie jak PRG — gate #15 otwarty).

**C. OpenStreetMap `place=*`.** ODbL (share-alike dla baz pochodnych, atrybucja), wymaga
ekstraktu (Overpass/Geofabrik) i czyszczenia; nic z tego nie weryfikowano w tej sesji
(egress zablokowany). Zbyt duży koszt i obowiązki licencyjne jak na MVP.

## Odrzucone (decyzja właściciela, 2026-10-01)

- **Google Places / Geocoding:** płatne, ToS zabrania cache'owania współrzędnych, łamie FREE-FIRST (#17)
  i „API czyta tylko z naszej bazy” (#14).
- **Open-Meteo Geocoding API wołane na żądanie** (wyszukiwanie nazw): wołanie zewnętrznego API z
  żądania użytkownika łamie #14 (i zużywa ten sam darmowy limit co pogoda).
- **Geokoder urządzenia** (systemowy w telefonie): dopuszczalny wyłącznie opcjonalnie do „Użyj mojej
  lokalizacji” (współrzędne → `POST /geo/locate`), nie jako źródło wyszukiwania miejscowości.

## Decision

### 1. Źródło: GeoNames PL (opcja A) — `geonames_pl`

Najmniej pracy i ryzyka techniczne: gotowy plik TSV w WGS84 z populacją, jedno źródło,
licencja CC BY 4.0 zweryfikowana na stronie źródła (komercyjnie OK z atrybucją). Rejestr
`docs/data/source-registry.md`: status **proposed (DISCOVERY)** do czasu przejścia Source Approval
Gate (reguła #15). **Układ pliku zweryfikowany na prawdziwym zrzucie** (workflow
`geonames-verify`, 2026-10-01, runner GitHub): 58 564 wiersze, wszystkie po 19 kolumn; parser →
45 415 prawidłowych miejscowości, 0 odrzuconych, 13 149 pominiętych (inne klasy/kody); „Gliwice”
= `PPLA3`, populacja 198 835, admin1 `83`, admin2 `2466`. (Lokalny sandbox ma zablokowany egress do
GeoNames — dlatego weryfikacja idzie przez Actions.) Parser dalej waliduje ściśle. PRNG zostaje zapisany jako **ścieżka ulepszenia** (urzędowe nazwy, EPSG:2180), nie wybór.

- Import, dwa tryby (operator-run, na produkcyjnym VPS, gdzie jest egress; nigdy na żądanie
  użytkownika):
  `docker compose exec api python -m app.connectors.geonames_places.ingest --download`
  pobiera `PL.zip`, `admin1CodesASCII.txt`, `admin2Codes.txt` do katalogu tymczasowego (URL bazowy z
  env `GEONAMES_BASE_URL`, domyślnie `https://download.geonames.org/export/dump/`; timeout 120 s,
  max 3 próby z rosnącą pauzą, 4xx poza 429 bez ponowień — reguła #5) i importuje; albo **lokalny
  plik** (`--file`/`GEONAMES_PL_FILE`, `.txt`/`.zip`, opcjonalnie `--admin1-file`/`--admin2-file`),
  `--validate-only` nie dotyka bazy, `--sample "Gliwice"` drukuje rekordy. Import jest
  idempotentny — można go powtarzać (np. raz na kwartał). Żadnych zapytań do GeoNames z API ani z
  mobile (#14); mobile nie woła zewnętrznego geokodera. Struktura `connectors/geonames_places/`
  (`parser.py`: parse/validate/normalize, `ingest.py`: store; bez `client.py` — jak `prg_gminy`,
  plik daje operator). Idempotentny upsert po `geonameid`; nie usuwa miejsc brakujących w nowszym
  pliku (mogą być przywołane przez `geo_areas`).
- Importowane klasy: `P` z kodami `PPL, PPLA, PPLA2, PPLA3, PPLA4, PPLC, PPLL`; pominięte
  historyczne/zniszczone/opuszczone (`PPLH/W/Q`) i części miast (`PPLX`, szum duplikatów).
- Atrybucja (CC BY 4.0) jest w odpowiedziach API (`attribution`) i w registry — ekran „Źródła”
  w mobile (TASK-12.6) ma ją pokazać.

### 2. Model: `places` + indeks prefiksowy bez rozszerzeń

Migracja `0014`: `places(id, name, normalized_name, kind, admin1_code, admin2_code,
latitude, longitude, population, source, source_record_id, imported_at)`, unikat
`(source, source_record_id)`; `geo_areas.place_id` (FK, unikat) i `geo_areas.last_requested_at`.
`kind` = kod cechy GeoNames; kody admin są **surowymi kodami GeoNames, nie TERYT**. Nazwy
(`admin1_name`, `admin2_name`) pochodzą z `admin1CodesASCII.txt`/`admin2Codes.txt` (układ
zweryfikowany na prawdziwych plikach): województwa są po angielsku („Silesia”), powiaty po polsku
(„Powiat będziński”; miasta na prawach powiatu = nazwa miasta). API składa z nich czytelny `label`
(„Nowa Wieś, pow. gliwicki, woj. śląskie”): `place_label` mapuje 16 angielskich nazw województw na
polskie przymiotniki (stała `VOIVODESHIP_PL`), powiat o nazwie miejscowości nie jest powtarzany,
nieznana nazwa jest pokazywana tak, jak ją ma GeoNames.

Wyszukiwanie: **deterministyczna kolumna `normalized_name`** (`app/places.py::normalize_name`:
casefold, NFKD bez znaków łączących, `ł→l`, wszystko poza `[a-z0-9]` → spacja) +
btree z `varchar_pattern_ops` pod `LIKE 'prefiks%'`. **Nie** używamy `pg_trgm`/`unaccent`:
obraz `postgis/postgis:16-3.4` jest oparty na obrazie `postgres`, który zawiera moduły contrib, ale
tego nie zweryfikowano w tej sesji (brak Dockera), a kolumna nie wymaga niczego i działa też w
testach na SQLite. Ograniczenie: dopasowanie tylko od początku nazwy (nie „Biała” w „Bielsko-Biała”).
Brak PostGIS-owej kolumny `geom` w `places` — nie ma zapytań przestrzennych po miejscowościach
(YAGNI); najbliższa stacja liczona haversine'em (ADR-006).

### 3. API (tylko z naszej bazy, #14)

- `GET /api/v1/places?q=&limit=` — `q` 2–100 znaków, `limit` 1–20 (domyślnie 10); sortowanie:
  dokładne dopasowanie znormalizowane, potem populacja malejąco (brak = 0), potem nazwa i id (remisy
  deterministyczne). Zapytanie normalizujące się do < 2 znaków → pusta lista. 422 **bez**
  `input`/`ctx` (rozszerzenie handlera: ścieżki `/api/v1/places*`), aplikacja nie loguje `q`
  (middleware loguje tylko ścieżkę). `Cache-Control: public, max-age=300`.
- `GET /api/v1/places/{place_id}` — miejscowość + stan jej obszaru; **nie tworzy ani nie odświeża**
  obszaru (id jest publiczne i wyliczalne — odczyt nie może podtrzymywać pollingu, ADR-026).
- `POST /api/v1/places/{place_id}/activate` — tworzy `geo_area` (`slug=place-<id>`, nazwa i
  współrzędne z `places`) przy pierwszym użyciu, odświeża `last_requested_at` i włącza polling,
  jeśli pozwalają limity (pkt 4). Idempotentny. Odpowiedź: `place`, `area` (jak w ADR-026),
  `polling` ∈ `active | inactive | capacity_reached | budget_exhausted`. Identyfikator obszaru
  to zasób publiczny; żadnych danych użytkownika, kont ani lokalizacji w tle (#11).

### 4. Polityka aktywacji i budżetu (zachowanie po przekroczeniu)

- **Limit aktywnych obszarów** `max_active_areas() = floor(0,7 · OPEN_METEO_DAILY_CALL_LIMIT / (8 ·
  ESTIMATED_BILLABLE_UNITS_PER_CALL + 1))`: 8 odpytań pogody/dobę (cykl 3 h, ADR-004) po
  `ESTIMATED_BILLABLE_UNITS_PER_CALL` jednostek (dziś 2: 19 zmiennych → 2) + 1 odpytanie pyłków/dobę
  (ADR-020), do 70% limitu (próg alertu ADR-003). Dziś: floor(7000/17) = **411** (wliczone
  zaseedowane miasta). Limit rośnie sam po podniesieniu `OPEN_METEO_DAILY_CALL_LIMIT` (plan
  komercyjny, ADR-022). Stałe 8/1 przypięte testem do interwałów schedulera.
- **Budżet chwilowy:** nowa aktywacja jest odmawiana, gdy dzisiejszy licznik `open_meteo` ≥ 90%
  limitu (`BUDGET_REFUSE_PCT`).
- **Po przekroczeniu = degradacja, nie błąd (#1):** obszar nadal powstaje (nieaktywny),
  odpowiedź ma `polling=capacity_reached|budget_exhausted`, a `GET /dashboard/latest?geo_area_id=`
  zwraca go z `weather_polling_active=false` i `weather/forecast=null`, `pollen=UNAVAILABLE`
  (ADR-026); powietrze z katalogu GIOŚ działa niezależnie. Brak wywłaszczania cudzych obszarów.
- **Wygaszanie (TTL):** `PLACE_ACTIVATION_TTL_DAYS` (domyślnie 7). Codzienny job schedulera
  (`place_expiry`) wyłącza polling obszarów z `place_id`, których `last_requested_at` starsze niż
  TTL (dokładnie TTL = zostaje). Obszary zaseedowane/gminy (`place_id IS NULL`) nie wygasają tą
  ścieżką. Wiersz i historia zostają — dashboard pokaże dane jako STALE, nie „zniknęło”. Jedyny
  sygnał to `activate` (klient wywołuje go przy wyborze miejsca i przy otwarciu aplikacji z
  wybranym miejscem); odczyty dashboardu się nie liczą (ADR-026).
- **Pierwszy fetch:** scheduler co tick (60 s) wykrywa aktywne obszary z `place_id` bez żadnej
  pogody i pobiera pogodę + pyłki od razu — max 3 próby co 15 min na obszar (pamięć procesu,
  ADR-007), potem normalny cykl. Każda próba idzie przez ten sam licznik budżetu (#16: to nie
  „stała na wszelki wypadek”, tylko jednorazowy start nowego obszaru). API nie woła źródła (#14).
- **Nadużycie:** `activate` przełączający polling z wyłączonego na włączony jest limitowany per IP
  (10/h, in-memory jak ADR-017); odświeżenie już aktywnego obszaru nie jest limitowane. To
  ograniczenie, nie zabezpieczenie — wyliczalne `place_id` + botnet mogą zająć limit 411 na TTL.
  Mocniejszy sygnał (heartbeat instalacji, limit obszarów na instalację) to zakres TASK-12.2.

### 5. `coverage` powietrza i siatka modelu (reguła #9)

Stałe w `app/geo.py`; odległość = centrum obszaru ↔ stacja, **zaokrąglona do 1 m** (liczba
widoczna dla klienta), górne granice włącznie:

| `coverage` | odległość | znaczenie |
|---|---|---|
| `exact` | ≤ 10 km | stacja „w mieście/tuż obok” (`EXACT_MAX_KM`, **decyzja produktowa**, nie pomiar) |
| `nearby` | ≤ 50 km | jak dotąd (ADR-006/025, `NEARBY_MAX_KM = MAX_MATCH_DISTANCE_KM`) |
| `regional` | ≤ 100 km | NOWE; odległa stacja, jawnie oznaczona (`REGIONAL_MAX_KM`) |
| `none` | > 100 km / brak | brak stacji → powietrze UNAVAILABLE, nigdy „dobre” |

`DashboardAir` dostaje `coverage` i `coverage_radius_km` (10/50/100; klient może napisać „stan dla
obszaru w promieniu ~50/~100 km”, z istniejącymi `station_name` i `distance_km`). `DashboardArea`
dostaje `coverage` = `{air, air_radius_km, weather:"grid", pollen:"grid", grid_description}` — przy
`none` blok `air` jest `null`, a `coverage.air == "none"` odróżnia to od „brak danych wciąż się
ładuje”. Pogoda i pyłki to **wartości modelu na siatce** (Open-Meteo, CAMS), nie pomiar w
miejscowości; opis po polsku w `grid_description`. `/air/latest?geo_area_id=` zwraca te same
pola (`coverage`, `coverage_radius_km`, opcjonalne jak reszta pól ADR-025).

Polling GIOŚ (`assigned_station_ids`) przypisuje teraz najbliższą stację w ≤ 100 km (było 50), żeby
pasmo `regional` miało dane; liczba odpytywanych stacji nadal ≤ liczba aktywnych obszarów.
Granica 50 km z ADR-025 pozostaje jako próg `nearby`/`regional`; reszta ADR-025 bez zmian.

**Werdykt „Na dwór” (ADR-016):** dane `regional` **nie wchodzą do silnika** (jak brak
stacji): grupa `air` jest rdzeniowa, więc silnik nie zwróci `GOOD` bez niej (→ `UNKNOWN`), a gdy
sama pogoda daje `MODERATE/POOR`, werdykt pozostaje taki. Powód: pomiar z 50–100 km nie opisuje
powietrza „tu” (inna dolina, smog niskiej emisji), więc nie wolno z niego wywieść pewnego
„wszystko dobrze”. Koszt: wieś 50–100 km od stacji nie dostanie werdyktu `GOOD` — świadomie;
karta powietrza z oznaczeniem `regional` i `distance_km` pokazuje dane obok. Alternatywa
(wpuszczać `regional` tylko „na gorsze”) odrzucona jako dodatkowa logika w silniku bez
kalibracji. `exact` i `nearby` — bez zmian (wchodzą do werdyktu).

## Consequences

- **Dane:** repo nie zawiera `PL.zip`; do uruchomienia wyszukiwania operator musi pobrać plik
  (registry: gate #15) i uruchomić import. Bez danych `GET /places` zwraca `[]`.
- **UI poza zakresem PR:** ekran wyboru (wyszukiwarka → `POST .../activate` → dashboard po
  `geo_area_id`) to TASK-12.2/12.3 po decyzji o designie. Klient musi: wołać `activate` przy
  wyborze **i** przy otwarciu aplikacji, pokazywać `coverage`/odległość oraz atrybucję GeoNames.
- **Duplikaty nazw:** „Nowa Wieś” występuje setki razy; `label` (powiat + województwo) rozróżnia
  większość, ale dwie wsie o tej samej nazwie w jednym powiecie nadal wyglądają tak samo (UI może
  pokazać dystans od użytkownika albo współrzędne).
- **Alerty:** obszar z `place_id` nie ma `teryt_code`, więc `local_alerts` daje wynik
  `unresolved` (fail-safe ADR-013), nie „brak alertów”; dopasowanie miejscowości do gminy
  (`resolve_gmina`) wymaga granic PRG — osobny krok po odblokowaniu PRG.
- **Obciążenie GIOŚ:** do ~411 obszarów × stacje (ADR-025: throttle 30 s/stację) wydłuża run
  GIOŚ; lista sensorów nadal bez cache (zapisane w ADR-025).
- **Niezweryfikowane:** brak lokalnego uruchomienia testów/`alembic check` (PyPI niedostępne) — pierwszy dowód to CI;
  `openapi.json` zaktualizowany ręcznie wg konwencji FastAPI (weryfikuje krok CI `--check`).
- **Limit aktywnych nie jest atomowy** (równoległe aktywacje mogą przekroczyć o kilka); poprawka
  = blokada wiersza, gdyby miało to znaczenie. Retry w kliencie HTTP mnoży zużycie jednostek
  ponad szacunek 8/dobę (znane z ADR-003/022; próg 90% to bufor).
- Zastępuje częściowo: ADR-025 (limit 50 km → pasma do 100 km), uzupełnia ADR-026 (mechanizm
  aktywacji, którego ADR-026 nie definiował; `POST /geo/locate` bez zmian).
