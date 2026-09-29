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
      produkcyjnym, nawet jeśli reszta MVP jeszcze nie gotowa.

### Phase 2 — Backend Core (dokończenie)

- [ ] **TASK-2.1:** Generowany klient TypeScript z OpenAPI (§17 Master Planu)
      — `packages/api-contract/README.md` jest wciąż placeholderem, a
      `apps/mobile/app/index.tsx` ręcznie typuje odpowiedź dashboardu
      (potwierdzone w kodzie). Ta kolejka dokłada sporo nowych endpointów/pól
      (`/weather/forecast`, `/pollen/latest`, `/water/latest`, rozszerzenia
      `dashboard_latest()`) — bez generowanego klienta ręczne typy będą się
      cicho rozjeżdżać z realnym schematem FastAPI. Zrobić to **teraz**, przed
      dalszym rozszerzaniem integracji mobile (TASK-7.2 i kolejne), żeby nie
      duplikować pracy ręcznego przepisywania typów.

### Phase 3 — Data Architecture (dokończenie)

- [ ] **TASK-3.1:** Raw ingestion / provenance (§33-34 Master Planu) — dziś
      connectory zapisują tylko znormalizowane rekordy (`Measurement`/
      `WeatherSnapshot`/`Forecast`), nie ma modelu `source_fetches` ani
      przechowania surowego payloadu (potwierdzone: brak `source_fetch`/
      `raw_payload` w kodzie). Bez tego nie da się odpowiedzieć na pytanie
      "co dokładnie zwróciło źródło w momencie zapisu tej wartości?" (§33) —
      istotne przy sporze o poprawność danych czy debugowaniu zmiany kształtu
      API źródła. Zakres: model `source_fetches` (źródło, endpoint, surowy
      payload, timestamp pobrania) + migracja + integracja z każdym
      connectorem (zapis raw payloadu obok normalize) + polityka retencji
      (§33: 7-30 dni, zależnie od źródła). Wymaga ADR (nowy typ
      danych/tabeli w modelu, rule #12).

### Phase 4 — Air (dokończenie)

- [ ] **TASK-4.1:** Pełny zestaw parametrów GIOŚ — dziś connector `gios`
      zaciąga wyłącznie PM2.5 (świadomy zakres vertical slice, §108 Master
      Planu). Rozszerzyć `parser.py`/`ingest.py` o PM10, NO2, SO2, O3, CO,
      C6H6 (te same sensory API GIOŚ, ten sam kontrakt fetch/parse/validate/
      normalize — rozszerzenie istniejącego connectora, nie nowy).
- [ ] **TASK-4.2:** Indeks jakości powietrza (AQI/CAQI wg metodologii GIOŚ) —
      zależny od TASK-4.1 (part potrzebuje >1 parametru). Do ustalenia: czy
      liczymy indeks sami wg opublikowanej metodologii GIOŚ, czy GIOŚ
      publikuje gotowy indeks per stacja do odczytania wprost (rule #10:
      jeśli liczymy sami, to nie jest to LLM ani zgadywanie — jawny,
      testowalny algorytm).

### Phase 5 — Weather (dokończenie)

- [ ] **TASK-5.3:** Forecast (§30 Master Planu) — nowy model `Forecast`
      (odrębny od `Measurement`, rule #7: `forecast_reference_time`,
      `valid_from`, `valid_until`, `model`, `source`), rozszerzenie
      `open_meteo` connectora o zapytanie `hourly`/`daily` obok `current`,
      `GET /api/v1/weather/forecast`. Wymaga ADR-010 (nowy typ danych w
      modelu, precedens: ADR-008 dla Measurement, ADR-009 dla Alert).
- [ ] **TASK-5.4:** Rozszerzyć `current`/`daily` o dew point, visibility, UV
      index — Open-Meteo je udostępnia w tym samym zapytaniu (`dew_point_2m`,
      `visibility`, `uv_index`/`uv_index_max`), brak dodatkowego round-tripu.
      Rozszerzenie `PARAM_CODES`/`FORECAST_PARAM_CODES` w connectorze, bez
      zmiany modelu (te same tabele `WeatherSnapshot`/`Forecast`).

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
      przyjętego ADR).

### Phase 7 — Dashboard (dokończenie)

- [ ] **TASK-7.1:** Source transparency na mobile — **korekta względem
      wcześniejszej wersji:** samo wyrenderowanie `station_name` nie
      wystarczy (a) bo weather w ogóle nie jest station-based (`geo_area`,
      nie stacja — nie ma czego tu renderować jako "nazwę stacji"), (b) bo
      `GET /api/v1/dashboard/latest` dziś nie zwraca w ogóle identyfikatora
      źródła dla `weather` (`air` ma `station_name`, ale ani jeden blok nie
      ma pełnego tekstu atrybucji). Realny zakres: dodać do
      `dashboard_latest()` pole `source` (id źródła) + `attribution` (pełny
      tekst z `source-registry.md`, dosłownie — np. "Weather data by
      Open-Meteo.com (CC BY 4.0)", "Dane: Główny Inspektorat Ochrony
      Środowiska (GIOŚ)") w obu blokach (`air`, `weather`), potem dopiero
      ekran mobile renderujący te dwa pola per sekcja (nie tylko nazwę
      stacji). **Wzorzec obowiązuje dla każdej kolejnej sekcji danych** —
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
      czyta z agregatu. Hydrologia (`/api/v1/hydrology`, §8) nie jest
      wymieniona w §55 jako część agregatu — zostaje osobnym fetchem na
      mobile, czysto frontendowa robota. Wzorzec `source`/`attribution` z
      TASK-7.1 (IMGW) dotyczy obu.
- [ ] **TASK-7.3:** Stany stale/no-data w UI (obecnie tylko
      loading/error/ready) — §59/§80 Master Planu.
- [ ] **TASK-7.4:** Source-level freshness (UNAVAILABLE: pusta lista =
      potwierdzone zero czy dawno nie było fetcha) — dotyczy `/air`,
      `/hydro`, `/alerts`, `/weather` razem. Wymaga własnego ADR-012
      (świadomy non-goal z ADR-009, teraz adresowany).
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
      TASK-8.5, wymaga działającego klucza CAMS.
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
      zdarzenia" z ROADMAP §2.6. Wymaga ADR-013 (nowy typ danych).
- [ ] **TASK-9.5:** Geo-matching alertów → lokalizacja (zależne od
      TASK-6.2) — dziś `/alerts/latest` zwraca WSZYSTKO, bez filtrowania.
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
      (TASK-9.5).
- [ ] Ostrzeżenia meteo (TASK-9.2) — pozostaje BLOCKED, sprawdzane przy
      okazji (patrz sekcja blokad).

### Phase 10 — Push

- [ ] **TASK-10.1:** Device registration + push tokens (Expo) —
      **BLOKADA: klucze FCM/APNs od Ciebie**, patrz sekcja blokad wyżej.
      Przygotuję backend (model tokenu, endpoint rejestracji) niezależnie od
      blokady, bo to nie wymaga kluczy zewnętrznych.
- [ ] **TASK-10.2:** Notification Engine + anti-spam (zależne od Alert
      Engine z Phase 9 i tokenów z TASK-10.1).
- [ ] **TASK-10.3:** Preferencje powiadomień (mobile) — użytkownik wybiera,
      jakie kategorie alertów/dla jakich lokalizacji dostaje push (§Phase 10
      Master Planu: "notification preferences"). Bez tego TASK-10.2 wysyła
      wszystko do wszystkich zarejestrowanych urządzeń, co narusza ideę
      geo-relevance z Phase 9.
- [ ] **TASK-10.4:** Deep links z powiadomienia do konkretnego
      alertu/ekranu w appce (§Phase 10 Master Planu: "deep links"). Zależne
      od TASK-9.7 (ekran Alerty, żeby było dokąd linkować).

### Phase 11 — Water / Hydrology (dokończenie)

- [ ] **TASK-11.1:** Research + Source Approval Gate dla kąpielisk
      (Sanepid/GIS) — zobacz blokadę wyżej, może wymagać zbadania
      `sk.gis.gov.pl` przez przeglądarkę zamiast dokumentacji API.
- [ ] **TASK-11.2:** Connector `bathing_water` (o ile TASK-11.1 znajdzie
      stabilne źródło) — status kąpieliska, przyczyna zamknięcia, sezon,
      E. coli/enterokoki/sinice, daty badań.
- [ ] **TASK-11.3:** "Zamknięcia kąpielisk" jako Alert/Event (zależne od
      TASK-11.2 + modeli z Phase 9).
- [ ] **TASK-11.4:** `GET /api/v1/water/latest` — status kąpieliska,
      przyczyna zamknięcia, sezon, wyniki badań, daty (Master Plan MVP:
      `/api/v1/water`) — czyta wyłącznie z naszej bazy (rule #14). Bez tego
      TASK-11.2/11.3 zbierają dane, których użytkownik nigdy nie zobaczy
      poza samym faktem zamknięcia jako alertu.
- [ ] **TASK-11.5:** Sekcja kąpielisk na mobile (status, badania, sezon) —
      dopiero po TASK-11.4. Wzorzec `source`/`attribution` z TASK-7.1
      (Sanepid/GIS) dotyczy też tej sekcji.
- [ ] **TASK-11.6:** Dodać `water` do `dashboard_latest()` (§55 — water to
      część głównego agregatu). Zależne od TASK-11.4 (endpoint/dane muszą
      istnieć) — **przeniesione tu z Phase 7** (ten sam powód co TASK-8.9).

### Phase 12 — Settings / Profiles

- [ ] **TASK-12.1:** Ekran Settings (mobile) — placeholder/skeleton, potem
      realne preferencje.
- [ ] **TASK-12.2:** Ręczny wybór lokalizacji (mobile) — rozszerzenie
      obecnej statycznej listy 7 miast o wybór przez użytkownika (bez
      background location — rule #11).
- [ ] **TASK-12.3:** Foreground location (device geolocation, jednorazowe
      żądanie, minimalne uprawnienia — rule #8/§8 Master Planu Principle 8).
- [ ] **TASK-12.5:** Wysyłka `observed_area_code` do `POST /api/v1/devices`
      przy każdym otwarciu appki z aktywną lokalizacją (foreground) i przy
      ręcznej zmianie lokalizacji w Settings (ADR-002, sekcja Decision) —
      **brakujące wcześniej**: TASK-12.2/12.3 tylko pobierają/wybierają
      lokalizację, TASK-10.1 tylko przygotowuje backend; bez tego klienckiego
      wpięcia zarejestrowane urządzenie ma nieaktualny lub brak
      `observed_area_code`, więc push trafia do złej gminy albo wcale.
      Zależne od TASK-10.1 (endpoint musi istnieć) i TASK-12.2/12.3 (skąd
      wziąć lokalizację).
- [ ] **TASK-12.4:** Profil użytkownika + podstawowe preferencje (allergy,
      family, outdoor — §12 Master Planu). Bez obowiązkowego konta (rule #11)
      — do przemyślenia jak to pogodzić z "profilem" w MVP bez logowania
      (prawdopodobnie: lokalny profil per-urządzenie, nie serwerowe konto).
      "outdoor" tu to tylko przechowana preferencja (czy ta osoba w ogóle
      chce widzieć `OutdoorCard`) — sam silnik interpretacji to TASK-7.6/
      7.7/7.8 (Phase 7), nie duplikować logiki tutaj.

### Phase 13 — Data Quality / Observability

- [ ] **TASK-13.1:** Source health / stale monitoring — rozszerzenie
      istniejącego per-wiersz freshness o widoczny status źródła
      (przydatne razem z TASK-7.4).
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
      Safety / App Privacy — oparte na TASK-14.1 (SDK inventory); w dużej
      mierze praca dokumentacyjna/prawna, nie kod; część do zrobienia razem
      z Tobą (deklaracje sklepowe wymagają decyzji biznesowych, nie tylko
      technicznych).
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

- [ ] **TASK-15.1:** Środowisko staging (osobne od dev/produkcji) na VPS.
- [ ] **TASK-15.2:** Środowisko produkcyjne + wdrożenie TASK-1.1 (backup
      poza VPS) i regularnego testu odtworzenia w praktyce (nie tylko kod
      skryptu — realny, zaplanowany przebieg testu).
- [ ] **TASK-15.3:** Monitoring produkcyjny (rozszerzenie TASK-13.2) na
      realnym środowisku.
- [ ] **TASK-15.4:** Release rollback readiness (§104 Master Planu) —
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
      techniczny) + konfiguracja EAS build dla Androida.
- [ ] **TASK-16.2:** Metadane, opis, ikony, screenshoty do listingu Google
      Play (zależne od TASK-16.1 i ukończonego UI).
- [ ] **TASK-16.3:** Konto Apple Developer + App Store Connect (**BLOKADA:
      decyzja/konto od Ciebie**, tak jak TASK-16.1) + konfiguracja EAS build
      dla iOS. Start równolegle z TASK-16.1/17.1 na Androidzie (Android
      closed testing), nie po zakończeniu Phase 18 dla Androida.
- [ ] **TASK-16.4:** TestFlight — build iOS do closed testingu, metadane/
      screenshoty do App Store (zależne od TASK-16.3 i ukończonego UI).
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
- [ ] **TASK-17.3:** Google Play closed testing (§88-89 Master Planu) —
      konto Personal (decyzja v1.2) wymaga **min. 12 testerów przez min. 14
      kolejnych dni** przed dostępem do produkcji. Zakres: upload builda na
      closed/internal track, rekrutacja ≥12 testerów (może wymagać Twojej
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
  wystarcza przy obecnej skali (ta sama logika co decyzja o braku workerów w
  ADR-007). Dodać dopiero gdy realny load to uzasadni, nie "na wszelki
  wypadek" (YAGNI).
- **PostGIS** — obecny haversine (ADR-006) wystarcza przy 7 zaseedowanych
  lokalizacjach; pełny PostGIS dopiero gdy TERYT/Geo Engine (Phase 6) tego
  faktycznie zażąda.
- **Workers (kolejka zadań)** — dziś ingest to skrypty CLI uruchamiane
  manualnie/przez prosty scheduler (ADR-007: brak workerów, bo skala tego
  nie wymaga). Realna kolejka (Celery/RQ/coś podobnego) dopiero gdy liczba
  connectorów/częstotliwość fetchowania realnie tego zażąda — nie jest to
  "zrobione" w Phase 0-4, tylko świadomie pominięte na razie, tak jak Redis.
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
