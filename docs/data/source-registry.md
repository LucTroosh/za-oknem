# Source Registry (starter)

Format wg §37 Master Planu. Status: DISCOVERY → VERIFIED → APPROVED → IMPLEMENTED →
PRODUCTION, alternatywnie BLOCKED. Uzupełniać przy każdym nowym connectorze
(Source Approval Gate, §38) — nie zaczynać implementacji connectora bez wpisu tutaj.

## open_meteo

- **owner:** OpenMeteo GmbH (Szwajcaria)
- **connector:** `open_meteo`
- **endpoint:** api.open-meteo.com (forecast + air-quality)
- **frequency:** ZWERYFIKOWANE wg dokumentacji Open-Meteo (open-meteo.com/en/docs,
  sekcja "Update frequency" per model): ICON (DWD, domyślny model dla Europy/Polski)
  odświeża się co 3h; GFS/HRRR (NOAA) co godzinę; ECMWF co 6h. Ponieważ domyślnie
  używamy modelu europejskiego (ICON), zgodnie z ADR-004 fetch **co 3h**, nie co
  godzinę "na wszelki wypadek". Uwaga: dokładny kształt odpowiedzi JSON (pola pod
  `current`/`current_units`) potwierdzony z oficjalnej dokumentacji tekstowej, ale
  **nie zweryfikowany na żywym przykładzie w tej sesji** (endpoint API blokowany przez
  robots.txt dla narzędzi fetch w tym środowisku) — connector waliduje kształt i
  rzuca czytelny błąd zamiast zgadywać, pierwsza żywa weryfikacja to najbliższy
  realny `docker compose exec api python -m app.connectors.open_meteo.ingest`.
- **coverage:** globalne, w tym Polska
- **license:** CC BY 4.0 (atrybucja wymagana)
- **commercial_use:** NIE na darmowym tierze — patrz ADR-003. Rewizja wymagana przed
  jakąkolwiek monetyzacją.
- **redistribution:** dozwolona pod CC BY 4.0 z atrybucją
- **caching:** wymagany snapshot w bazie (ADR-001), zero zapytań on-demand per użytkownik
- **rate_limit:** 600/min, 5000/h, 10000/dzień, 300000/miesiąc (darmowy tier)
- **attribution:** "Weather data by Open-Meteo.com (CC BY 4.0)" — wymagane w ekranie Źródła
- **status:** IMPLEMENTED (connector `open_meteo` — client/parser/ingest — oraz
  `GET /api/v1/weather/latest` gotowe 2026-09-28; pierwsza żywa weryfikacja
  kształtu JSON nastąpi przy pierwszym realnym uruchomieniu ingestu, patrz
  uwaga o robots.txt wyżej — connector waliduje i rzuca błąd zamiast zgadywać)
- **forecast (`daily`):** dodane 2026-09-29 (TASK-5.3, ADR-010) — jedno
  zapytanie HTTP dołącza `daily=...` obok `current=...` (Open-Meteo pozwala
  łączyć oba w jednym wywołaniu). Kształt (`daily`/`daily_units`, równoległe
  tablice `time`+per-param) potwierdzony z oficjalnej dokumentacji tekstowej
  (ten sam robots.txt blocker co `current`, ten sam przyjęty precedens —
  weather nie jest danymi bezpieczeństwa). Open-Meteo nie publikuje własnego
  znacznika czasu "run modelu" — `forecast_reference_time` to nasz `fetched_at`
  zaokrąglony do 3h cyklu (ADR-010), jawnie udokumentowane przybliżenie.
  `model="auto"` to dokładna, udokumentowana wartość domyślna Open-Meteo, nie
  wymyślona etykieta.
- **last_verified_at:** 2026-09-28 (current), 2026-09-29 (dokumentacja daily)

## open_meteo_pollen (CAMS Europe pyłki przez Open-Meteo Air Quality API)

Decyzja i pełna lista tego, co zweryfikowane/niezweryfikowane: ADR-020.

- **owner:** OpenMeteo GmbH (relay) / ECMWF-Copernicus CAMS (model)
- **connector:** `open_meteo_pollen` (`app/connectors/open_meteo_pollen/`)
- **endpoint:** `https://air-quality-api.open-meteo.com/v1/air-quality`,
  `hourly=alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,ragweed_pollen`,
  `domains=cams_europe`, `forecast_days=4`, `timezone=UTC` — bez klucza
- **species:** dokładnie 5 gatunków MVP (Master Plan §6): olcha=alder, brzoza=birch,
  trawy=grass, bylica=mugwort, ambrozja=ragweed; jednostka grains/m³. Open-Meteo
  oferuje też `olive_pollen` — poza MVP, nie pobieramy.
- **frequency:** ZWERYFIKOWANE wg dokumentacji — Open-Meteo: „Every 24 hours, 4 days
  forecast”; ADS (CAMS Europe air quality forecasts): raz dziennie, dostępne 06:45 UTC
  (lead 0–48 h) i 08:30 UTC (lead 49–96 h). Fetch **raz na dobę** (ADR-004, rule #16).
- **coverage:** tylko Europa („Only available in Europe during pollen season”), siatka
  0,1° (~11 km), godzinowo; poza sezonem pyłkowym wartości mogą być puste (null vs 0:
  NIEZWERYFIKOWANE — parser zachowuje oba wiernie)
- **nature:** PROGNOZA MODELOWA, nie pomiar (rule #7). ADS: prognozy zmiennych poza
  NO/NO₂/SO₂/O₃/PM2.5/PM10/pyłem „are unvalidated and should be considered experimental”
- **license:** Open-Meteo: CC BY 4.0; dane CAMS: CC-BY (strona datasetu ADS). Wcześniejszy
  wpis `cams_ads` mówił „bez ograniczeń użycia” — strona datasetu podaje CC-BY, więc
  atrybucja jest obowiązkowa
- **commercial_use:** NIE na darmowym tierze Open-Meteo — ta sama zasada co ADR-003
  (subskrypcja/reklamy = komercyjne; Patronite nieopisane). Rewizja wymagana przed
  jakąkolwiek monetyzacją; alternatywa: płatny plan Open-Meteo albo CAMS ADS
  bezpośrednio (klucz — blokada człowieka)
- **redistribution:** dozwolona pod CC BY 4.0 z atrybucją
- **caching:** snapshot w bazie (ADR-001, `pollen_snapshots`), zero zapytań on-demand
- **rate_limit:** 600/min, 5000/h, 10000/dzień, 300000/mies. (darmowy tier; pricing page
  wymienia Air Quality API w tym samym tierze). Koszt wywołania: zakładane 1 jednostka
  (5 zmiennych, 4 dni) wg reguły „>10 zmiennych / >14 dni = więcej wywołań” — czy reguła
  dotyczy Air Quality API: NIEZWERYFIKOWANE. Liczone we wspólnym liczniku `open_meteo`
- **attribution:** "Pollen forecast: Copernicus Atmosphere Monitoring Service (CAMS) European air quality forecast, via Open-Meteo.com (CC BY 4.0). Contains modified Copernicus Atmosphere Monitoring Service information." — wymagane w ekranie Źródła i na karcie pyłkowej (Open-Meteo wymaga też linku do open-meteo.com przy wyświetlanych danych)
- **status:** IMPLEMENTED (backend: connector + `pollen_snapshots` + scheduler +
  `GET /api/v1/pollen/latest`, 2026-10-01). Kształt odpowiedzi JSON NIEZWERYFIKOWANY NA
  ŻYWO (egress zablokowany) — parser używa tylko pól z dokumentacji i odrzuca resztę;
  pierwsza żywa weryfikacja przy pierwszym realnym ingeście
- **last_verified_at:** 2026-10-01 (dokumentacja; bez żywego przykładu)

## cams_ads (Copernicus Atmosphere Data Store — pyłki, CAMS Air)

> Od ADR-020 pyłki MVP idą przez `open_meteo_pollen` (bez klucza). Ten wpis zostaje jako
> alternatywa (źródło pierwotne, licencja bez rozróżnienia komercyjne/niekomercyjne) —
> wymaga klucza od człowieka (TASK-8.5 pierwotnie).

- **owner:** ECMWF / Copernicus (Unia Europejska)
- **connector:** `cams` (do zaprojektowania — inny kształt niż API pogodowe: pobranie
  pliku NetCDF/GRIB dla wycinka Polski, nie zapytanie per-punkt)
- **endpoint:** ads.atmosphere.copernicus.eu (wymaga rejestracji, klucz API)
- **frequency:** raz dziennie (prognoza pyłków aktualizowana raz/dzień, 4 dni naprzód) —
  zgodne z ADR-004, fetch nie częściej niż ten cykl
- **coverage:** Europa, w tym Polska (tylko powierzchnia, brak pionowego profilu)
- **license:** dane opisane przez Copernicus jako dostępne bez ograniczeń użycia,
  wymagana widoczna atrybucja programu Copernicus (Licence to Use Copernicus Products)
- **commercial_use:** TAK (bez ograniczeń wg dokumentacji Copernicus) — do potwierdzenia
  przy pełnym Source Approval Gate przed Phase 8
- **redistribution:** wymaga atrybucji Copernicus przy każdej publikacji danych
- **caching:** snapshot dzienny w bazie, tak jak weather (ADR-001)
- **rate_limit:** nieznany dokładnie — UNKNOWN, sprawdzić przy implementacji (Phase 8)
- **attribution:** "Contains modified Copernicus Atmosphere Monitoring Service
  information" — wymagane
- **status:** DISCOVERY (licencja wstępnie sprawdzona, techniczny kształt API nie
  zweryfikowany)
- **last_verified_at:** 2026-09-28

## gios (GIOŚ — jakość powietrza, stacje pomiarowe)

- **owner:** Główny Inspektorat Ochrony Środowiska (Polska, instytucja publiczna)
- **connector:** `gios`
- **endpoint:** `https://api.gios.gov.pl/pjp-api/v1/rest/` — `/station/findAll`,
  `/station/sensors/{stationId}`, `/data/getData/{sensorId}`, `/aqindex/getIndex/{stationId}`.
  Starsze endpointy bez `/v1/` wycofane 30.06.2025 — potwierdzone w dokumentacji GIOŚ
  (nie zgadywane).
- **frequency:** ZWERYFIKOWANE na żywo 2026-09-28: lista stacji (`/station/findAll`)
  deklaruje `sy:updatePeriod: year` we własnym `meta` — aktualizuje się raz na rok, więc
  cache'ować długo (dni/tygodnie), nigdy odpytywać przy każdym ingest. Dane pomiarowe
  (`/data/getData/{sensorId}`) są godzinowe (kod stanowiska kończy się na `-1g` = "1
  godzina", potwierdzone na żywym przykładzie). Zgodnie z ADR-004: scheduler docelowo
  co godzinę dla danych, raz na dzień/tydzień dla listy stacji — do ostatecznego
  ustalenia w Phase 5.
- **coverage:** Polska (sieć stacji GIOŚ, liczba i lokalizacje zmienne)
- **license:** dane publiczne sektora publicznego — wymagane "jasne i wyraźne wskazanie
  źródła" przy republikacji (cytat z dokumentacji GIOŚ)
- **commercial_use:** brak jawnego zakazu w znalezionej dokumentacji — do potwierdzenia
  przy pełnym Source Approval Gate przed produkcją
- **redistribution:** dozwolona z atrybucją źródła
- **caching:** zgodnie z regułą #14 (CLAUDE.md) — mobile API czyta wyłącznie z naszej
  bazy, nigdy nie woła GIOŚ na żądanie użytkownika
- **rate_limit:** 2 zapytania/min (endpointy standardowe, np. listy stacji),
  1500 zapytań/min (dane bieżące i indeks jakości powietrza) — wg dokumentacji GIOŚ
- **attribution:** "Dane: Główny Inspektorat Ochrony Środowiska (GIOŚ)" — wymagane w
  ekranie Źródła
- **status:** IMPLEMENTED (connector `gios` — client/parser/ingest — oraz
  `GET /api/v1/air/latest` gotowe; VERIFIED na żywo 2026-09-28, użytkownik uruchomił
  connector przeciwko prawdziwemu API). **Realny kształt odpowiedzi różni się istotnie od pierwotnie
  zakładanego, udokumentowanego schematu** — API zwraca JSON-LD z polskimi kluczami
  (`Lista stacji pomiarowych`, `Identyfikator stacji`, `Nazwa stacji`, `WGS84 φ N`,
  `WGS84 λ E`, `Wskaźnik - wzór`, `Lista danych pomiarowych`, `Data`, `Wartość` itd.),
  nie angielskim camelCase jak sugerowała dokumentacja. Listy (`/station/findAll`,
  `/station/sensors`) są **paginowane** (`totalPages`, `links.next/prev/first/last`) —
  domyślnie 20 pozycji/strona. Connector przepisany pod realny kształt (`client.py`,
  `parser.py`) po tej weryfikacji; `find_stations()` w kliencie celowo unika
  przechodzenia całej (rate-limited) listy stron przy szukaniu znanego ID stacji.
- **last_verified_at:** 2026-09-28

## eea_eaqi (Europejski Indeks Jakości Powietrza — METODOLOGIA, nie feed)

- **owner:** European Environment Agency (EEA); pasma: ETC HE Report 2024/17, v1,
  3.07.2025, DOI 10.5281/zenodo.15781195
- **connector:** BRAK — to nie jest źródło danych ani połączenie w runtime. Wagę ma tylko
  opublikowana tabela progów, którą implementuje `apps/api/app/air_index.py` (ADR-015);
  dane wejściowe to pomiary `gios`. Dlatego Source Approval Gate (§38/rule #15) dla
  connectora nie ma tu zastosowania; wymagane jest to, co gate sprawdza dla treści:
  licencja i atrybucja (niżej) oraz weryfikacja progów z URL i datą.
- **endpoint:** brak wywołań; źródła treści: <https://airindex.eea.europa.eu/AQI/index.html>
  i PDF raportu ETC HE 2024/17 (eionet.europa.eu)
- **frequency:** n/d. Indeks godzinowy (1 h) — liczony przy odczycie z ostatnich
  pomiarów GIOŚ; świeżość = świeżość wejść (rule #8)
- **coverage:** nasze liczenie dla stacji GIOŚ; metodologia europejska
- **license:** CC-BY 4.0 (<https://www.eea.europa.eu/en/legal-notice>, zweryfikowane
  2026-09-30)
- **commercial_use:** TAK (wg tej samej strony: „commercial or non-commercial purposes”)
- **redistribution:** dozwolona z wskazaniem EEA jako źródła i bez zniekształcania sensu
- **caching:** n/d (brak danych z EEA)
- **rate_limit:** n/d
- **attribution:** „Europejski Indeks Jakości Powietrza (EEA), liczony z pomiarów GIOŚ” —
  wymagane przy wyniku w UI i w ekranie Źródła. To nasze obliczenie wg metodologii EEA,
  nie oficjalny indeks EEA ani GIOŚ.
- **status:** VERIFIED (progi, agregacja, minimalny zestaw; 2026-09-30) — IMPLEMENTED w
  TASK-4.2. NIEzweryfikowane (nasze decyzje w ADR-015): konwencja granic pasm dla wartości
  ułamkowych, typ stacji, polskie nazwy 6 pasm.
- **last_verified_at:** 2026-09-30

## imgw_hydro (stan wody — Measurement)

- **owner:** Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy
  (Polska, instytucja publiczna)
- **connector:** `imgw_hydro`
- **endpoint:** `https://danepubliczne.imgw.pl/api/data/hydro/` — jedno wywołanie
  zwraca WSZYSTKIE stacje (brak paginacji, w przeciwieństwie do GIOŚ), z
  `lat`/`lon` wprost w payloadzie. Zweryfikowane na żywo 2026-09-29 (WebFetch).
- **frequency:** NIEZNANA z dokumentacji (sprawdzone: brak w regulaminie/apiinfo) —
  ADR-008 przyjmuje roboczo 1h (jak GIOŚ, ta sama domena danych rządowych), jawnie
  oznaczone jako założenie startowe, nie zweryfikowany cykl (rule #16).
- **coverage:** Polska (sieć stacji hydrologicznych IMGW)
- **license:** niekomercyjne/prywatne użycie bezpłatne; komercyjne wymaga płatnej
  umowy (poza "danymi wysokiej wartości") — regulamin `danepubliczne.imgw.pl/apiinfo`,
  zweryfikowany na żywo 2026-09-29
- **commercial_use:** NIE na darmowym tierze — analogicznie do ADR-003 (Open-Meteo),
  rewizja wymagana przed jakąkolwiek monetyzacją (patrz ADR-008)
- **redistribution:** dozwolona z wymaganą atrybucją
- **caching:** zgodnie z regułą #14 — mobile API czyta wyłącznie z naszej bazy
- **rate_limit:** brak jawnego limitu w regulaminie (sprawdzone, nie zgadywane)
- **attribution:** "Źródłem pochodzenia danych jest Instytut Meteorologii i
  Gospodarki Wodnej – Państwowy Instytut Badawczy" (+ dopisek o przetworzeniu,
  jeśli dane są modyfikowane) — wymagane w ekranie Źródła
- **status:** IMPLEMENTED (connector `imgw_hydro` — client/parser/ingest — oraz
  `GET /api/v1/hydro/latest` gotowe 2026-09-29; kształt payloadu zweryfikowany
  live, pierwsza faktyczna weryfikacja cyklu odświeżania nastąpi przy pierwszym
  realnym uruchomieniu ingestu)
- **progi ostrzegawcze/alarmowe (`stan_ostrzegawczy`/`stan_alarmowy`):**
  zweryfikowane na żywo 2026-09-29 w tym samym payloadzie co `stan_wody` —
  publikowane wprost przez IMGW per stacja, wartości liczbowe jako string, jak
  `stan_wody`. Mogą być `null` dla stacji bez zdefiniowanego progu (potwierdzone
  na żywo, np. stacje na jeziorach: "Żukowo", "Borucino") — to nie błąd, tylko
  brak progu dla tej stacji. `normalize()` emituje je jako osobne rekordy
  Measurement (`water_level_warn_cm`/`water_level_alarm_cm`) o stabilnej
  tożsamości (stacja+param_code, bez timestampu) — `ingest.py` nadpisuje
  (upsert) lub usuwa (gdy próg wraca jako `null`) JEDEN wiersz per próg przy
  każdym przebiegu, niezależnie od cyklu odczytu `stan_wody` (progi nie mają
  własnego znacznika czasu ze źródła — patrz TASK-9.3, 3 rundy Codex review).
  Status NORMAL/WARNING/ALARM/UNKNOWN liczony deterministycznie przy odczycie
  w `GET /api/v1/hydro/latest` — prosta komparacja liczb opublikowanych przez
  źródło, nie interpretacja LLM (rule #10)
- **last_verified_at:** 2026-09-29

## imgw_warningshydro (ostrzeżenia hydrologiczne — Alert)

- **connector:** `imgw_warningshydro` (client/parser/ingest) — model `Alert`
  (ADR-009), oddzielny od `imgw_hydro`/Measurement (rule #7)
- **endpoint:** `https://danepubliczne.imgw.pl/api/data/warningshydro` —
  zweryfikowane na żywo 2026-09-29 (WebFetch). Kształt: lista obiektów
  ostrzeżeń (`stopień`, `data_od`, `data_do`, `prawdopodobieństwo`, `zdarzenie`,
  `obszary[].wojewodztwo`) lub `{"message": "..."}` przy braku aktywnych
  ostrzeżeń (parsowane defensywnie jako pusta lista — patrz ADR-009; kształt
  pustego stanu potwierdzony na żywo tylko dla `warningsmeteo`, dla
  `warningshydro` obsłużony tym samym kodem "na wszelki wypadek", nie
  zweryfikowany osobno).
- **frequency:** NIEZNANA z dokumentacji — ADR-009 przyjmuje roboczo 1h
  (source-critical, ale bez potwierdzonego realnego cyklu — rule #16 wyjątek
  dla ostrzeżeń, z jawnym uzasadnieniem tutaj)
- **license/rate_limit/attribution:** jak `imgw_hydro` wyżej (ten sam regulamin)
- **status:** IMPLEMENTED — connector, model `Alert`, `GET /api/v1/alerts/latest`
  i scheduler (`run_imgw_warningshydro`, co 1h) gotowe 2026-09-29;
  `severity_raw` przechowywane bez reinterpretacji (rule #10)
- **last_verified_at:** 2026-09-29

## gis_bathing_sk (Serwis Kąpieliskowy GIS — bieżący status kąpielisk, BLOCKED)

- **owner:** Główny Inspektorat Sanitarny (Polska, instytucja publiczna)
- **connector:** brak (nie implementować — patrz ADR-021)
- **endpoint:** `https://sk.gis.gov.pl/kapieliska` (lista HTML, ok. 718
  kąpielisk), `https://sk.gis.gov.pl/index.php/kapielisko/{id}` (strona
  kąpieliska: status wody, E. coli, enterokoki, daty badań, sezon) — sprawdzone
  WebFetch 2026-10-01; to HTML renderowany serwerowo, nie udokumentowane API.
- **frequency:** min. 3 badania w sezonie, odstęp maks. miesiąc (gov.pl GIS);
  cykl odświeżania strony nieznany
- **license / commercial_use / redistribution / rate_limit:** NIEZNANE — na
  stronach kąpieliska ani `/informacje` nie znaleziono regulaminu ani licencji
  (tekst portalu gov.pl jest CC BY-SA 4.0, ale to nie licencja danych serwisu)
- **attribution:** do ustalenia z GIS
- **status:** BLOCKED — brak zgody/warunków na automatyczne pobieranie
  (rule #15); potrzebny kontakt z GIS
- **last_verified_at:** 2026-10-01

## eea_bathing_water (EEA — Bathing Water Directive, rejestr + klasyfikacja roczna)

- **owner:** European Environment Agency (dane: organy państw członkowskich)
- **connector:** brak (kandydat, niezaimplementowany)
- **endpoint:** zbiór „Bathing Water Directive - Status of bathing water"
  (EEA Datahub, Excel .xls/.xlsx, publikacja 2026-06-02, pokrycie do 2025);
  usługa `https://marine.discomap.eea.europa.eu/arcgis/rest/services/BathingWater/BathingWater_Dyna_WM_2025/MapServer`
  (docelowa, ale pola `_2025` NIE sprawdzone; poniższą listę pól zweryfikowano
  na starszej `..._2018`, warstwa 0: `monitoringSiteIdentifier`, `bathingWaterName`, `countryName`,
  `bwWaterCategory`, `latitude`, `longitude`, `qualityStatus`,
  `qualityStatus_minus1..10`, `bwProfileLink`; JSON/geoJSON/PBF;
  `maxRecordCount` 1000 — wg `_2018`) — sprawdzone WebFetch 2026-10-01
- **frequency:** roczna (cykl raportowania Dyrektywy); NIE status bieżący
- **coverage:** Europa, w tym Polska (filtr po kraju niezweryfikowany)
- **license / commercial_use:** wydanie 2024 (rekord katalogu EEA
  `30e5d599-6bc1-408d-9e65-a10e433b81ef`): CC BY 4.0, copyright DG ENV/EEA
  (zweryfikowane 2026-10-01); wydanie 2025 — NIEZWERYFIKOWANE. ArcGIS ma
  usługę per rok (`..._2015`…`_2025`) — aktualna to `_2025`, nie `_2018`. Copyright usługi: „EEA, Bathing waters
  data and coordinates: Member states authorities"
- **rate_limit:** nieznany
- **attribution:** do ustalenia po potwierdzeniu licencji
- **nie zawiera:** przydatności bieżącej, przyczyny zamknięcia, E. coli,
  enterokoków, sinic, dat badań
- **status:** DISCOVERY (kandydat na rejestr lokalizacji + klasyfikację roczną;
  Gate niezaliczony — licencja wydania 2025, schemat pliku/pól `_2025` i filtr
  po kraju niepotwierdzone)
- **last_verified_at:** 2026-10-01

## dane.gov.pl (kąpieliska) — NIEZWERYFIKOWANE

Próba odczytu `api.dane.gov.pl` nie powiodła się (błąd uprawnień narzędzia),
wyszukiwanie WWW nie wskazało zbioru GIS. Status: DISCOVERY — sprawdzić ręcznie.

## imgw_warningsmeteo (ostrzeżenia meteorologiczne — Alert, ZABLOKOWANE na weryfikacji)

- **connector:** `imgw_warningsmeteo` — CZĘŚCIOWY: `client.py` (fetch + retry)
  i `parser.py::parse_warnings()` (dispatch listy/pustego stanu) gotowe i
  zweryfikowane. `normalize()` (mapowanie pól pojedynczego ostrzeżenia) i
  `ingest.py` CELOWO nie zaimplementowane — patrz niżej.
- **endpoint:** `https://danepubliczne.imgw.pl/api/data/warningsmeteo` —
  zweryfikowane na żywo 2026-09-29; przy braku ostrzeżeń zwraca
  `{"message": "Brak ostrzeżeń meteorologicznych"}` (potwierdzone na żywo)
- **blocker:** w chwili implementacji API nie zwracało ŻADNEGO aktywnego
  ostrzeżenia meteo, więc — w przeciwieństwie do `warningshydro`, gdzie miałem
  żywy przykład z realnymi wartościami pól — nie ma zweryfikowanego kształtu
  pojedynczego rekordu ostrzeżenia. Nieoficjalne źródła (scrapery stron
  trzecich) sugerują INNY schemat niż hydro (`id`, `stopien` 1–3, `tresc`,
  `teryt[]` — kody powiatów, nie województw jak w hydro) — nie zweryfikowane
  na żywo, więc świadomie NIE wpisane do `normalize()` (rule #10: nigdy nie
  zgadywać kształtu danych bezpieczeństwa; rule #15: Source Approval Gate
  wymaga realnej weryfikacji, nie inferencji). Decyzja użytkownika: poczekać
  na realny przykład zamiast budować na niepotwierdzonym schemacie.
- **license/rate_limit/attribution:** jak `imgw_hydro` wyżej (ten sam regulamin)
- **status:** DISCOVERY (częściowo IMPLEMENTED — patrz wyżej) — dokończyć
  `normalize()`/`ingest.py`/`GET /api/v1/alerts/latest` (rozszerzyć o
  `source_id="imgw_warningsmeteo"`) dopiero po zaobserwowaniu żywego,
  aktywnego ostrzeżenia meteo
- **last_verified_at:** 2026-09-29

## prg_gminy (GUGiK — Państwowy Rejestr Granic, granice gmin)

- **owner:** Główny Urząd Geodezji i Kartografii (GUGiK, Polska, instytucja publiczna)
- **connector:** `prg_gminy` (TASK-6.2) — import z LOKALNEGO pliku GeoJSON; connector
  niczego nie pobiera (`parser` + `ingest`, bez `client`), plik przygotowuje operator
- **endpoint (źródło, nie wołane przez aplikację):** wg strony
  `https://www.geoportal.gov.pl/pl/dane/panstwowy-rejestr-granic-prg/` (odczytanej
  2026-09-30): `https://opendata.geoportal.gov.pl/prg/granice/00_jednostki_administracyjne.zip`
  (SHP) i `.../00_jednostki_administracyjne_gml.zip` (GML) — jednostki administracyjne;
  archiwum 2005–2025: `https://opendata.geoportal.gov.pl/prg/granice_archiwalne/`
- **frequency:** wg tej strony: aktualizacja raz w roku, wg stanu na 1 stycznia (ADR-004:
  import ręczny, raz w roku — nie ma schedulera)
- **coverage:** cała Polska
- **license:** strona PRG: „Dane PRG są dostępne bezpłatnie i do dowolnego wykorzystania".
  NIE zweryfikowano formalnego tekstu licencji/warunków (np. czy wymagana jest atrybucja)
  — do potwierdzenia przez człowieka przed użyciem produkcyjnym
- **commercial_use:** UNKNOWN (sformułowanie „do dowolnego wykorzystania" sugeruje TAK, ale
  to nie jest zweryfikowany tekst licencji) — Source Approval Gate (#15) otwarty
- **attribution:** UNKNOWN — do ustalenia razem z licencją
- **format/rozmiar/układ:** SHP i GML zgodnie ze stroną; rozmiar pliku NIE ustalony; układ
  współrzędnych: strona wspomina PL-1992 (EPSG:2180) w przykładach, nie potwierdzono wprost
  — parser odrzuca pliki nie-WGS84 (walidacja bbox), więc błąd układu nie przejdzie cicho.
  Nazwy atrybutów (`JPT_KOD_JE`, `JPT_NAZWA_`) NIE zweryfikowane na prawdziwym pliku —
  konfigurowalne flagami CLI
- **dostępność z tego środowiska:** NIE — próba `curl -I` na powyższy URL z sandboxa dała
  `CONNECT tunnel failed, response 403` (egress proxy); nic nie pobrano ani nie
  sprawdzono na próbce danych
- **status:** DISCOVERY
- **last_verified_at:** 2026-09-30 (tylko treść strony PRG; nie same dane)

## teryt (GUS — rejestr TERYT, wykaz jednostek TERC)

- **owner:** Główny Urząd Statystyczny (GUS)
- **connector:** brak — TASK-6.2 bierze kody TERYT z atrybutów granic PRG (jedno źródło,
  spójne geometria↔kod); osobny import TERC nie jest potrzebny do point-in-polygon
- **endpoint:** strona `https://eteryt.stat.gov.pl/eTeryt/rejestr_teryt/udostepnianie_danych/baza_teryt/uzytkownicy_indywidualni/pobieranie/pliki_pelne.aspx`
  udostępnia pliki TERC, SIMC, ULIC, WMRODZ (przyciski „Pobierz"); istnieje też API TERYT
  (`api.stat.gov.pl`, wg wyników wyszukiwania — nie sprawdzano, czy wymaga rejestracji)
- **license/commercial_use/attribution/rate_limit/format:** UNKNOWN — strona nie podaje
  licencji ani formatu; nie sprawdzano plików
- **dostępność z tego środowiska:** NIE (egress proxy 403 dla eteryt.stat.gov.pl)
- **status:** DISCOVERY (nieużywane produkcyjnie)
- **last_verified_at:** 2026-09-30 (tylko treść strony)
