# Backlog — kolejność realizacji do końca MVP

**Cel tego pliku:** jedna, uporządkowana lista tego, co zostało do zrobienia,
żeby nie skakać po tematach (decyzja użytkownika, 2026-09-29). Kolejność =
numeracja PHASE z `Development-Master-Plan-v1.2.md` (sekcja 2640+) — to już
jest przemyślana sekwencja zależności (np. Geo Engine przed geo-relevance
alertów), nie coś wymyślonego na nowo tutaj. W obrębie fazy: najpierw to, co
odblokowuje kolejne fazy i nie ma zewnętrznych zależności poza naszą kontrolą.

Status faz 0-4 (Foundation → pierwszy vertical slice): ✅ DONE, patrz ROADMAP.md.

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

### Phase 5 — Weather (dokończenie)

- [ ] **TASK-5.3:** Forecast (§30 Master Planu) — nowy model `Forecast`
      (odrębny od `Measurement`, rule #7: `forecast_reference_time`,
      `valid_from`, `valid_until`, `model`, `source`), rozszerzenie
      `open_meteo` connectora o zapytanie `hourly`/`daily` obok `current`,
      `GET /api/v1/weather/forecast`. Wymaga ADR-010 (nowy typ danych w
      modelu, precedens: ADR-008 dla Measurement, ADR-009 dla Alert).

### Phase 6 — Geo Engine

- [ ] **TASK-6.1:** TERYT-based geo model (§26-27) — decyzja: pełny TERYT
      teraz czy rozszerzenie obecnej nearest-station/statycznej listy
      (ADR-006) o proste dopasowanie województwa dla potrzeb Phase 9
      (geo-relevance alertów)? Rekomendacja: zacząć od najmniejszego
      rozszerzenia, które odblokowuje Phase 9 (mapowanie
      lokalizacja→województwo dla 7 zaseedowanych miast, bez pełnego TERYT),
      pełny Geo Engine dopiero gdy realnie potrzebny (YAGNI, zgodnie z
      ADR-006's dotychczasową filozofią). Wymaga ADR-011 jeśli rozszerzamy
      poza obecny zakres ADR-006.

### Phase 7 — Dashboard (dokończenie)

- [ ] **TASK-7.1:** Source transparency na mobile — wyrenderować
      `station_name`/źródło na ekranie (obecnie zbierane, ale nie
      pokazywane — zgodność z wymogiem atrybucji licencyjnej z
      source-registry.md, nie tylko UX).
- [ ] **TASK-7.2:** Dodać sekcje hydro (`/hydro/latest`) i alerty
      (`/alerts/latest`) do dashboardu mobile — backend już gotowy, czysto
      frontendowa robota.
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

### Phase 15+ — Production Infra / Store / Release / Operations

Odłożone do momentu, gdy Phase 0-14 są zamknięte — nie ma sensu stawiać
produkcyjnej infrastruktury czy przygotowywać store listingu dla appki,
która nie ma jeszcze pełnego MVP. Rewizja kolejności możliwa, jeśli
zdecydujesz inaczej.

---

## Świadomie NIE w tej kolejce (bez zmiany decyzji użytkownika)

- Redis (cache) — obecnie wszystko czyta z PostgreSQL bezpośrednio i to
  wystarcza przy obecnej skali (ta sama logika co decyzja o braku workerów w
  ADR-007). Dodać dopiero gdy realny load to uzasadni, nie "na wszelki
  wypadek" (YAGNI, ponytail).
- PostGIS — obecny haversine (ADR-006) wystarcza przy 7 zaseedowanych
  lokalizacjach; pełny PostGIS dopiero gdy TERYT/Geo Engine (Phase 6) tego
  faktycznie zażąda.
- Wszystko z sekcji "Poza MVP" w ROADMAP.md (mapa, Green Index, background
  location, obowiązkowe konto, PWA, monetyzacja) — bez zmiany decyzji
  użytkownika + ADR.
