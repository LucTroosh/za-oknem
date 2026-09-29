# Backlog — kolejność realizacji do końca MVP

**Cel tego pliku:** jedna, uporządkowana lista tego, co zostało do zrobienia,
żeby nie skakać po tematach (decyzja użytkownika, 2026-09-29). Kolejność =
numeracja PHASE z `Development-Master-Plan-v1.2.md` (sekcja 2640+) — to już
jest przemyślana sekwencja zależności (np. Geo Engine przed geo-relevance
alertów), nie coś wymyślonego na nowo tutaj. W obrębie fazy: najpierw to, co
odblokowuje kolejne fazy i nie ma zewnętrznych zależności poza naszą kontrolą.

Status faz 0-4: **częściowo.** Vertical slice (GIOŚ PM2.5 → DB → API → mobile)
i szkielet infra (Docker/Caddy/CI, bez PostGIS/Redis/workerów/monitoringu/backupu
— patrz sekcja "Świadomie NIE w tej kolejce" niżej, to nie jest to samo co
"zrobione") są gotowe, patrz ROADMAP.md. Faza 4 (Air) ma jednak dziury —
patrz nowa sekcja "Phase 4 — Air (dokończenie)" poniżej: tylko PM2.5 jest
faktycznie zaciągane, reszta parametrów GIOŚ i indeks jakości powietrza — nie.

Ten plik żyje obok `ROADMAP.md` (stan faktyczny) i `source-registry.md` (źródła):
BACKLOG = co i w jakiej kolejności, ROADMAP = co już jest zrobione.
Aktualizować po każdym ukończonym tasku (odznaczyć, ew. dopisać kolejny).

## Zasady wykonania (bez zmian względem dotychczasowej sesji)

Task po tasku: branch → implementacja → testy → PR → `@codex review` →
weryfikacja realna każdego findingu względem kodu → root-cause fix → merge
(po green CI + czystym review) → aktualizacja ROADMAP.md w tym samym PR lub
małym follow-upie. Zero zgadywania kształtu danych bezpieczeństwa (rule #10).
Żadna zmiana architektury bez ADR (rule #12).

## Blokady wymagające Twojej akcji (nie mojej — flaguję z góry, nie czekam bezczynnie)

- **Phase 8, pyłki (CAMS/Copernicus ADS):** wymaga rejestracji konta na
  ads.atmosphere.copernicus.eu i klucza API — to musi zrobić człowiek
  (weryfikacja e-mail/warunki). Gdy dojdę do tej fazy, przygotuję connector
  pod gotowy kontrakt i poproszę Cię o sam klucz (jako zmienną środowiskową,
  nigdy w repo — rule #3).
- **Phase 10, push (Expo/FCM/APNs):** wymaga kont deweloperskich
  Google/Apple i kluczy — podobnie, przygotuję kod, klucze dostarczysz Ty.
- **Phase 11, kąpieliska (Sanepid/GIS):** `sk.gis.gov.pl` to appka JS bez
  udokumentowanego publicznego API — zbadam przez przeglądarkę (network
  requests), ale jeśli nie znajdę stabilnego, oficjalnego API, zgłoszę to
  zamiast zgadywać czy scrapować niestabilny endpoint.
- **Phase 9, ostrzeżenia meteo (TASK-9.2):** dalej BLOCKED — API IMGW wciąż
  nie zwróciło żadnego aktywnego ostrzeżenia (sprawdzone ponownie
  2026-09-29 11:xx, wciąż `{"message": "Brak ostrzeżeń meteorologicznych"}`).
  Nie da się tego przyspieszyć — będę to sprawdzać przy okazji innych tasków.

Wszystko inne poniżej nie ma zewnętrznych zależności i mogę to zrobić sam.

---

## Kolejka

### Phase 1 — Infra (dokończenie)

- [ ] **TASK-1.1:** Backup — §68 Master Planu definiuje zakres jako
      PostgreSQL + **konfigurację** + kluczowe dane, nie tylko bazę
      (poprzednia wersja tego tasku pokrywała wyłącznie PostgreSQL). `pg_dump`
      cykliczny dla bazy + kopia plików konfiguracyjnych (`.env`-szablony bez
      sekretów, `docker-compose.yml`, konfiguracja Caddy) — **przechowywane
      POZA VPS** (lokalna kopia na tym samym serwerze nie liczy się jako
      backup, bo utrata VPS niszczy oba egzemplarze naraz; np. wysyłka do
      S3-kompatybilnego storage lub innego hosta), retencja, oraz
      **regularny automatyczny test odtworzenia** (nie tylko udokumentowana
      procedura — §68: "sam backup bez testu odtworzenia nie jest
      wystarczający"). Priorytet przed jakimkolwiek wdrożeniem
      produkcyjnym, nawet jeśli reszta MVP jeszcze nie gotowa. **Realne
      sekrety (hasło DB, klucze API providerów, credentiale push,
      konfiguracja monitoringu) muszą mieć osobną, zabezpieczoną ścieżkę
      odtworzenia** — `.env`-szablony bez wartości (jak wyżej) nie
      wystarczą przy utracie VPS, bo nie da się z nich odtworzyć realnej
      konfiguracji. Zaszyfrowany backup sekretów (np. `sops`/`age` + ten
      sam off-host storage co reszta) albo zewnętrzny secret manager —
      rule #3 (żadnych sekretów w repo) nie zwalnia z ich backupu, tylko
      zabrania trzymać ich jawnie w git.

### Phase 2 — Backend Core (dokończenie)

- [ ] **TASK-2.1:** Generowany klient TypeScript z OpenAPI (§17 Master Planu)
      — `packages/api-contract/README.md` jest wciąż placeholderem, a
      `apps/mobile/app/index.tsx` ręcznie typuje odpowiedź dashboardu
      (potwierdzone w kodzie). Ta kolejka dokłada sporo nowych endpointów/pól
      (`/weather/forecast`, `/pollen/latest`, `/water/latest`, rozszerzenia
      `dashboard_latest()`) — bez generowanego klienta ręczne typy będą się
      cicho rozjeżdżać z realnym schematem FastAPI. Zrobić to **teraz**, przed
      dalszym rozszerzaniem integracji mobile (TASK-7.2 i kolejne), żeby nie
      duplikować pracy ręcznego przepisywania typów. **Wymaga najpierw
      Pydantic response models** — dziś endpointy danych (`dashboard_latest`,
      `latest_weather`, `latest_air_quality`) zwracają `-> dict` bez
      `response_model`, więc wygenerowany OpenAPI schema (i klient z niego)
      opisze je jako generyczne obiekty bez pól — bez typów żadna korzyść z
      generowanego klienta względem ręcznego rzutowania. Dodać
      `response_model` do tych endpointów w ramach tego tasku, przed
      generowaniem klienta.

### Phase 3 — Data Architecture (dokończenie)

- [ ] **TASK-3.1:** Raw ingestion / provenance (§33-34 Master Planu) — dziś
      connectory zapisują tylko znormalizowane rekordy (`Measurement`/
      `WeatherSnapshot`/`Forecast`), nie ma modelu `source_fetches` ani
      przechowania surowego payloadu (potwierdzone: brak `source_fetch`/
      `raw_payload` w kodzie). Bez tego nie da się odpowiedzieć na pytanie
      "co dokładnie zwróciło źródło w momencie zapisu tej wartości?" (§33) —
      istotne przy sporze o poprawność danych czy debugowaniu zmiany kształtu
      API źródła. Zakres: model `source_fetches` (źródło, endpoint, surowy
      payload, timestamp pobrania), **oraz FK `source_fetch_id` na
      znormalizowanych rekordach + wersja parsera/normalizacji + status
      walidacji** — bez tego linku, przy kilku odczytach tego samego
      `source_record_id` w czasie, nie da się jednoznacznie wskazać, który
      surowy payload wyprodukował którą wartość (§33 pytanie audytowe
      zostaje bez odpowiedzi mimo istnienia surowych payloadów) + migracja
      + integracja z każdym
      connectorem (zapis raw payloadu obok normalize) + polityka retencji
      (§33: 7-30 dni, zależnie od źródła). Wymaga ADR (nowy typ
      danych/tabeli w modelu, rule #12).

### Phase 4 — Air (dokończenie)

- [ ] **TASK-4.1:** Pełny zestaw parametrów GIOŚ — dziś connector `gios`
      zaciąga wyłącznie PM2.5 (świadomy zakres vertical slice, §108 Master
      Planu). Rozszerzyć `parser.py`/`ingest.py` o PM10, NO2, SO2, O3, CO,
      C6H6 (te same sensory API GIOŚ, ten sam kontrakt fetch/parse/validate/
      normalize — rozszerzenie istniejącego connectora, nie nowy). **Zakres
      obejmuje też ujawnienie tych parametrów** — dziś `air.py`/
      `dashboard.py` filtrują wyłącznie `PM2.5`, a mobile (`index.tsx`)
      renderuje tylko PM2.5, więc bez zmiany endpointów/agregatu/UI nowe
      parametry trafią do bazy i nigdzie dalej. Rozszerzyć te trzy miejsca
      o pełną listę (TASK-4.2 dokłada indeks/agregat na tym samym zestawie).
- [ ] **TASK-4.2:** Indeks jakości powietrza (AQI/CAQI wg metodologii GIOŚ) —
      zależny od TASK-4.1 (part potrzebuje >1 parametru). Do ustalenia: czy
      liczymy indeks sami wg opublikowanej metodologii GIOŚ, czy GIOŚ
      publikuje gotowy indeks per stacja do odczytania wprost (rule #10:
      jeśli liczymy sami, to nie jest to LLM ani zgadywanie — jawny,
      testowalny algorytm). **Zakres: indeks ogólny ORAZ indeksy cząstkowe
      per zanieczyszczenie** (oba wymienione osobno w MVP scope Master
      Planu) — nie tylko jeden zagregowany wynik. Tak jak TASK-4.1, wymaga
      też ujawnienia: zapis + `air.py`/`dashboard.py`/mobile, inaczej
      policzony indeks jest niewidoczny.

### Phase 5 — Weather (dokończenie)

- [ ] **TASK-5.3:** Forecast (§30 Master Planu) — nowy model `Forecast`
      (odrębny od `Measurement`, rule #7: `forecast_reference_time`,
      `valid_from`, `valid_until`, `model`, `source`), rozszerzenie
      `open_meteo` connectora o zapytanie `hourly`/`daily` obok `current`,
      `GET /api/v1/weather/forecast`. Wymaga ADR-010 (nowy typ danych w
      modelu, precedens: ADR-008 dla Measurement, ADR-009 dla Alert).
- [ ] **TASK-5.4:** Rozszerzyć `current`/`daily` o dew point, visibility, UV
      index. **Korekta (Codex) — poprzedni opis był błędny:** to NIE jest
      samo rozszerzenie `PARAM_CODES` "w tym samym zapytaniu bez
      dodatkowego round-tripu" — `client.py` (komentarz przy
      `CURRENT_PARAMS`) wprost stwierdza, że Open-Meteo udostępnia dew
      point/visibility/UV index WYŁĄCZNIE pod `hourly`, nie pod `current`.
      Samo dopisanie ich do `PARAM_CODES` sprawi, że `normalize()`
      (parser.py:41-46, pętla po `PARAM_CODES` rzucająca
      `OpenMeteoParseError` na brakujący parametr) odrzuci CAŁY payload
      pogodowy dla danej gminy, nie tylko te 3 pola — realna regresja
      current-weather, nie rozszerzenie. Realny zakres: dociągnięcie
      `hourly` w tym samym requeście (Open-Meteo obsługuje `current`+
      `hourly` razem, więc round-trip faktycznie nie rośnie), wybór
      obserwacji godzinowej najbliższej "teraz" (albo inna udokumentowana
      metoda wyprowadzenia wartości bieżącej z `hourly`), i dopiero potem
      zapis jako `WeatherSnapshot`. `PARAM_CODES`/`FORECAST_PARAM_CODES`
      zostają rozszerzone, ale logika parsera musi rozróżniać źródło
      (`current` vs `hourly`) per param, nie traktować ich jednolicie.
      **Zakres obejmuje też ujawnienie** — dziś mobile (`index.tsx`)
      renderuje tylko `temperature_2m`, TASK-5.5 dotyczy wyłącznie
      prognozy, a żaden późniejszy task nie wraca po dew point/
      visibility/UV; dodać je do API/mobile current-weather presentation
      w tym samym tasku. **Rozszerzenie zakresu (Codex, runda 6):** §5
      Master Planu wymienia jako MVP całą listę pól current-weather —
      temperatura odczuwalna, wilgotność, punkt rosy, ciśnienie,
      zachmurzenie, opady, deszcz, śnieg, wiatr, porywy, kierunek wiatru,
      widoczność, UV, kod warunków — nie tylko te 3 dodane wyżej. Connector
      po tym tasku będzie zapisywał większość z nich (`WeatherSnapshot`),
      ale żaden task nie ujawnia ich w API/mobile poza temperaturą i (z tej
      poprawki) dew point/visibility/UV. Zakres API/mobile presentation w
      tym tasku obejmuje więc pełny zestaw MVP z §5, nie tylko 3 pola
      wymagające dociągnięcia z `hourly`.
- [ ] **TASK-5.5:** Dostarczenie prognozy do użytkownika — TASK-5.3 kończy
      się na `GET /api/v1/weather/forecast`, ale nic go nie konsumuje:
      `dashboard_latest()` i mobile Home (`index.tsx`) czytają tylko
      current-weather. Dodać prognozę do agregatu (albo osobny fetch na
      ekranie pogody) + UI (§5 Master Planu wymienia prognozę jako MVP
      field), inaczej endpoint istnieje, ale jest niewidoczny dla
      użytkownika.

### Phase 6 — Geo Engine

- [ ] **TASK-6.2:** TERYT-based geo model (§26-27). **Druga korekta tego
      tasku** (Codex, runda 2): pierwsza korekta ograniczyła zakres do
      mapowania TERYT tylko dla 7 zaseedowanych miast — to za mało. ADR-005
      (Accepted) explicité przypisuje do Phase 6: pełny import listy gmin z
      TERYT (nie tylko 7 miast) ORAZ dopasowanie dowolnych współrzędnych
      użytkownika → najbliższa gmina (nearest-station/point-in-polygon) —
      to jest właśnie "migracja z seeda do pełnego Geo Engine", o której
      mówi ADR-005. Ograniczenie do 7 miast zostawiłoby TASK-12.3 (foreground
      location) bez możliwości rozpoznania użytkownika gdziekolwiek indziej
      w Polsce, co jest sprzeczne z celem MVP. Realny zakres TASK-6.2: (1)
      pełny import gmin TERYT do `geo_areas` (kolumna TERYT + granice
      administracyjne, np. z GUS/TERYT XML/CSV — potrzebujemy geometrii
      gminy, nie tylko punktu), (2) **point-in-polygon jako jedyna metoda
      dopasowania przynależności administracyjnej** (dowolne lat/lon →
      gmina) — ADR-002 mówi wprost o "przynależności administracyjnej"
      (point-in-polygon), nie o dystansie; "nearest-gmina" po odległości od
      centroidu może przypisać użytkownika blisko nieregularnej granicy do
      sąsiedniej gminy, co bezpośrednio psuje geo-matching alertów (Phase 9)
      i targeting push (Phase 10) — nearest-distance zostaje tym, czym jest
      dziś w ADR-006 (dopasowanie do najbliższej *stacji/punktu pomiarowego*,
      nie do jednostki administracyjnej), (3) `geo_area_id` jako wspólny
      klucz dla Alert Engine (Phase 9) i Push (Phase 10, ADR-002).
      Jeśli mimo to zdecydujesz na węższy zakres, wymaga to NAJPIERW rewizji
      ADR-005 i ADR-002 (rule #12 — nie wolno po cichu reinterpretować
      przyjętego ADR). **(4) Aktywność gminy jako filtr pollingu pogody** —
      `run_open_meteo()` dziś odpytuje KAŻDY wiersz `geo_areas` co 3h; przy
      pełnym imporcie ~2.5k gmin to ~20k zapytań/dzień, ponad limit
      Open-Meteo 10000/dzień (`source-registry.md`). Import TERYT musi więc
      wprowadzić rozróżnienie "gmina do geo-matchingu" (zawsze, do alertów/
      push) vs. "gmina z aktywnym pollingiem pogody" (tylko wybrane/
      obserwowane lokalizacje użytkowników), inaczej TASK-6.2 samo w sobie
      wyłącza pogodę przy wdrożeniu. **(5) Resolver TERYT dla klienta** —
      TASK-12.3 dostarcza surowe współrzędne GPS, a TASK-12.5 wymaga
      `observed_area_code`; żaden task nie wystawia point-in-polygon z (2)
      przez API. Dodać endpoint (np. `POST /api/v1/geo/resolve` lub przyjęcie
      współrzędnych bezpośrednio w `POST /api/v1/devices` z serwerowym
      resolve) pod ograniczeniami ADR-002 (bez trwałego logowania precyzyjnej
      lokalizacji) — inaczej TASK-12.5 nie da się zaimplementować bez
      duplikowania geometrii gmin w aplikacji mobilnej. **(6) PostGIS** —
      "Świadomie NIE w tej kolejce" (patrz sekcja niżej) odkłada PostGIS
      dokładnie do momentu, gdy Phase 6 Geo Engine "tego faktycznie
      zażąda" (ADR-006) — import geometrii gmin + point-in-polygon z (1)/(2)
      JEST tym momentem. Realny zakres obejmuje więc też provisioning i
      użycie PostGIS (nie tylko in-process biblioteki geometrii w Pythonie)
      — inaczej ten task da się ukończyć bez PostGIS mimo że stack i §26-27
      go zakładają. **(7) Zasięg stacji GIOŚ** — pełny import TERYT
      rozwiązuje geo-matching administracyjny, ale `run_gios()`
      (`scheduler.py`) nadal odpytuje wyłącznie ręcznie skonfigurowane
      `GIOS_STATION_IDS`, a ADR-006 dopasowuje tylko do już zaciągniętych
      stacji w promieniu 50 km — użytkownik poza tą garstką dostanie
      poprawną gminę, ale zero danych o powietrzu. Dodać do zakresu
      odkrycie/dobór stacji GIOŚ per aktywna gmina (katalog stacji + ich
      polling), nie tylko geo-matching bez danych do dopasowania. **(8)
      Zawężenie dashboardu do wybranej lokalizacji** — `dashboard_latest()`
      dziś zwraca `areas` dla KAŻDEGO wiersza `geo_areas`
      (`dashboard.py:25-88`); przy pełnym imporcie ~2.5k gmin z (1) ten sam
      request liczyłby i pobierał dane dla całego kraju zamiast pojedynczej
      lokalizacji użytkownika. TASK-12.2 tylko rozszerza selektor, żaden
      task nie dodaje kontraktu "wybrana lokalizacja" do requestu. Dodać
      parametr (np. `geo_area_id`/`observed_area_code`) zawężający agregat
      do lokalizacji z manualnego wyboru (TASK-12.2) lub GPS-resolve z (5).

### Phase 7 — Dashboard (dokończenie)

- [ ] **TASK-7.1:** Source transparency na mobile — **korekta względem
      wcześniejszej wersji:** samo wyrenderowanie `station_name` nie
      wystarczy (a) bo weather w ogóle nie jest station-based (`geo_area`,
      nie stacja — nie ma czego tu renderować jako "nazwę stacji"), (b) bo
      `GET /api/v1/dashboard/latest` dziś nie zwraca w ogóle identyfikatora
      źródła dla `weather` (`air` ma `station_name`, ale ani jeden blok nie
      ma pełnego tekstu atrybucji). Realny zakres: dodać do
      `dashboard_latest()` pola `source` (id źródła) + `attribution` (pełny
      tekst z `source-registry.md`, dosłownie — np. "Weather data by
      Open-Meteo.com (CC BY 4.0)", "Dane: Główny Inspektorat Ochrony
      Środowiska (GIOŚ)") **+ `observed_at`** (kontrakt source-transparency
      to source+timestamp+freshness razem, nie samo źródło — dziś oba bloki
      zwracają `freshness`, ale nie `observed_at`, więc użytkownik widzi
      "FRESH", ale nie widzi KIEDY) w obu blokach (`air`, `weather`), potem
      dopiero ekran mobile renderujący te trzy pola per sekcja (nie tylko
      nazwę stacji). **Wzorzec obowiązuje dla każdej kolejnej sekcji danych** —
      TASK-7.2 (IMGW hydro/alerty), TASK-8.8 (CAMS pyłki), TASK-11.5
      (kąpieliska/Sanepid) muszą dodać `source`+`attribution` do swoich
      bloków tym samym wzorcem, nie tylko `air`/`weather`; source-registry.md
      już wymaga widocznej atrybucji IMGW i Copernicus, więc to nie jest
      opcjonalne rozszerzenie.
- [ ] **TASK-7.2:** **Korekta: `alerts` musi wejść do `dashboard_latest()`**
      (§55 Master Planu wymienia `alerts` wprost w agregacie: location,
      alerts, air, weather, pollen, outdoor, water) — dziś `dashboard_latest()`
      ma tylko `air`+`weather`, poprzednia wersja tego tasku kazała mobile
      pobierać `/alerts/latest` osobno, co jest niezgodne z §55 (agregat ma
      ograniczać liczbę niezależnych requestów). Zakres: dodać `alerts`
      (niefiltrowane — TASK-9.7 dodaje filtrowanie po lokalizacji dopiero po
      Phase 9) do `dashboard_latest()`, potem sekcja alertów na mobile
      czyta z agregatu. Hydrologia (realny endpoint: `GET /api/v1/hydro/
      latest` w `apps/api/app/api/v1/hydro.py` — nie `/api/v1/hydrology`,
      uważać przy implementacji mobile fetcha; §8) nie jest wymieniona w
      §55 jako część agregatu — zostaje osobnym fetchem na mobile, czysto
      frontendowa robota. Wzorzec `source`/`attribution` z TASK-7.1 (IMGW)
      dotyczy obu. **Brakujący element (Codex):** w przeciwieństwie do
      `alerts` (który ma jawne odroczenie geo-matchingu do TASK-9.5),
      hydrologia nie ma ŻADNEGO tasku dodającego geo-matching —
      `/api/v1/hydro/latest` zwraca dziś WSZYSTKIE wodowskazy w kraju
      (zweryfikowane w `hydro.py:50-95`, brak parametru lokalizacji), więc
      "osobny fetch" bez dalszego kroku oznacza ogólnokrajową listę zamiast
      lokalnego kontekstu. Dodać do zakresu TASK-9.5 (skoro i tak dodaje
      geo-matching w tej samej fazie) albo osobnego tasku Phase 9
      dopasowanie najbliższego wodowskazu per gmina, tym samym wzorcem
      nearest-station/haversine co ADR-006 dla GIOŚ — nie zostawiać tego
      bez właściciela.
- [ ] **TASK-7.3:** Stany stale/no-data w UI (obecnie tylko
      loading/error/ready) — §59/§80 Master Planu.
- [ ] **TASK-7.4:** Source-level freshness (UNAVAILABLE: pusta lista =
      potwierdzone zero czy dawno nie było fetcha) — dotyczy `/air`,
      `/hydro`, `/alerts`, `/weather` razem. Wymaga własnego ADR-012
      (świadomy non-goal z ADR-009, teraz adresowany). **Korekta (Codex):**
      mobile Home czyta wyłącznie `/api/v1/dashboard/latest`
      (`apps/mobile/app/index.tsx`), nie te cztery endpointy osobno —
      ograniczenie zakresu do nich zostawia agregat (`air`/`weather: null`
      w `dashboard.py`) bez rozróżnienia "potwierdzone zero" od "źródło
      nigdy nie fetchowało/przestało fetchować", czyli dokładnie ten sam
      problem widoczny tam, gdzie użytkownik faktycznie go zobaczy. Zakres
      obejmuje więc też przeniesienie stanu UNAVAILABLE do kontraktu
      `dashboard_latest()` i jego renderowania na mobile, nie tylko cztery
      detail endpointy. **Brakujący zakres (Codex):** `water` (TASK-11.4)
      i `pollen` (TASK-8.7) trafiają do tego samego agregatu (§55) i mają
      dokładnie ten sam problem "pusta lista vs źródło nigdy nie
      fetchowało" (Sanepid/CAMS też mogą milczeć bez błędu), ale powstają
      w Phase 8/11 — po tym tasku. TASK-8.7/TASK-11.4/TASK-11.6/TASK-8.9
      muszą reużyć ADR-012 z tego tasku (ten sam czterostanowy model
      FRESH/RECENT/STALE/UNAVAILABLE), nie definiować freshness dla
      water/pollen od nowa ani po cichu pomijać rozróżnienia
      "potwierdzone zero".
- [ ] **TASK-7.6:** Outdoor Interpretation Engine (§52 Master Planu) —
      deterministyczny, testowalny algorytm (temperatura + opady + wiatr +
      jakość powietrza + UV → GOOD/MODERATE/POOR + `reasons[]`); **nie LLM**
      (rule #10, §52/§53 explicité to zabraniają dla samej klasyfikacji).
      Zależny od Forecast (TASK-5.3, gotowe) i pełnego zestawu parametrów
      GIOŚ (TASK-4.1) dla wejść.
- [ ] **TASK-7.7:** `outdoor` w payloadzie `dashboard_latest()` (§55) — wynik
      TASK-7.6 per geo_area, zależny od TASK-7.6.
- [ ] **TASK-7.8:** `OutdoorCard` na mobile dashboard (§56/§58) — bez tego
      TASK-7.6/7.7 nic nie pokazują użytkownikowi. Dotyczy też preferencji
      "outdoor" z TASK-12.4 (kiedy pokazywać kartę / dla kogo jest istotna).

### Phase 8 — Pollen

- [ ] **TASK-8.5:** Source Approval Gate dla `cams` (Copernicus ADS) —
      **BLOKADA: potrzebny klucz API od Ciebie**, patrz sekcja blokad wyżej.
      Do tego czasu: przygotować kontrakt connectora (client/parser/normalize)
      pod znany format CAMS bez możliwości żywej weryfikacji, zaznaczyć
      jawnie w source-registry jako DISCOVERY→VERIFIED dopiero po realnym
      dostępie (rule #10/#15 — nie zgadywać kształtu).
- [ ] **TASK-8.6:** Model `PollenSnapshot` (ADR-001 opcja C — snapshot per
      gmina, jak weather) + migracja Alembic + ingest — dopiero po
      TASK-8.5, wymaga działającego klucza CAMS. **Konkretnie 5 gatunków z
      §6 MVP: olcha, brzoza, trawy, bylica, ambrozja** — nie generyczny
      agregat ani podzbiór; wymienić je jawnie w modelu/ingest/endponcie
      (TASK-8.7)/karcie mobile (TASK-8.8) i acceptance criteria każdego z
      tych tasków. **Zakres obejmuje też
      wpięcie w `app/scheduler.py`** (job raz dziennie, ten sam wzorzec
      izolacji błędów co `run_open_meteo`/`run_gios`) — bez tego
      `/pollen/latest` i dashboard zależą od ręcznych uruchomień ingestu i
      z czasem pokażą dane STALE/UNAVAILABLE mimo działającego connectora.
      **Wymóg z TASK-3.1 (Codex):** ten connector powstaje w Phase 8, już
      po Phase 3 — ukończenie TASK-3.1 samo w sobie nie obejmuje connectorów,
      które jeszcze nie istniały. Ingest musi zapisywać `source_fetch_id`
      (+ surowy payload/wersję parsera/status walidacji z kontraktu TASK-3.1)
      tak samo jak GIOŚ/Open-Meteo — nie zakładać, że to "już zrobione".
- [ ] **TASK-8.7:** `GET /api/v1/pollen/latest` (freshness, grupowanie per
      geo_area, ten sam wzorzec co `/weather/latest`) — czyta wyłącznie z
      naszej bazy (rule #14).
- [ ] **TASK-8.8:** Karta pyłkowa na mobile dashboard (§Phase 8 Master
      Planu: "pollen card") — bez tego Phase 8 nie dostarcza niczego
      użytkownikowi mimo działającego backendu. Profil alergika (który
      pyłki są dla mnie istotne) to już TASK-12.4, nie duplikować tu.
      Wzorzec `source`/`attribution` z TASK-7.1 (Copernicus) dotyczy też tej
      karty.
- [ ] **TASK-8.9:** Dodać `pollen` do `dashboard_latest()` (§55 — pollen to
      część głównego agregatu, nie tylko `/pollen/latest`; §55 wymaga też,
      że `pollen` w tej odpowiedzi zawsze pochodzi z lokalnego snapshotu, nie
      z zapytania do CAMS na żądanie). Zależne od TASK-8.7 (endpoint/dane
      muszą istnieć) — **przeniesione tu z Phase 7** (Codex: poprzednia
      wersja umieszczała to przed własną zależnością).

### Phase 9 — Alerts (dokończenie)

- [ ] **TASK-9.4:** `Event` model (§31) — odrębny od `Alert`/`Measurement`
      (rule #7). Potrzebny do "istotne lokalne zagrożenia / zweryfikowane
      zdarzenia" z ROADMAP §2.6. Wymaga ADR-013 (nowy typ danych). **Zakres
      obejmuje też realną ścieżkę zasilania** — sam model bez źródła danych
      zostaje pustą tabelą, a TASK-9.6 (Alert Engine) zakłada istniejące
      rekordy `Event`. Dziś istniejące connectory (np. IMGW warnings) piszą
      wprost do `Alert`, nie ma workflow tworzącego `Event`. **Korekta
      (Codex, runda 6) — poprzednia wersja pozwalała po cichu wyrzucić
      scope z MVP:** "istotne lokalne zagrożenia" i "zweryfikowane zdarzenia
      środowiskowe" to explicit pozycje MVP w §9 Master Planu ("ALERTY I
      ZDARZENIA"), nie Future — "świadomie ograniczyć MVP do samego modelu
      bez populacji" byłoby cichym zdjęciem zatwierdzonego zakresu MVP przez
      wpis w ADR, nie decyzją do podjęcia w treści taska. Ten task nie ma
      dziś zidentyfikowanego źródła danych dla tej kategorii (IMGW ostrzega
      przez `Alert`, nie przez zdarzenia zweryfikowane) — **BLOKADA:
      potrzebna Twoja decyzja o źródle** (np. RCB/RSO, informacje służb,
      albo ręczny/administracyjny workflow zgłaszania zdarzeń), tym samym
      wzorcem jak TASK-8.5 (CAMS) blokuje na kluczu API. Do czasu decyzji:
      przygotować kontrakt modelu/ingestu, ale nie zamykać Phase 9 (TASK-9.6
      zależny od realnych rekordów `Event`) bez albo działającego źródła,
      albo jawnej rewizji zakresu MVP w ADR-013 zatwierdzonej przez Ciebie
      (rule #12) — nie przez implementatora po cichu.
- [ ] **TASK-9.5:** Geo-matching alertów → lokalizacja (zależne od
      TASK-6.2) — dziś `/alerts/latest` zwraca WSZYSTKO, bez filtrowania.
      **Zakres obejmuje też `dashboard_latest()`** — TASK-7.2 dodał tam
      `alerts` świadomie niefiltrowane (Phase 9 jeszcze nie istniało), a
      TASK-9.7 filtruje tylko osobny ekran Alerty, więc bez tej poprawki
      tutaj główny dashboard nadal pokazywałby wszystkie alerty krajowe
      mimo ukończenia całej kolejki. Zastosować ten sam geo-matching do
      pola `alerts` w agregacie. **I do hydrologii (Codex, patrz TASK-7.2)**
      — `/api/v1/hydro/latest` ma dokładnie ten sam brak filtrowania co
      `/alerts/latest` miał przed tym taskiem, a żaden inny task go nie
      adresuje; dodać nearest-station matching (wzorzec ADR-006) tu, przy
      okazji tej samej pracy nad geo-matchingiem.
- [ ] **TASK-9.6:** Alert Engine (§47) — severity, deduplication, geo
      relevance, na bazie modeli `Alert`+`Event`+geo-matching z powyższych
      tasków. Duży task, prawdopodobnie do rozbicia na 2-3 mniejsze PR.
- [ ] **TASK-9.7:** Osobny ekran "Alerty" (mobile) — przeniesiony tu z
      Phase 7 (Codex: nie da się go zrobić wcześniej w kolejności, bo
      zależy od TASK-9.5 wyżej). Dziś alerty (od TASK-7.2) są co najwyżej
      niefiltrowaną sekcją dashboardu; potrzebny dedykowany ekran z pełną
      listą, szczegółem alertu (treść źródłowa, timestamp, źródło — rule
      #10: LLM nigdy nie jest źródłem prawdy dla alertów, więc pokazujemy
      oryginalny tekst, nie streszczenie), i filtrowaniem po lokalizacji
      (TASK-9.5). **Zakres obejmuje bottom navigation (§57: Home/Alerty/
      Settings)** — dziś root layout to sam stack, więc ten ekran (i później
      Settings z TASK-12.1) powstałby bez sposobu, żeby użytkownik się do
      niego dostał. Wprowadzić tab layout tutaj, jako pierwszy task, który
      faktycznie potrzebuje drugiej zakładki (Settings z TASK-12.1 dokłada
      tylko trzecią do gotowego layoutu).
- [ ] Ostrzeżenia meteo (TASK-9.2) — pozostaje BLOCKED, sprawdzane przy
      okazji (patrz sekcja blokad).

### Phase 10 — Push

- [ ] **TASK-10.1:** Device registration + push tokens (Expo) —
      **BLOKADA: klucze FCM/APNs od Ciebie**, patrz sekcja blokad wyżej.
      Przygotuję backend (model tokenu, endpoint rejestracji) niezależnie od
      blokady, bo to nie wymaga kluczy zewnętrznych. APNs konkretnie wymaga
      konta Apple Developer, które w tej kolejce jest dopiero w TASK-16.3
      (6 faz dalej) — samo konto/enrollment (nie cały zakres TASK-16.3:
      store listing, TestFlight) to decyzja biznesowa, którą możesz podjąć
      wcześniej równolegle, żeby nie blokować walidacji APNs aż do Phase 16;
      jeśli nie, walidacja end-to-end dla iOS zostaje odłożona do tego czasu
      (backend/Android część kończy się normalnie). **Zakres obejmuje też
      §65-66 Master Planu** — device registration to endpoint operacyjny
      (nie publiczny read), więc wymaga validation + rate limiting + abuse
      protection wprost, nie jako opcjonalny przykład użycia Redis w
      TASK-15.4 — bez tego dowolny klient może masowo tworzyć/odświeżać
      rekordy urządzeń i zasilać push niezweryfikowanymi tokenami.
- [ ] **TASK-10.5:** Mobile client push registration (`expo-notifications`)
      — TASK-10.1 kończy się na backendzie (model + endpoint), ale żaden
      task nie prosi o uprawnienie powiadomień, nie pobiera Expo push
      tokena ani nie wysyła go do `POST /api/v1/devices` z appki. Bez tego
      TASK-10.2 (Notification Engine) zakłada tokeny, których żaden klient
      nigdy nie zarejestrował — świeża instalacja nie dostanie push w
      ogóle. Zakres: permission request, pobranie tokena, wysyłka przy
      starcie + cykl odświeżania (token refresh). Zależne od TASK-10.1
      (endpoint musi istnieć).
- [ ] **TASK-10.2:** Notification Engine + anti-spam (zależne od Alert
      Engine z Phase 9 i tokenów z TASK-10.1/TASK-10.5).
- [ ] **TASK-10.3:** Preferencje powiadomień — użytkownik wybiera, jakie
      kategorie alertów/dla jakich lokalizacji dostaje push (§Phase 10
      Master Planu: "notification preferences"). **Nie tylko mobile UI** —
      Notification Engine (TASK-10.2) decyduje server-side, zanim klient w
      ogóle się odezwie (app w tle/zabita), więc preferencje muszą mieć
      model + endpoint per-urządzenie (nie lokalny stan appki) i TASK-10.2
      musi je faktycznie sprawdzać przed wysyłką — inaczej zmiana ustawień
      nie ma efektu, a TASK-10.2 nadal wysyła wszystko do wszystkich.
- [ ] **TASK-10.4:** Deep links z powiadomienia do konkretnego
      alertu/ekranu w appce (§Phase 10 Master Planu: "deep links"). Zależne
      od TASK-9.7 (ekran Alerty, żeby było dokąd linkować).

### Phase 11 — Water / Hydrology (dokończenie)

- [ ] **TASK-11.1:** Research + Source Approval Gate dla kąpielisk
      (Sanepid/GIS) — zobacz blokadę wyżej, może wymagać zbadania
      `sk.gis.gov.pl` przez przeglądarkę zamiast dokumentacji API.
- [ ] **TASK-11.2:** Connector `bathing_water` (o ile TASK-11.1 znajdzie
      stabilne źródło) — status kąpieliska, przyczyna zamknięcia, sezon,
      E. coli/enterokoki/sinice, daty badań, **oraz nazwa i lokalizacja
      kąpieliska (współrzędne + `geo_area_id`/gmina)** — bez tego przy
      wielu kąpieliskach nie da się dopasować "najbliższe/istotne dla mnie"
      (TASK-11.4/11.5) ani określić, którego użytkownika dotyczy zamknięcie
      jako alert (TASK-11.3). Kontrakt connectora
      (fetch/parse/validate/normalize) kończy się na `parser.py`/
      `ingest.py`, ale zakres tego tasku musi objąć też model + migrację
      Alembic + wpięcie w harmonogram — bez tego TASK-11.4 (czyta wyłącznie
      z naszej bazy, rule #14) nie ma z czego czytać. **Wymóg z TASK-3.1
      (Codex):** ten connector powstaje w Phase 11, długo po Phase 3 —
      musi zapisywać `source_fetch_id` (+ surowy payload/wersję parsera/
      status walidacji z kontraktu TASK-3.1) tak samo jak GIOŚ/Open-Meteo,
      nie zakładać, że TASK-3.1 to już pokrywa.
- [ ] **TASK-11.3:** "Zamknięcia kąpielisk" jako Alert/Event (zależne od
      TASK-11.2 + modeli z Phase 9).
- [ ] **TASK-11.4:** `GET /api/v1/water/latest` — status kąpieliska,
      przyczyna zamknięcia, sezon, wyniki badań, daty (Master Plan MVP:
      `/api/v1/water`) — czyta wyłącznie z naszej bazy (rule #14). Bez tego
      TASK-11.2/11.3 zbierają dane, których użytkownik nigdy nie zobaczy
      poza samym faktem zamknięcia jako alertu. **Zakres obejmuje freshness
      (rule #8)** — TASK-7.4 pokrywa tylko `/air`, `/hydro`, `/alerts`,
      `/weather`, nie `/water`; przy danych bezpieczeństwa (otwarte/
      zamknięte kąpielisko) brak rozróżnienia FRESH/STALE jest szczególnie
      ryzykowny — nieaktualny status "otwarte" wygląda identycznie jak
      aktualny. **Brakujący geo-matching (Codex):** §27 Master Planu
      wymaga wprost `USER LOCATION → NEAREST RELEVANT SITE → WATER STATUS`
      dla kąpielisk, tym samym wzorcem co stacje powietrza — dziś ani ten
      task, ani żaden inny nie definiuje parametru lokalizacji/dopasowania
      najbliższego kąpieliska, mimo że TASK-11.2 zapisuje współrzędne
      właśnie w tym celu. Dodać nearest-site matching (wzorzec
      nearest-station/haversine z ADR-006) do `/water/latest`.
- [ ] **TASK-11.5:** Sekcja kąpielisk na mobile (status, badania, sezon) —
      dopiero po TASK-11.4. Wzorzec `source`/`attribution` z TASK-7.1
      (Sanepid/GIS) dotyczy też tej sekcji.
- [ ] **TASK-11.6:** Dodać `water` do `dashboard_latest()` (§55 — water to
      część głównego agregatu). Zależne od TASK-11.4 (endpoint/dane muszą
      istnieć) — **przeniesione tu z Phase 7** (ten sam powód co TASK-8.9).
      Geo-matching z poprawki TASK-11.4 dotyczy też pola `water` w
      agregacie — bez tego dashboard pokazywałby niezwiązane kąpielisko
      zamiast najbliższego.

### Phase 12 — Settings / Profiles

- [ ] **TASK-12.1:** Ekran Settings (mobile) — placeholder/skeleton, potem
      realne preferencje. Bottom navigation (§57) wprowadzone już w TASK-9.7
      (pierwszy ekran wymagający drugiej zakładki) — tu tylko dodać trzecią
      zakładkę do istniejącego tab layoutu, nie tworzyć nawigacji od nowa.
- [ ] **TASK-12.6:** Pozostałe sekcje Settings z §60 Master Planu — location/
      profile/allergies/outdoor/notifications pokrywają TASK-12.2/12.3/
      12.4/10.3, ale §60 wymienia też **data & privacy, sources, about**, dla
      których żaden task nie istnieje. Dodać te trzy sekcje (privacy policy/
      dane, ekran źródeł — ten sam wzorzec `source`/`attribution` co
      TASK-7.1 — i o aplikacji) przed release, nie zostawiać jako
      placeholder.
- [ ] **TASK-12.2:** Ręczny wybór lokalizacji (mobile) — rozszerzenie
      obecnej statycznej listy 7 miast o wybór przez użytkownika (bez
      background location — rule #11). **Korekta (Codex):** po TASK-6.2
      punkt (8) `dashboard_latest()` zawęża się do jednej wybranej
      lokalizacji (`geo_area_id`) z pełnego importu TERYT (~2.5k gmin) —
      dziś `apps/mobile/app/index.tsx` nie ma żadnego katalogu gmin, cały
      wybór pochodzi z odpowiedzi dashboardu (który po 6.2 zwraca tylko
      jedną lokalizację). Bez osobnego źródła danych do wyboru użytkownik
      z wyłączonym GPS nie ma jak w ogóle wybrać gminy. Zakres obejmuje
      więc dodanie przeszukiwalnego/paginowanego endpointu gmin (albo
      spakowanie zaimportowanego katalogu TERYT do klienta) — nie tylko
      rozszerzenie UI selektora.
- [ ] **TASK-12.3:** Foreground location (device geolocation, jednorazowe
      żądanie, minimalne uprawnienia — rule #8/§8 Master Planu Principle 8).
      **Brakujące podpięcie (Codex):** dziś żaden task nie łączy wyniku tego
      GPS-odczytu z tym, co użytkownik faktycznie widzi na dashboardzie —
      TASK-6.2(5)/TASK-12.5 prowadzą wyłącznie do rejestracji push
      (`observed_area_code` w `POST /api/v1/devices`), nie do wyboru
      lokalizacji w `apps/mobile/app/index.tsx`. Po TASK-6.2(8) zawężającym
      `dashboard_latest()` do jednej wybranej lokalizacji, ekran Home musi
      mieć skądś tę lokalizację — bez tego podpięcia użytkownik z włączonym
      GPS nadal widziałby domyślną/ostatnio ręcznie wybraną gminę z
      TASK-12.2, nie tę, w której faktycznie jest. Zakres obejmuje więc
      użycie resolvera z TASK-6.2(5) (współrzędne GPS → `geo_area_id`) jako
      źródła domyślnej/aktualizowanej lokalizacji w selektorze TASK-12.2,
      nie tylko jako danych wejściowych do TASK-12.5.
- [ ] **TASK-12.5:** Wysyłka `observed_area_code` do `POST /api/v1/devices`
      przy każdym otwarciu appki z aktywną lokalizacją (foreground) i przy
      ręcznej zmianie lokalizacji w Settings (ADR-002, sekcja Decision) —
      **brakujące wcześniej**: TASK-12.2/12.3 tylko pobierają/wybierają
      lokalizację, TASK-10.1 tylko przygotowuje backend; bez tego klienckiego
      wpięcia zarejestrowane urządzenie ma nieaktualny lub brak
      `observed_area_code`, więc push trafia do złej gminy albo wcale.
      Zależne od TASK-10.1 (endpoint musi istnieć), TASK-12.2/12.3 (skąd
      wziąć lokalizację) i resolvera TERYT z TASK-6.2 punkt (5) (GPS →
      `observed_area_code` po stronie serwera).
- [ ] **TASK-12.4:** Profil użytkownika + podstawowe preferencje (allergy,
      family, outdoor — §12 Master Planu). Bez obowiązkowego konta (rule #11)
      — do przemyślenia jak to pogodzić z "profilem" w MVP bez logowania
      (prawdopodobnie: lokalny profil per-urządzenie, nie serwerowe konto).
      "outdoor" tu to tylko przechowana preferencja (czy ta osoba w ogóle
      chce widzieć `OutdoorCard`) — sam silnik interpretacji to TASK-7.6/
      7.7/7.8 (Phase 7), nie duplikować logiki tutaj. **Zakres obejmuje też
      realne zastosowanie preferencji** — karty pyłkowa/outdoor powstały
      wcześniej (Phase 7/8) i żaden późniejszy task nie wraca do nich, żeby
      uwzględnić allergy/family/outdoor z tego tasku; bez tej integracji
      zmiana ustawień nie ma żadnego efektu w produkcie. Dodać krok
      "zastosuj profil" po TASK-12.4 do dashboardu/kart pyłkowej/outdoor.

### Phase 13 — Data Quality / Observability

- [ ] **TASK-13.1:** Source health / stale monitoring — rozszerzenie
      istniejącego per-wiersz freshness o widoczny status źródła
      (przydatne razem z TASK-7.4). **Pełny zakres §44 Master Planu**: last
      attempted/successful fetch, duration, records fetched/processed,
      validation errors, duplicate rate, stale rate, source availability —
      dzisiejszy scheduler (ADR-007) trzyma stan tylko w pamięci procesu i
      nie ma historii runów, więc po restarcie/nieudanym fetchu operator nie
      odtworzy tych sygnałów. Zakres obejmuje trwałe (DB lub zewnętrzny
      monitoring z TASK-13.2) przechowanie per-run telemetrii, nie tylko
      aktualnego stanu. **Brakujący element (Codex):** ADR-001 wprost wymaga
      "licznik dziennych wywołań per źródło w bazie, alert przy 70% dziennego
      limitu", a ADR-004 rozszerza ten wymóg na każdy connector — żaden task
      w tej kolejce tego nie implementuje. Bez tego rosnący zbiór aktywnych
      gmin (TASK-6.2) może po cichu wyczerpać limit Open-Meteo/CAMS i
      zostawić pogodę/pyłki stale dla wszystkich, zanim ktokolwiek to
      zauważy. Zakres TASK-13.1 obejmuje więc też ten licznik+alert, nie
      tylko listę sygnałów z §44.
- [ ] **TASK-13.2:** Monitoring/error-reporting (§69 Master Planu) —
      **korekta: sam `logging` NIE wystarczy** (poprzednia wersja tego tasku
      błędnie na to pozwalała). §69 wymaga realnego capture wyjątków
      mobile/API (Sentry lub odpowiednik) + metryk (API latency, error rate,
      connector success, stale data, push delivery) — to są rzeczy, których
      structured `logging` bez zewnętrznego serwisu nie daje (agregacja,
      alerty, wyszukiwanie po incydencie). Wymaga zewnętrznego konta
      (Sentry lub odpowiednik) — **BLOKADA: decyzja/konto od Ciebie**, jeśli
      wybierzemy płatny plan; jest darmowy tier, więc to nie musi wstrzymać
      startu tasku. TASK-15.3 (Phase 15) to tylko wdrożenie tego na
      produkcji, nie substytut.
- [ ] **TASK-13.3:** Minimalne analytics eventy (§70 Master Planu):
      `app_open`, `location_selected`, `dashboard_view`, `alert_open`,
      `notification_open`, `settings_open` — nic ponad to (§70: "nie
      zbieramy więcej danych niż potrzebujemy"). Zależne od decyzji
      narzędzia (self-hosted vs. zewnętrzne — inwentaryzacja co zbieramy
      trafia jako wejście do TASK-14.2's Privacy Policy).

### Phase 14 — Security / Privacy

- [ ] **TASK-14.1:** SDK inventory (§72 Master Planu) — `docs/privacy/
      sdk-inventory.md`, dla każdego SDK z danymi osobowymi: nazwa, dane,
      cel, Android, iOS, processor/provider, transfer, retention, **żadnych
      wartości TBD przed release** (§72 explicité). Musi powstać po
      zainstalowaniu Sentry (TASK-13.2), analytics (TASK-13.3), SDK
      lokalizacji (TASK-12.3) i push (TASK-10.1/Expo/FCM/APNs) — inaczej nie
      ma czego inwentaryzować. **Brakujące wcześniej**: bez tego Privacy
      Policy/Data Safety w TASK-14.2 nie da się rzetelnie zweryfikować
      względem faktycznych zależności.
- [ ] **TASK-14.2:** Przegląd bezpieczeństwa, RODO, Privacy Policy, Data
      Safety / App Privacy — oparte na TASK-14.1 (SDK inventory) **oraz na
      pełnym data inventory z §71** (SDK inventory pokrywa tylko dane
      przechodzące przez SDK-i mobilne, nie dane przetwarzane wyłącznie
      backendowo: `device_id`, push token, `observed_area_code`, logi
      serwera i ich retencja — §71: DATA INVENTORY → PURPOSE → LEGAL BASIS →
      RETENTION → PROCESSORS → USER RIGHTS, dla wszystkich danych, nie tylko
      tych z SDK). W dużej mierze praca dokumentacyjna/prawna, nie kod;
      część do zrobienia razem z Tobą (deklaracje sklepowe wymagają decyzji
      biznesowych, nie tylko technicznych). **Brakujący element (Codex):**
      "Przegląd bezpieczeństwa" jak dotąd opisany to wyłącznie inwentaryzacje
      i deklaracje prawne — §64 Master Planu (Security Baseline) wymaga też
      konkretnych kontroli technicznych: payload limits, CORS, security
      headers, firewall, osobne credentials, Docker hardening,
      dependency updates. Żaden task w kolejce (tu ani w Phase 15) tego
      nie implementuje/weryfikuje. **Korekta (Codex, runda 5) — poprzednia
      wersja tworzyła cykl zależności:** wymaganie "remediacji i weryfikacji
      całej listy z §64" jako acceptance condition TASK-14.2 jest
      niewykonalne, bo firewall/Docker hardening/osobne credentials
      wdraża dopiero realna infrastruktura w Phase 15 (`### Phase 15` —
      "wykonanie odłożone aż Phase 0-14 zamknięte"), a TASK-14.2 należy do
      Phase 14, więc nie może zależeć od pracy z fazy, która startuje
      dopiero PO jego zamknięciu. Poprawiony zakres: TASK-14.2 weryfikuje i
      wdraża tylko kontrole z §64 niewymagające produkcyjnej infrastruktury
      (payload limits, CORS, security headers, proces aktualizacji
      zależności) jako własne acceptance criteria; firewall, Docker
      hardening i osobne credentials produkcyjne zostają jawnie acceptance
      criteria TASK-15.1/15.2 (nie TASK-14.2) — TASK-14.2 kończy się
      checklistą §64 z jawnie oznaczonymi pozycjami "do TASK-15.1/15.2",
      nie próbą ich wdrożenia przed istnieniem środowiska produkcyjnego.
- [ ] **TASK-14.3:** Przegląd zgodności analytics/monitoringu z gotową
      Privacy Policy (czy eventy z TASK-13.3 i metryki z TASK-13.2 faktycznie
      odpowiadają temu, co deklaruje Privacy Policy z TASK-14.2) —
      **przeniesione tu z Phase 13** (Codex: poprzednia wersja umieszczała
      tę weryfikację przed taskiem, od którego zależy — w sekwencyjnej
      kolejce zablokowałaby się na nieistniejącej jeszcze polityce). Krótki,
      ale wymagany przed release (§71 RODO).

### Phase 15 — Production Infrastructure

Zaplanowane, wykonanie odłożone aż Phase 0-14 zamknięte (nie ma sensu
stawiać produkcyjnej infry dla appki bez pełnego MVP) — ale wypisane
jawnie, żeby kolejka faktycznie prowadziła do wydania, nie kończyła się na
placeholderze.

- [ ] **TASK-15.0:** Source Approval Gate — domknięcie wszystkich źródeł
      przed produkcją (rule #15). `source-registry.md` ma dziś realne dziury
      mimo statusu IMPLEMENTED: GIOŚ ma `commercial_use` "do potwierdzenia
      przy pełnym Source Approval Gate przed produkcją" (linia 76-77),
      Open-Meteo nigdy nie miał żywej weryfikacji kształtu JSON (linia
      18-33). TASK-6.2 dokłada GUS/TERYT/PRG (granice gmin) bez wpisu w
      registry i bez gate w ogóle. **Korekta (Codex) — poprzednia wersja
      miała lukę:** "świadomie udokumentować akceptowane ryzyko" jako
      alternatywa dla VERIFIED/APPROVED jest sprzeczna z rule #15
      (CLAUDE.md: "Przed użyciem produkcyjnym KAŻDE źródło przechodzi
      Source Approval Gate" — bez wyjątków) i z modelem statusów §37
      Master Planu (DISCOVERY→VERIFIED→APPROVED→IMPLEMENTED→PRODUCTION,
      jedyna alternatywa to BLOCKED — nie ma stanu "zaakceptowane
      ryzyko, wdrażamy mimo to"). Zakres: KAŻDE aktywne w produkcji
      źródło musi osiągnąć APPROVED/PRODUCTION w `source-registry.md`
      zanim TASK-15.2 wdroży produkcję; źródło, które tego nie osiągnie,
      zostaje wyłączone albo zastąpione — nie "wdrożone z udokumentowanym
      ryzykiem".
- [ ] **TASK-15.1:** Środowisko staging (osobne od dev/produkcji) na VPS.
- [ ] **TASK-15.2:** Środowisko produkcyjne + wdrożenie TASK-1.1 (backup
      poza VPS) i regularnego testu odtworzenia w praktyce (nie tylko kod
      skryptu — realny, zaplanowany przebieg testu). **Brakujący element
      (Codex):** §86 Master Planu wymaga konkretnego pipeline'u
      `main → staging → manual approval → production`, a repo ma dziś
      wyłącznie `.github/workflows/ci.yml` (sam CI: lint/typecheck/testy/
      build). Same TASK-15.1/15.2, jak napisane, kończą się na
      wystawieniu hostów staging/produkcji, nigdy nie tworzą workflow CD
      z bramką manual approval — bez tego nie ma powtarzalnej ścieżki
      promocji przetestowanego artefaktu na produkcję. Zakres obejmuje
      więc jawnie dodanie workflow CD (`.github/workflows/cd.yml` lub
      podobny) + wpięcie credentiali/approval gate dla produkcji, nie
      tylko provisioning maszyn.
- [ ] **TASK-15.3:** Monitoring produkcyjny (rozszerzenie TASK-13.2) na
      realnym środowisku.
- [ ] **TASK-15.4:** Redis w produkcji (§45, §103 Release Candidate
      checklist) — ADR-007 zdejmuje z Redis tylko rolę kolejki/workera dla
      schedulera ("Redis... zostaje nieużyty przez scheduler"), nie znosi
      §45 (cache/rate-limiting/short-lived state) ani pozycji "[ ] Redis" w
      §103. "Świadomie NIE w tej kolejce" (patrz sekcja niżej) odkłada
      Redis do czasu, aż load to uzasadni — to poprawny YAGNI dla fazy
      rozwoju, ale bez tego tasku żaden punkt kolejki faktycznie nie
      implementuje Redis przed Phase 18, więc checklist z §103 zostałby
      niespełniony przy release mimo ukończenia całej reszty MVP. Zakres:
      realne zastosowanie Redis (np. cache `/dashboard/latest`, rate
      limiting per-device) + walidacja produkcyjna, ALBO — jeśli po
      przeanalizowaniu przy tej skali dalej nie ma uzasadnienia — formalna
      rewizja §103 przez ADR (rule #12), nie ciche pominięcie.
- [ ] **TASK-15.5:** Release rollback readiness (§104 Master Planu) —
      możliwość wyłączenia pojedynczego connectora/kategorii alertów,
      zmiany konfiguracji i rollbacku backendu **bez rebuildu appki**
      (§104: "nie powinno być konieczności przebudowy całej aplikacji w
      przypadku awarii jednego źródła"). Bez tego pierwszy publiczny release
      nie ma bezpiecznej ścieżki wycofania złego deploya — musi być gotowe
      przed TASK-18.1/18.2, nie po.

### Phase 16 — Store Preparation

Master Plan §7/§16/§18 (source of truth): Android pierwszy release, **iOS
równolegle od momentu closed testingu Androida** — to nie jest "iOS później
jeśli będzie czas", tylko część zaplanowanej sekwencji. Poprzednia wersja
tej sekcji pokrywała tylko Androida — poprawka niżej.

- [ ] **TASK-16.1:** Konto Google Play Console (**BLOKADA: decyzja/konto
      od Ciebie** — rejestracja dewelopera to krok biznesowy/prawny, nie
      techniczny) + konfiguracja EAS build dla Androida. **Wymaga jawnej
      weryfikacji target SDK 36+ (§90 Master Planu, wymóg Google Play od
      28.09.2026)** — `app.json` dziś nie ustawia `targetSdkVersion`
      (domyślna wartość toolchaina Expo), a żaden inny task tego nie
      sprawdza; ustawić i zweryfikować przed uploadem, nie po odrzuceniu
      przez Play.
- [ ] **TASK-16.2:** Metadane, opis, ikony, screenshoty do listingu Google
      Play (zależne od TASK-16.1 i ukończonego UI).
- [ ] **TASK-16.3:** Konto Apple Developer + App Store Connect (**BLOKADA:
      decyzja/konto od Ciebie**, tak jak TASK-16.1) + konfiguracja EAS build
      dla iOS. Start równolegle z TASK-16.1/17.1 na Androidzie (Android
      closed testing), nie po zakończeniu Phase 18 dla Androida.
- [ ] **TASK-16.4:** TestFlight — build iOS do closed testingu, metadane/
      screenshoty do App Store (zależne od TASK-16.3 i ukończonego UI).
      **Brakujący element (Codex):** §99 Master Planu wymaga App Review
      Notes dla reviewera (uruchomienie, location flow, brak
      obowiązkowego konta, alerty, ograniczenia, dane testowe, ewentualne
      specjalne kroki) — dziś żaden task tego nie przygotowuje, więc
      TASK-18.2 mógłby dojść do submission bez tych informacji i dostać
      odrzucenie od Apple Review z błahego, unikalnego powodu. Dodać
      przygotowanie App Review Notes do zakresu tego tasku (albo
      osobnego tasku bezpośrednio przed TASK-18.2).
- [ ] **TASK-16.5:** Publiczna strona (§23/§102 Master Planu) — minimalny
      zakres: `/`, `/privacy`, `/terms`, `/support`, `/contact`, `/about`,
      wdrożona pod publicznym HTTPS z realnym URL-em. Treść Privacy
      Policy/Terms pochodzi z TASK-14.2, ale sam fakt istnienia strony to
      osobna praca (deploy, domena/subdomena) — **BLOKADA częściowa: jeśli
      wybierzemy dedykowaną domenę zamiast subdomeny istniejącego VPS,
      rejestracja to decyzja/koszt po Twojej stronie**, inaczej mogę to
      zrobić sam. Bez tego Google Play (Privacy Policy URL) i App Store
      Connect (Privacy + Support URL) nie przyjmą zgłoszenia — blokuje
      TASK-18.1/18.2 niezależnie od tego, czy reszta MVP jest gotowa.

### Phase 17 — Testing

- [ ] **TASK-17.1:** QA/E2E przejście przez kluczowe ścieżki (onboarding,
      dashboard, alert, push) na realnym build EAS (Android + iOS/TestFlight).
- [ ] **TASK-17.2:** Testy odporności — utrata sieci, źródło zwraca błąd/
      puste dane w trakcie działania appki (rule #1 w praktyce, nie tylko w
      testach jednostkowych connectorów).
- [ ] **TASK-17.4:** Location Test Matrix + Push Test Matrix + Network Test
      Matrix (§77-79 Master Planu) — TASK-17.1's happy-path E2E i TASK-17.2's
      network/source failures nie pokrywają tych macierzy wprost: permission
      denied/approximate/poor accuracy/changed location (§77), quiet hours/
      foreground/background/killed app/duplicate/expired event (§78), oraz
      WiFi vs. mobile/slow connection/API timeout/source timeout/partial
      backend failure (§79 — TASK-17.2 pokrywa tylko offline/błąd źródła/
      puste dane, nie te sześć przypadków). To platform-specific przypadki,
      które mogą zawieść mimo ukończenia TASK-17.1/17.2 — osobny, jawny
      przebieg przed release.
- [ ] **TASK-17.3:** Google Play closed testing (§88-89 Master Planu) —
      konto Personal (decyzja v1.2) wymaga **min. 12 testerów przez min. 14
      kolejnych dni na torze closed** przed dostępem do produkcji — tor
      internal NIE spełnia tego wymogu (§89), więc może zużyć 14 dni i nadal
      zostawić TASK-18.1 zablokowany. Zakres: upload builda konkretnie na
      **closed track** (internal zostaje ewentualnym wcześniejszym smoke-
      testem, nie substytutem), rekrutacja ≥12 testerów (może wymagać Twojej
      pomocy — sieć znajomych/beta testerów), **odczekanie 14 dni** zanim
      TASK-18.1 w ogóle będzie możliwe. To realny czas kalendarzowy, nie coś
      do przyspieszenia pracą — warto uruchomić ten track jak najwcześniej
      równolegle z TASK-17.1/17.2, nie czekać aż wszystko inne będzie gotowe.

### Phase 18 — Public Release

- [ ] **TASK-18.1:** Publikacja w Google Play (zależne od Phase 14
      Security/Privacy + Phase 16 Store Prep + Phase 17 Testing, **w tym
      ukończonego 14-dniowego closed testu z TASK-17.3** — bez tego Google
      Play nie da dostępu do produkcji niezależnie od stanu reszty MVP).
- [ ] **TASK-18.2:** Publikacja w App Store po zakończonym TestFlight
      (zależne od TASK-16.3/16.4 + Phase 14 + Phase 17).

### Phase 19 — Operations

- [ ] **TASK-19.1:** Rutyna utrzymania connectorów (co sprawdzać, jak
      często, kto reaguje na źródło, które zmieniło kształt odpowiedzi).
- [ ] **TASK-19.2:** Proces incident response (co robimy, gdy źródło padnie
      na dłużej niż freshness threshold pozwala, gdy backup/restore zawiedzie
      na realnym incydencie).

Rewizja kolejności lub zakresu Phase 15-19 możliwa, jeśli zdecydujesz
inaczej — powyższe to pierwsza konkretna wersja, nie coś zamkniętego.

---

## Świadomie NIE w tej kolejce (bez zmiany decyzji użytkownika)

Uwaga: to jest lista rzeczy świadomie odłożonych z uzasadnieniem — nie należy
tego mylić ze statusem "zrobione" dla Phase 0-4 wyżej.

- **Redis (cache)** — obecnie wszystko czyta z PostgreSQL bezpośrednio i to
  wystarcza przy obecnej skali w trakcie developmentu (ta sama logika co
  decyzja o braku workerów w ADR-007). To NIE jest jednak odłożone bez
  terminu: §103 Release Candidate checklist wymaga Redis przed release, więc
  TASK-15.4 (Phase 15) implementuje go (albo formalnie rewiduje §103 przez
  ADR) przed TASK-18.1/18.2 — dopóki to nie nastąpi, brak Redis tutaj nie
  jest zamkniętym tematem, tylko świadomie odłożonym do tego taska.
- **PostGIS** — obecny haversine (ADR-006) wystarcza przy 7 zaseedowanych
  lokalizacjach; pełny PostGIS dopiero gdy TERYT/Geo Engine (Phase 6) tego
  faktycznie zażąda.
- **Workers (kolejka zadań)** — dziś ingest to skrypty CLI uruchamiane
  manualnie/przez prosty scheduler (ADR-007: brak workerów, bo skala tego
  nie wymaga). Realna kolejka (Celery/RQ/coś podobnego) dopiero gdy liczba
  connectorów/częstotliwość fetchowania realnie tego zażąda — nie jest to
  "zrobione" w Phase 0-4, tylko świadomie pominięte na razie, tak jak Redis.
  **Konkretny trigger do rewizji (Codex):** `scheduler.py` jest jednowątkowy
  i sekwencyjny — `main()` czeka na pełne zakończenie `run_open_meteo()`
  (synchroniczny request per gmina) zanim sprawdzi, czy `run_imgw_warningshydro`
  (bezpieczeństwo — ostrzeżenia) jest już due w tej samej iteracji. TASK-6.2
  planuje pełny import TERYT (~2.5k gmin) z pollingiem pogody ograniczonym do
  "aktywnych" gmin (punkt 4) — jeśli ten zbiór urośnie do setek/tysięcy, spowolnienie
  Open-Meteo może opóźniać odświeżanie ostrzeżeń o godziny. Rewizja tego non-goalu
  (bounded concurrency, osobny proces dla warningshydro, albo jawna bramka
  wydajnościowa przed release) jest więc częścią TASK-6.2/Phase 15, nie
  nieokreślonym "kiedyś" — nie zamykać Phase 15 bez tego sprawdzenia.
- **Monitoring/alerting produkcyjny poza `logging`** — patrz TASK-13.2
  (Phase 13), świadomie odłożone do momentu, gdy aplikacja ma realny ruch
  produkcyjny do monitorowania; do tego czasu structured `logging` +
  ręczne sprawdzanie wystarcza.
- **Backup bazy danych** — nie skonfigurowany. To NIE jest świadomy,
  uzasadniony YAGNI-non-goal jak powyższe (utrata danych to realne ryzyko od
  pierwszego dnia produkcji, nie kwestia skali) — brakujący element Phase 1
  (Foundation/infra), patrz **TASK-1.1** poniżej; do zrobienia przed
  jakimkolwiek realnym wdrożeniem produkcyjnym, nie odkładane celowo.
- Wszystko z sekcji "Poza MVP" w ROADMAP.md (mapa, Green Index, background
  location, obowiązkowe konto, PWA, monetyzacja) — bez zmiany decyzji
  użytkownika + ADR.
