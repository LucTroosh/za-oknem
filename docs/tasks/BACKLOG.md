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

- [ ] **TASK-1.1:** Backup PostgreSQL (VPS, Docker) — `pg_dump` cykliczny
      (cron w kontenerze lub na hoście), **przechowywany POZA VPS** (§68
      Master Planu — lokalna kopia na tym samym serwerze nie liczy się jako
      backup, bo utrata VPS niszczy oba egzemplarze naraz; np. wysyłka do
      S3-kompatybilnego storage lub innego hosta), retencja, oraz
      **regularny automatyczny test odtworzenia** (nie tylko udokumentowana
      procedura — §68: "sam backup bez testu odtworzenia nie jest
      wystarczający"). Priorytet przed jakimkolwiek wdrożeniem
      produkcyjnym, nawet jeśli reszta MVP jeszcze nie gotowa.

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

- [ ] **TASK-6.1:** TERYT-based geo model (§26-27). **Druga korekta tego
      tasku** (Codex, runda 2): pierwsza korekta ograniczyła zakres do
      mapowania TERYT tylko dla 7 zaseedowanych miast — to za mało. ADR-005
      (Accepted) explicité przypisuje do Phase 6: pełny import listy gmin z
      TERYT (nie tylko 7 miast) ORAZ dopasowanie dowolnych współrzędnych
      użytkownika → najbliższa gmina (nearest-station/point-in-polygon) —
      to jest właśnie "migracja z seeda do pełnego Geo Engine", o której
      mówi ADR-005. Ograniczenie do 7 miast zostawiłoby TASK-12.3 (foreground
      location) bez możliwości rozpoznania użytkownika gdziekolwiek indziej
      w Polsce, co jest sprzeczne z celem MVP. Realny zakres TASK-6.1: (1)
      pełny import gmin TERYT do `geo_areas` (kolumna TERYT + dane
      geograficzne, np. z GUS/TERYT XML/CSV), (2) point-in-polygon lub
      nearest-gmina matching dla dowolnych lat/lon, (3) `geo_area_id` jako
      wspólny klucz dla Alert Engine (Phase 9) i Push (Phase 10, ADR-002).
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
      stacji).
- [ ] **TASK-7.2:** Dodać sekcje hydro (`/hydro/latest`) i alerty
      (`/alerts/latest`) do dashboardu mobile — backend już gotowy, czysto
      frontendowa robota.
- [ ] **TASK-7.5:** Osobny ekran "Alerty" (mobile) — dziś alerty (o ile
      TASK-7.2 je w ogóle doda) są co najwyżej sekcją dashboardu; potrzebny
      dedykowany ekran z pełną listą, szczegółem alertu (treść źródłowa,
      timestamp, źródło — rule #10: LLM nigdy nie jest źródłem prawdy dla
      alertów, więc pokazujemy oryginalny tekst, nie streszczenie). Zależny
      od TASK-9.5 (geo-matching), inaczej pokazujemy wszystko bez filtrowania
      lokalizacją.
- [ ] **TASK-7.3:** Stany stale/no-data w UI (obecnie tylko
      loading/error/ready) — §59/§80 Master Planu.
- [ ] **TASK-7.4:** Source-level freshness (UNAVAILABLE: pusta lista =
      potwierdzone zero czy dawno nie było fetcha) — dotyczy `/air`,
      `/hydro`, `/alerts`, `/weather` razem. Wymaga własnego ADR-012
      (świadomy non-goal z ADR-009, teraz adresowany).

### Phase 8 — Pollen

- [ ] **TASK-8.1:** Source Approval Gate dla `cams` (Copernicus ADS) —
      **BLOKADA: potrzebny klucz API od Ciebie**, patrz sekcja blokad wyżej.
      Do tego czasu: przygotować kontrakt connectora (client/parser/normalize)
      pod znany format CAMS bez możliwości żywej weryfikacji, zaznaczyć
      jawnie w source-registry jako DISCOVERY→VERIFIED dopiero po realnym
      dostępie (rule #10/#15 — nie zgadywać kształtu).
- [ ] **TASK-8.2:** Model `PollenSnapshot` (ADR-001 opcja C — snapshot per
      gmina, jak weather) + migracja Alembic + ingest — dopiero po
      TASK-8.1, wymaga działającego klucza CAMS.
- [ ] **TASK-8.3:** `GET /api/v1/pollen/latest` (freshness, grupowanie per
      geo_area, ten sam wzorzec co `/weather/latest`) — czyta wyłącznie z
      naszej bazy (rule #14).
- [ ] **TASK-8.4:** Karta pyłkowa na mobile dashboard (§Phase 8 Master
      Planu: "pollen card") — bez tego Phase 8 nie dostarcza niczego
      użytkownikowi mimo działającego backendu. Profil alergika (który
      pyłki są dla mnie istotne) to już TASK-12.4, nie duplikować tu.

### Phase 9 — Alerts (dokończenie)

- [ ] **TASK-9.4:** `Event` model (§31) — odrębny od `Alert`/`Measurement`
      (rule #7). Potrzebny do "istotne lokalne zagrożenia / zweryfikowane
      zdarzenia" z ROADMAP §2.6. Wymaga ADR-013 (nowy typ danych).
- [ ] **TASK-9.5:** Geo-matching alertów → lokalizacja (zależne od
      TASK-6.1) — dziś `/alerts/latest` zwraca WSZYSTKO, bez filtrowania.
- [ ] **TASK-9.6:** Alert Engine (§47) — severity, deduplication, geo
      relevance, na bazie modeli `Alert`+`Event`+geo-matching z powyższych
      tasków. Duży task, prawdopodobnie do rozbicia na 2-3 mniejsze PR.
- [ ] Ostrzeżenia meteo (TASK-9.2) — pozostaje BLOCKED, sprawdzane przy
      okazji (patrz sekcja blokad).

### Phase 10 — Push

- [ ] **TASK-10.1:** Device registration + push tokens (Expo) —
      **BLOKADA: klucze FCM/APNs od Ciebie**, patrz sekcja blokad wyżej.
      Przygotuję backend (model tokenu, endpoint rejestracji) niezależnie od
      blokady, bo to nie wymaga kluczy zewnętrznych.
- [ ] **TASK-10.2:** Notification Engine + anti-spam (zależne od Alert
      Engine z Phase 9 i tokenów z TASK-10.1).

### Phase 11 — Water / Hydrology (dokończenie)

- [ ] **TASK-11.1:** Research + Source Approval Gate dla kąpielisk
      (Sanepid/GIS) — zobacz blokadę wyżej, może wymagać zbadania
      `sk.gis.gov.pl` przez przeglądarkę zamiast dokumentacji API.
- [ ] **TASK-11.2:** Connector `bathing_water` (o ile TASK-11.1 znajdzie
      stabilne źródło) — status kąpieliska, przyczyna zamknięcia, sezon,
      E. coli/enterokoki/sinice, daty badań.
- [ ] **TASK-11.3:** "Zamknięcia kąpielisk" jako Alert/Event (zależne od
      TASK-11.2 + modeli z Phase 9).

### Phase 12 — Settings / Profiles

- [ ] **TASK-12.1:** Ekran Settings (mobile) — placeholder/skeleton, potem
      realne preferencje.
- [ ] **TASK-12.2:** Ręczny wybór lokalizacji (mobile) — rozszerzenie
      obecnej statycznej listy 7 miast o wybór przez użytkownika (bez
      background location — rule #11).
- [ ] **TASK-12.3:** Foreground location (device geolocation, jednorazowe
      żądanie, minimalne uprawnienia — rule #8/§8 Master Planu Principle 8).
- [ ] **TASK-12.4:** Profil użytkownika + podstawowe preferencje (allergy,
      family, outdoor — §12 Master Planu). Bez obowiązkowego konta (rule #11)
      — do przemyślenia jak to pogodzić z "profilem" w MVP bez logowania
      (prawdopodobnie: lokalny profil per-urządzenie, nie serwerowe konto).

### Phase 13 — Data Quality / Observability

- [ ] **TASK-13.1:** Source health / stale monitoring — rozszerzenie
      istniejącego per-wiersz freshness o widoczny status źródła
      (przydatne razem z TASK-7.4).
- [ ] **TASK-13.2:** Podstawowe monitoring/alerting (Sentry czy
      odpowiednik) — do decyzji, czy to wymaga zewnętrznego konta (Sentry)
      czy wystarczy rozszerzenie istniejącego `logging`.

### Phase 14 — Security / Privacy

- [ ] **TASK-14.1:** Przegląd bezpieczeństwa, RODO, Privacy Policy, Data
      Safety / App Privacy — w dużej mierze praca dokumentacyjna/prawna,
      nie kod; część do zrobienia razem z Tobą (deklaracje sklepowe wymagają
      decyzji biznesowych, nie tylko technicznych).

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

### Phase 16 — Store Preparation

- [ ] **TASK-16.1:** Konto Google Play Console (**BLOKADA: decyzja/konto
      od Ciebie** — rejestracja dewelopera to krok biznesowy/prawny, nie
      techniczny) + konfiguracja EAS build dla Androida.
- [ ] **TASK-16.2:** Metadane, opis, ikony, screenshoty do listingu Google
      Play (zależne od TASK-16.1 i ukończonego UI).

### Phase 17 — Testing

- [ ] **TASK-17.1:** QA/E2E przejście przez kluczowe ścieżki (onboarding,
      dashboard, alert, push) na realnym build EAS.
- [ ] **TASK-17.2:** Testy odporności — utrata sieci, źródło zwraca błąd/
      puste dane w trakcie działania appki (rule #1 w praktyce, nie tylko w
      testach jednostkowych connectorów).

### Phase 18 — Public Release

- [ ] **TASK-18.1:** Publikacja w Google Play (zależne od Phase 14
      Security/Privacy + Phase 16 Store Prep + Phase 17 Testing).

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
