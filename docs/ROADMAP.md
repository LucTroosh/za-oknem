# Za Oknem — Roadmap

**Ten plik odzwierciedla stan faktyczny kodu, nie plany.** Aktualizowany po
każdym zmergowanym PR (patrz przypis na końcu). Źródło wizji produktowej:
[`Development-Master-Plan-v1.2.md`](architecture/Development-Master-Plan-v1.2.md)
(§4–§11). Status źródeł danych ze szczegółami (licencja, rate limit,
attribution): [`source-registry.md`](data/source-registry.md).

**Ostatnia aktualizacja:** 2026-10-01 (po PR #83; stan main = f6d7ece)

Legenda: ✅ DONE · 🟡 PARTIAL (częściowo, mniej niż pełny zakres MVP) ·
⛔ BLOCKED (zatrzymane na konkretnym warunku) · ⬜ TODO (nie zaczęte)

---

## 1. Gdzie jesteśmy (jednym zdaniem)

Pierwszy cel z CLAUDE.md — **Vertical Slice: GIOŚ → Connector → PostgreSQL →
FastAPI → React Native → PM2.5 na ekranie** — jest zrobiony i rozszerzony o
kolejne źródła (pogoda, poziom wody, ostrzeżenia hydrologiczne) i warstwy
pochodne (EAQI, outdoor). Backend ma też pyłki (CAMS Europe przez Open-Meteo, bez
karty mobile i bez agregatu), fundament Geo Engine (PostGIS + resolver, **bez
załadowanych granic gmin**), rejestrację urządzeń pod push (bez kluczy FCM/APNs)
i `GET /api/v1/health/sources`. Nie jesteśmy jeszcze przy pełnym zakresie danych
z §4 Master Planu (kąpieliska: tylko research i ADR-021, źródło ZABLOKOWANE — patrz
2.4 i sekcja 6) ani przy pełnym MVP mobile (tylko jeden ekran, bez
Alerts/Settings/push/profilu).

---

## 2. Dane / metryki — zakres z Master Planu §4-9 vs stan faktyczny

### 2.1. Powietrze (§4.1)

| Metryka (MVP wg Master Planu) | Status |
|---|---|
| PM2.5, PM10, NO2, SO2, O3, CO, C6H6 | ✅ DONE — GIOŚ, pełny zestaw parametrów MVP (TASK-4.1, PR #48), `GET /api/v1/air/latest`, w dashboardzie |
| indeks jakości powietrza + indeksy cząstkowe | ✅ DONE — **Europejski Indeks Jakości Powietrza (EAQI, EEA)**, nie natywny indeks GIOŚ: `app/air_index.py` (progi EEA zweryfikowane 2026-09-30, najgorszy z cząstkowych, minimalny zestaw, STALE/inna jednostka = brak), pole `index` w `/air/latest` i w bloku `air` dashboardu, mobile `AirIndexBadge` (TASK-4.2, ADR-015, PR #63). Opcja A (gotowy indeks GIOŚ `aqindex/getIndex`) pozostaje odłożona. Nasze decyzje poza specyfikacją EEA (granice dla wartości ułamkowych, typ stacji, polskie nazwy pasm) w ADR-015 |
| Sensor.Community, CAMS Air (MVP+) | ⬜ TODO (poza MVP na razie) |

### 2.2. Pogoda (§5)

| Metryka (MVP wg Master Planu) | Status |
|---|---|
| temperatura, wilgotność, wiatr (prędkość+kierunek+porywy), kod warunków, odczuwalna, ciśnienie, zachmurzenie, opady/deszcz/śnieg | ✅ DONE — Open-Meteo, `GET /api/v1/weather/latest` + dashboard (12/15 pól MVP, PR #41); na mobile `WeatherCard` pokazuje wszystkie zwracane pola z jednostkami (TASK-5.4, PR #78) |
| punkt rosy, widoczność, UV | ✅ DONE — Open-Meteo `hourly` (osobny fetch nie był potrzebny, jeden request z `current`+`hourly`+`daily`), dopasowanie do godziny `current` w parserze (TASK-5.4) |
| prognoza (forecast, nie tylko current) | ✅ DONE — model `Forecast` (§30, ADR-010), `GET /api/v1/weather/forecast`, dzienna prognoza (temp max/min, opady, kod pogody) (TASK-5.3, PR #46); widoczna dla użytkownika w `dashboard_latest()` + mobile, 3 dni max/min z atrybucją i freshness (TASK-5.5); prognoza godzinowa 48 h w `forecast.hours[]` (TASK-5.6, ADR-030, PR #88; niewyświetlana w UI, silnik „najlepszego okna” = TASK-7.10, godzinowe powietrze = TASK-7.11) |

### 2.3. Pylenie (§6)

| Metryka | Status |
|---|---|
| olcha, brzoza, trawy, bylica, ambrozja | 🟡 PARTIAL — **backend ✅** (TASK-8.5–8.7, PR #71, ADR-020): connector `open_meteo_pollen` (CAMS Europe przez Open-Meteo Air Quality — **prognoza modelowa, nie pomiar**, `kind=model_forecast`), `PollenSnapshot` (5 gatunków, NULL ≠ 0), scheduler 24 h z `source_status`, provenance, `GET /api/v1/pollen/latest`. **Brak** karty mobile (TASK-8.8) i bloku `pollen` w `dashboard_latest()` (TASK-8.9) — w toku w osobnym PR, nie DONE. Rzeczywiste pomiary (OBAŚ) niezweryfikowane |
| kalendarz pylenia (typowy sezon, nie pomiar/prognoza) | 🟡 PARTIAL — statyczne dane + `GET /api/v1/pollen/calendar` (ADR-023, TASK-8.10): leszczyna, olsza, brzoza, jesion, dąb, trawy, bylica, Cladosporium; ambrozja/pokrzywowate NIEZWERYFIKOWANE (`not_covered`); UI: karta „Kalendarz pylenia — typowy sezon” na mobile (osobna od prognozy CAMS) |

### 2.4. Woda / kąpieliska (§7)

| Metryka | Status |
|---|---|
| status kąpieliska (dopuszczone/niedopuszczone), przyczyna zamknięcia, sezon kąpielowy, lokalizacja kąpieliska | ⛔ BLOCKED — research + ADR-021 (Proposed) gotowe (TASK-11.1 🟡 częściowo, 11.2 ⛔; PR #72, bez kodu); GIS (`sk.gis.gov.pl`) to HTML bez API/licencji, EEA daje tylko rejestr + klasyfikację roczną (licencja wydania 2025 niepotwierdzona); brak źródła statusu bieżącego |
| E. coli, enterokoki, sinice | ⛔ BLOCKED — brak źródła bieżących pomiarów (ADR-021, TASK-11) |
| data ostatniego / następnego badania próbki | ⛔ BLOCKED — brak źródła bieżących pomiarów (ADR-021, TASK-11) |

### 2.5. Hydrologia (§8)

| Metryka (MVP wg Master Planu) | Status |
|---|---|
| poziom rzek | ✅ DONE — IMGW hydro (ADR-008), `GET /api/v1/hydro/latest` |
| stan ostrzegawczy / stan alarmowy | ✅ DONE — progi per stacja (upsert/delete względem cyklu ingestu), `status: NORMAL/WARNING/ALARM/UNKNOWN` w `GET /api/v1/hydro/latest` (TASK-9.3, PR #42) |
| ostrzeżenia hydrologiczne | ✅ DONE — `imgw_warningshydro` (ADR-009), `GET /api/v1/alerts/latest`; w agregacie `dashboard_latest()` (`alerts`, scope `national`) i na mobile jako „Ostrzeżenia — cała Polska” (TASK-7.2) |

### 2.6. Alerty i zdarzenia (§9)

| Typ (MVP wg Master Planu) | Status |
|---|---|
| ostrzeżenia hydrologiczne | ✅ DONE (patrz 2.5) |
| ostrzeżenia meteorologiczne | ⛔ BLOCKED — `imgw_warningsmeteo`: `client.py` + dispatch pustego stanu zweryfikowane i gotowe (PR #38), ale `normalize()` (mapowanie pól pojedynczego ostrzeżenia) **czeka na żywy przykład aktywnego ostrzeżenia** — API nie miało żadnego w chwili implementacji, a nieoficjalne źródła sugerują inny schemat pól niż hydro. Nie zgadujemy danych bezpieczeństwa (rule #10/#15). Wznowić: `docs/tasks/TASK-9.2-imgw-warningsmeteo-blocked.md` |
| zamknięcia kąpielisk | ⛔ BLOCKED — zależne od źródła statusu bieżącego kąpielisk (2.4, ADR-021) |
| istotne lokalne zagrożenia / zweryfikowane zdarzenia | ⬜ TODO — model `Event` (§31) nie istnieje; granica Alert ≠ Event ≠ Notification opisana w ADR-013 (PR #81), `Event` czeka na decyzję człowieka o źródle (TASK-9.4) |
| geo-matching alertu → lokalizacja użytkownika | 🟡 PARTIAL — backend (TASK-9.5 część, PR #81, ADR-013): nazwa województwa z `obszary` → kod TERC → prefiks `geo_areas.teryt_code` (`app/alert_geo.py`, bez migracji, bez LLM), `GET /api/v1/alerts/latest?geo_area_id=`, `AlertOut.geo_match` (`voivodeship`/`unresolved`), `local_alerts` per obszar w `dashboard_latest()`; krajowe `alerts` bez zmian. **Poziom = województwo** (IMGW hydro nie podaje TERYT/powiatów/gmin, tylko `kod_zlewni`). Obszary bez `teryt_code` (seedy przed importem granic gmin) i nierozpoznane obszary alertu → `unresolved` (pokazane, nie ukryte). Brak: użycie w mobile (TASK-9.7), `/hydro/latest` po lokalizacji, meteo (⛔) |
| Alert Engine (§47) / Notification Engine (§50) | ⬜ TODO — poza scope'em dotychczasowych tasków, świadomie odłożone |

---

## 3. Backend — checklist z §10 (MVP zawiera)

| Element | Status |
|---|---|
| FastAPI | ✅ DONE |
| PostgreSQL | ✅ DONE |
| PostGIS | 🟡 PARTIAL — fundament gotowy (TASK-6.2, PR #70, ADR-019): migracja `0011` (`postgis`, `geo_areas.teryt_code`/`boundary`/`weather_polling_active`), obraz `postgis/postgis:16-3.4` w CI/compose. **Brak danych**: granice gmin PRG nie są załadowane (pobranie + licencja po stronie człowieka, sekcja 6) |
| Redis (cache/stan krótkotrwały) | ⬜ TODO — nie wdrożone; obecnie wszystko czyta z PostgreSQL bezpośrednio |
| Connector framework (fetch/parse/validate/normalize) | ✅ DONE — wzorzec ustalony i powtórzony w 6 connectorach (`gios`, `open_meteo`, `open_meteo_pollen`, `imgw_hydro`, `imgw_warningshydro`, `imgw_warningsmeteo` częściowo); `prg_gminy` to importer jednorazowy z lokalnego pliku, nie connector sieciowy |
| Scheduler | ✅ DONE — ADR-007, loop-based, per-job interval gating, izolacja awarii (rule #1, `_run_job_safely`) |
| Workers (oddzielny proces/kolejka) | ⬜ TODO — świadomie NIE zrobione (ADR-007): scheduler w jednym procesie wystarcza przy obecnej skali, przejście na worker/queue dopiero gdy realnie potrzebne |
| Normalization / validation | 🟡 PARTIAL — wzorzec (fetch/parse/validate/normalize) wdrożony w pełni w 5 connectorach (`gios`, `open_meteo`, `open_meteo_pollen`, `imgw_hydro`, `imgw_warningshydro`); `imgw_warningsmeteo` ma tylko `client.py` + dispatch pustego stanu, brak `normalize()`/`ingest.py` (patrz 2.6, blocker) |
| Freshness | 🟡 PARTIAL — per-wiersz freshness (FRESH/RECENT/STALE) dla `/air`, `/hydro`, `/alerts`, `/weather`; **source-level freshness z UNAVAILABLE (ADR-012, TASK-7.4)** dla ostrzeżeń (#59, #61) i hydrologii (#62): tabela `source_status` zapisywana przez scheduler i ręczne CLI, `source_status` w `/alerts/latest`, `/hydro/latest` i agregacie; mobile nie pokazuje „brak ostrzeżeń/alarmów”, gdy źródło milczy lub status zestarzał się na urządzeniu (>6h); `air`/`weather` w agregacie też niosą `source_status` (TASK-7.3, PR #78); pyłki mają `source_status` w `/pollen/latest` (PR #71). Widok operatorski: `GET /api/v1/health/sources` (TASK-13.1, PR #69) |
| Provenance / raw ingestion (§33-34) | ✅ DONE — `source_fetches` (surowy payload, endpoint, wersja parsera, status walidacji) + nullable FK `source_fetch_id` na `Measurement`/`Alert`/`WeatherSnapshot`/`Forecast`; wszystkie connectory istniejące w PR #65 (4; pyłki dołączyły w PR #71); retencja payloadu 7/14/30 dni, metadane zostają; zapis best-effort, awaria nie psuje ingestu (ADR-014, TASK-3.1, PR #65). Rekordy sprzed migracji 0009 mają FK NULL |
| Outdoor Interpretation Engine (§52) | 🟡 PARTIAL — `app/outdoor.py`: deterministyczny GOOD/MODERATE/POOR/UNKNOWN + `reasons[]`/`missing[]` (ADR-016, PR #64); progi PM/UV/wiatr ze źródłami (PM/NO₂/O₃ czytane z `air_index.BANDS`), temperatura/opady/widoczność oznaczone „do kalibracji”; NO₂/O₃ (grupy opcjonalne) i burza WMO ≥95 → POOR w silniku (addendum ADR-016, PR #87). Podłączony: blok `outdoor` per obszar w `dashboard_latest()` i `OutdoorCard` na mobile (TASK-7.7/7.8, PR #68); preferencje „outdoor” użytkownika (TASK-12.4) nie istnieją |
| Geo matching | 🟡 PARTIAL — nearest-station GIOŚ↔geo_area (ADR-006, próg 50 km) oraz **point-in-polygon lat/lon → gmina** (`app/geo.py::resolve_gmina`, `POST /api/v1/geo/resolve`, TASK-6.2 punkty 1–6, PR #70, ADR-019). Resolver bez danych zwraca `None` (granice gmin niezaładowane). Odkrywanie stacji GIOŚ per aktywny obszar (6.2/7, ADR-025): katalog `gios_stations` (odświeżany ≤ 1×/dobę), przypisanie nearest ≤ 50 km z tie-breakiem po id, `assignment_method` w dashboardzie i `/air/latest?geo_area_id=`; `GIOS_STATION_IDS` nadal override. Alerty dopasowane do obszaru po TERYT (województwo, ADR-013, PR #81). Zawężenie do lokalizacji (6.2/8, ADR-026): `/dashboard/latest?geo_area_id=` (404 dla nieznanego; obszar bez pollingu → `weather_polling_active=false`, weather/forecast/pollen puste, air wg stacji z katalogu ≤ 50 km, outdoor UNKNOWN bez rdzenia), `GET /areas`, `POST /geo/locate` (point-in-polygon → najbliższy aktywny obszar ≤ 25 km jawnie jako `nearest_area` → `out_of_range`); backend, bez klienta mobile. Nie zrobione: `/hydro/latest` po lokalizacji (TASK-9.5), aktywacja pollingu wybranej gminy (TASK-12.2) |
| Dowolna miejscowość (TASK-6.3, ADR-029) | 🟡 PARTIAL — backend gotowy: rejestr `places` (migracja `0014`, import GeoNames PL (`--download` albo plik, z nazwami powiatów/województw → `label`), `geonames_places`), `GET /api/v1/places?q=` (prefiks bez diakrytyków), `POST /places/{id}/activate` (limit aktywnych z budżetu Open-Meteo ~411, TTL 7 dni, pierwszy fetch w minuty), jawny `coverage` powietrza (`exact` ≤ 10 / `nearby` ≤ 50 / `regional` ≤ 100 km / `none`; pogoda i pyłki = `grid`), polling GIOŚ do 100 km, `regional` poza werdyktem „Na dwór”. **Brak danych w bazie** do czasu importu pliku GeoNames (gate #15 otwarty); UI wyboru → TASK-12.7 |
| Alert Engine | ⬜ TODO |
| Notification Engine | ⬜ TODO |
| REST API | 🟡 PARTIAL — `/air`, `/weather`, `/hydro`, `/alerts`, `/pollen`, `/dashboard/latest` (`?geo_area_id=`), `/areas`, `/geo/resolve`, `/geo/locate`, `/devices`, `/health`, `/health/sources`; wersjonowane pod `/api/v1/`. Brak `/water` (kąpieliska ⛔). `/dashboard/latest` ma `response_model` + typy TS generowane z OpenAPI (TASK-2.1, ADR-024) |
| Logging | ✅ DONE — `logging` per connector/scheduler, ustandaryzowane |
| Source health (TASK-13.1) | 🟡 PARTIAL — `GET /api/v1/health/sources` (freshness FRESH/RECENT/STALE/UNAVAILABLE, ostatnia próba/sukces, zsanityzowany `last_error`, budżet dzienny), scheduler loguje raz na zmianę stanu (PR #69; ADR-012). **Brak** historii runów i telemetrii §44 (duration, records processed, validation errors, duplicate/stale rate) — wymaga osobnego ADR i migracji; pyłki w rejestrze dołączone w PR #71 |
| Device registration (TASK-10.1, ADR-017) | 🟡 PARTIAL — backend: `POST/DELETE /api/v1/devices` bez konta, sekret urządzenia (SHA-256), rate limit in-memory, migracja `0010` (PR #67). Realna wysyłka push wymaga kluczy FCM/APNs (sekcja 6); klient mobilny (10.5), preferencje (10.3a) i Notification Engine (10.2) ⬜ |
| Monitoring | 🟡 PARTIAL — dzienny licznik wywołań per źródło + WARNING przy 70% limitu (TASK-13.1a, PR #55) i source health (wiersz wyżej); brak zewnętrznego monitoringu/alertingu (TASK-13.2) |
| Provider config Free→Paid (TASK-13.4, ADR-022) | 🟡 PARTIAL — (kod gotowy, PR #73; do ✅ po pierwszym żądaniu testowym z prawdziwym kluczem komercyjnym i potwierdzeniu hosta Air Quality) endpointy Open-Meteo i `OPEN_METEO_API_KEY` w env (domyślnie Free), klucz maskowany w wyjątkach/logach/provenance; przejście na plan komercyjny = tylko config. **Przed monetyzacją: checklista w ADR-003** (plan komercyjny Open-Meteo, env produkcyjne, licencje pozostałych źródeł). Host `customer-air-quality-api…` niezweryfikowany wprost |
| Backup | 🟡 PARTIAL — `backup.sh`/`restore_test.sh`/`test_backup_restore.sh` gotowe i przetestowane na Postgres 16 (dump+sekrety szyfrowane age bez plaintextu na dysku, spójna migawka dump+manifest, walidacja manifestu, limit wieku backupu, hasło poza argv); brak: realny off-VPS storage provider, zaplanowane uruchamianie na produkcji (TASK-15.2/15.3), wydzielony host weryfikacyjny |

---

## 4. Mobile — checklist z §10 (MVP zawiera)

| Element | Status |
|---|---|
| Home / Dashboard | 🟡 PARTIAL — zakładka „Start” (`app/(tabs)/index.tsx`; logika w `lib/home.ts`, spec Frontend UX/UI v1 §9–§17, §40–§44, §50): nagłówek (nazwa obszaru, data po polsku, temperatura) → Hero Verdict „Na dwór” LIVE (✓/!/×/?, brak mocków) → karty Powietrze / Pogoda / Prognoza pyłków (data-driven; pyłki zawsze jako prognoza CAMS; tap = rozwinięcie dotychczasowych szczegółów, w tym prognozy) → status ostrzeżeń (✓ „Brak aktywnych ostrzeżeń” ≠ ? „Nie udało się sprawdzić ostrzeżeń”; realne ostrzeżenie/stan wody wędruje pod nagłówek) → kalendarz pylenia. Skeletony per moduł, błędy bez technikaliów, częściowa awaria nie blokuje ekranu, stale: „Dane z HH:MM” / „Dane mogą być nieaktualne”. Pokazuje jeden obszar (pierwszy; `TODO(TASK-12.7)` — wybór lokalizacji). Sekcja „Co możesz dziś robić?” NIE jest renderowana (brak backendu). Stany wody i lista ostrzeżeń — zakładka Alerty. |
| Nawigacja + design system | 🟡 PARTIAL — Expo Router, tab bar Start/Alerty/Ustawienia (ikony Home/Bell/Settings, Ionicons) (`app/(tabs)/`; w `app/` tylko trasy, moduły logiki i testy w `apps/mobile/lib/`), tokeny (`lib/theme.ts`, kontrast ≥ 4.5:1 sprawdzany testem w obu paletach), jasny/ciemny motyw wg systemu, safe-area, a11y (role/labele, min. dotyk 44, status = glif + słowo + kolor). Bez NativeWind (ADR-027) — StyleSheet + tokeny. **Niezweryfikowane na urządzeniu/emulatorze** (brak środowiska w PR): wygląd i tab bar do obejrzenia ręcznie |
| Mapa ekranów UI i polityka mocków | 🟡 PARTIAL — **dokumentacja, bez kodu**: [`docs/ui/screen-map.md`](ui/screen-map.md) (drzewo nawigacji, tabele ekran/element/źródło/status/stany, kontrakt danych dla przyszłych pól, macierz „co live”) + ADR-028 (Proposed: mocki UI za flagą, `Sourced<T>`, zakaz mocków danych bezpieczeństwa). Zadania `TASK-7.9`, `TASK-8.11`, `TASK-12.10`–`12.19` w BACKLOG; uwzględnia spec UI właściciela (jedna lokalizacja, Welcome + tematy, kąpieliska poza UI, powiadomienia ukryte); żaden mock jeszcze nie istnieje w kodzie |
| Alerts (ekran) | 🟡 PARTIAL — zakładka Alerty: ostrzeżenia IMGW + stany wody, **cała Polska** (bez geo-filtra do czasu lokalizacji/TASK-9.5+9.7; `local_alerts` i `?geo_area_id=` z backendu jeszcze nieużyte), brak szczegółu pojedynczego alertu |
| Settings | 🟡 PARTIAL — placeholder (TASK-12.1): wersja, lista źródeł z `attribution` backendu, informacja o braku konta/lokalizacji; brak preferencji, brak strony polityki prywatności (nie ma jej w `docs/`) |
| foreground location | ⬜ TODO — obecnie statyczna lista 7 zaseedowanych miast, brak geolokalizacji urządzenia |
| ręczny wybór lokalizacji | ⬜ TODO |
| push notifications | ⬜ TODO — (backend rejestracji urządzeń 🟡 w sekcji 3; klient mobilny i wysyłka nie istnieją) |
| profil użytkownika | ⬜ TODO |
| podstawowe preferencje | ⬜ TODO |
| source transparency | ✅ DONE — `dashboard_latest()` zwraca `source`+`attribution`+`observed_at` dla air i weather, mobile renderuje atrybucję pod każdą sekcją (TASK-7.1, PR #49) |
| freshness (UI) | ✅ DONE — etykieta freshness pokazywana per sekcja |
| loading / error / stale / no-data states | ✅ DONE dla powietrza i pogody — loading/error/ready + FRESH/RECENT/STALE/UNAVAILABLE i „brak danych” (etykieta wieku, przygaszenie, efektywna świeżość = worst z danych i `source_status`; TASK-7.3, PR #78). Prognoza dzienna: tylko etykieta freshness |

---

## 5. Poza MVP (§11) — celowo nietykane

Zgodnie z Master Planem, świadomie NIE robimy: mapy, uniwersalnego Green
Index, background location, obowiązkowego konta, PWA, rozbudowanego
social/community, zaawansowanej monetyzacji, pełnej historii danych,
rozbudowanych funkcji premium. Nie zmieniać bez decyzji użytkownika + ADR.

---

## 6. Aktywne blokady (wymagają decyzji lub zewnętrznego zdarzenia)

| Blokada | Co odblokuje | Task |
|---|---|---|
| `imgw_warningsmeteo.normalize()` | Żywe, aktywne ostrzeżenie meteo w API (burze/upały latem, śnieg/mróz zimą) do podejrzenia realnego kształtu pól | TASK-9.2 |
| Kąpieliska: brak źródła BIEŻĄCEGO statusu | Status BIEŻĄCY wymaga zgody/API od GIS (`sk.gis.gov.pl` to HTML bez API i licencji) lub innego zatwierdzonego źródła (dane.gov.pl/WIOŚ — kandydaci, niesprawdzeni). EEA po potwierdzeniu licencji wydania 2025, schematu i filtra PL odblokuje tylko rejestr + klasyfikację roczną, NIE status bieżący. Pełny Gate §38 (APPROVED) dla każdego wybranego źródła | TASK-11.1/11.2, ADR-021 |
| Geo-matching alertów — dokładność poniżej województwa | Dopasowanie na poziomie województwa jest (PR #81, ADR-013). Powiat/gmina wymaga, by źródło podawało TERYT (hydro: tylko `kod_zlewni`; meteo: kształt nieznany, TASK-9.2) lub zbioru zlewnia↔gmina. Dopóki granice gmin nie są załadowane, obszary seedowe mają `teryt_code = NULL` → `unresolved` | TASK-9.5 |

### Blokady po stronie człowieka (kod nie przesunie tego dalej)

| Do zrobienia | Czego dotyczy | Task / źródło |
|---|---|---|
| Zatwierdzić licencję PRG (GUGiK) w Source Approval Gate i pobrać `00_jednostki_administracyjne.zip` → GeoJSON gmin → import (`python -m app.connectors.prg_gminy.ingest`) | Bez tego `POST /geo/resolve` zwraca `None`, a 6.2 zostaje 🟡 | TASK-6.2, `docs/tasks/TASK-6.2-geo-engine-foundation.md` |
| Na VPS uruchomić import GeoNames (`docker compose exec api python -m app.connectors.geonames_places.ingest --download`) i formalnie przejść Source Approval Gate (`geonames_pl`, CC BY 4.0) | Bez tego `GET /places` zwraca pustą listę (wybór dowolnej miejscowości nie działa); układ pliku zweryfikowany na prawdziwym zrzucie | TASK-6.3, ADR-029, `source-registry.md` |
| Kontakt z GIS ws. udostępnienia API/danych o kąpieliskach (albo wybór innego zatwierdzonego źródła); potwierdzić licencję EEA 2025, jeśli wystarczy rejestr + klasyfikacja roczna | Odblokowanie 2.4 | TASK-11.1/11.2, ADR-021, `docs/tasks/TASK-11-bathing-water.md` |
| IMGW: ustalić, czy hydro/ostrzeżenia to dane o wysokiej wartości (HVD, rozp. UE 2023/138) i jak ma się CC BY-NC-ND 4.0 zbioru plikowego do API; w razie potrzeby umowa (biznes@imgw.pl) | Przed monetyzacją (checklista ADR-003) | ADR-003, `source-registry.md` |
| Open-Meteo: pisemne potwierdzenie dla Patronite (szara strefa), ceny planów komercyjnych (niezweryfikowane), potwierdzenie hosta Air Quality (`customer-air-quality-api…`) i pierwsze żądanie z prawdziwym kluczem | TASK-13.4 🟡 → ✅; przed monetyzacją | ADR-003, ADR-022 |
| OBAŚ — nawiązać kontakt (rzeczywiste pomiary pyłków; dziś kandydat, nic niezweryfikowane) | Opcjonalne uzupełnienie pyłków pomiarami (osobny byt Measurement) | `source-registry.md` (`obas`), ADR-022 |
| Klucze FCM/APNs (konta deweloperskie Google/Apple) jako zmienne środowiskowe | Realna wysyłka push; walidacja iOS wymaga konta Apple Developer | TASK-10.1 🟡, 10.2 |
| Skasować pusty plik `pr.json` w katalogu głównym repo, jeśli jest w lokalnej kopii (nie jest śledzony w `main`) | Higiena repo | — |

---

## 7. Historia PR (referencja, nie duplikować szczegółów z commitów)

| PR | Co wniósł |
|---|---|
| #32–#34 | Testy retroaktywne, hardening, source-registry housekeeping |
| #35 | Scheduler (ADR-007) |
| #36 | IMGW hydro / Measurement (ADR-008), `/hydro/latest` |
| #37 | IMGW warnings hydro / Alert (ADR-009), `/alerts/latest`, reconciliation, freshness, izolacja awarii schedulera |
| #38 | `imgw_warningsmeteo` — client + dispatch zweryfikowane, `normalize()` świadomie zablokowane (TASK-9.2) |
| #39 | Fix rule #10 w `imgw_warningshydro/parser.py` (exact-shape matching dla pustego stanu) |
| #40 | `docs/ROADMAP.md` (ten plik) + reguła utrzymania w CLAUDE.md |
| #41 | Open-Meteo: rozszerzenie `CURRENT_PARAMS` z 4 do 12/15 pól MVP (§5) |
| #42 | `imgw_hydro`: progi ostrzegawcze/alarmowe stanu wody + status NORMAL/WARNING/ALARM/UNKNOWN (TASK-9.3, ADR-008) — 6 rund przeglądu Codex, patrz historia w TASK-9.3 |
| #43 | `docs/ROADMAP.md` — odzwierciedlenie PR #40/#41 |
| #44 | `docs/ROADMAP.md`/TASK-9.3 — progi hydro DONE, uzupełnienie historii review (2 dodatkowe realne poprawki dokumentacji) |
| #45 | `docs/tasks/BACKLOG.md` — uporządkowana kolejka pozostałych faz + reguły przekrojowe (provenance, limity źródeł, source_status) |
| #46 | Forecast (§30, ADR-010): `GET /api/v1/weather/forecast`, domyka Phase 5 |
| #48 | GIOŚ: pełny zestaw parametrów MVP (PM10/NO2/SO2/O3/CO/C6H6, TASK-4.1) + fix jednostki CO + izolacja awarii per-param |
| #49 | Source transparency w `dashboard_latest()` + mobile (TASK-7.1) |
| #50 | Open-Meteo: punkt rosy/widoczność/UV index z `hourly` dopasowane do godziny `current` (TASK-5.4), domyka pozostałe MVP pola §5; per-param freshness na `/weather/latest` |
| #51, #53, #54 | Typed `response_model` dla `/air/latest`, `/hydro/latest`, `/alerts/latest` (TASK-API-1/3/4) |
| #52 | Typed `response_model` dla `/weather/latest` i `/weather/forecast` (pola czasowe jako `datetime`) |
| #55 | Dzienny licznik wywołań per źródło + alert 70% (TASK-13.1a): jednostki rozliczeniowe Open-Meteo, każda próba HTTP liczona przed wysłaniem, atomowy inkrement |
| #56 | Per-param `observed_at`/`freshness` pogody w `dashboard_latest()` + mobile (Codex P1 z PR #50, rezydualny w agregacie) |
| #57 | Prognoza w `dashboard_latest()` + mobile (TASK-5.5), wspólny helper `forecasts_by_area()` z `/weather/forecast` |
| #58 | Ostrzeżenia IMGW w `dashboard_latest()` + mobile, jawnie ogólnokrajowe do czasu geo-matchingu (TASK-7.2) |
| #47 | Backup + test odtworzenia (TASK-1.1, §68): age, spójna migawka, manifest, hasło poza argv |
| #59 | Source-level freshness / UNAVAILABLE dla ostrzeżeń (ADR-012, TASK-7.4) |
| #61 | Follow-up #59: status starzeje się na urządzeniu (6h, timer 60 s), brak `source_status` bez wyjątku, `last_success_at` z przyszłości = STALE |
| #62 | Hydrologia na mobile: „Stany wody — cała Polska” (WARNING/ALARM), `attribution` + `source_status` w `/hydro/latest`, CLI hydro zapisuje `source_status` (TASK-7.2) |
| #64 | Outdoor Interpretation Engine (ADR-016, TASK-7.6) — czysty moduł, niepodłączony do API |
| #65 | Provenance: `source_fetches` + `source_fetch_id`, retencja payloadów (ADR-014, TASK-3.1) |
| #66 | Sync ROADMAP/BACKLOG po #61 #62 #64 #65 (docs) |
| #67 | Rejestracja urządzeń pod push bez konta: `POST/DELETE /api/v1/devices`, model `Device`, migracja `0010`, rate limit (ADR-017, TASK-10.1) — 🟡, bez kluczy FCM/APNs |
| #68 | `outdoor` w `dashboard_latest()` + `OutdoorCard` na mobile (TASK-7.7/7.8) |
| #69 | Source health: `GET /api/v1/health/sources` + logi zmian stanu w schedulerze (TASK-13.1, ADR-012) — 🟡, bez historii runów/telemetrii §44 |
| #70 | Geo Engine — fundament (TASK-6.2, ADR-019): PostGIS, migracja `0011`, importer `prg_gminy`, `resolve_gmina`, `POST /api/v1/geo/resolve`, `weather_polling_active`; bez danych gmin — 🟡 |
| #71 | Pyłki backend (TASK-8.5–8.7, ADR-020): `open_meteo_pollen`, `PollenSnapshot`, scheduler, `GET /api/v1/pollen/latest`; karta mobile i agregat (8.8/8.9) osobno |
| #63 | Europejski indeks jakości powietrza EAQI/EEA (ADR-015, TASK-4.2): `air_index.py`, `index` w `/air/latest` i dashboardzie, mobile `AirIndexBadge`; indeks GIOŚ odłożony |
| #72 | Kąpieliska: research źródeł + ADR-021 (Proposed), registry; TASK-11.1 częściowo, 11.2 ZABLOKOWANE — bez kodu |
| #73 | Provider config Free→Paid (ADR-022, TASK-13.4): endpointy/klucz Open-Meteo w env, maskowanie klucza, FREE-FIRST (reguła #17), checklista przed monetyzacją (ADR-003) |
| #75 | Pyłki w dashboardzie: blok `pollen` w `dashboard_latest()` (TASK-8.9, izolowany, freshness + `source_status`) + karta mobile `PollenCard`/`pollen.ts` (TASK-8.8); progi sezon/szczyt EAACI wg CAMS/EEA (ADR-020) |
| #79 | Stacje GIOŚ per aktywny obszar (TASK-6.2 (7), ADR-025): katalog `gios_stations` (migracja `0013`, odświeżany ≤ 1×/dobę), `geo.select_stations` (nearest ≤ 50 km, tie-break po id), polling stacji przypisanych do `polling_areas` (`GIOS_STATION_IDS` = override), `assignment_method` w dashboardzie i `/air/latest?geo_area_id=` |
| #77 | Kontrakt API (TASK-2.1, ADR-024): `response_model` `DashboardResponse` dla `/dashboard/latest` (1:1 z dotychczasowym JSON-em), `openapi.json` + typy TS generowane bez zależności w `packages/api-contract`, kroki CI `--check`, `contract.test.ts` w mobile |
| #76 | Kalendarz pylenia: statyczne dane referencyjne + `GET /api/v1/pollen/calendar` (ADR-023, TASK-8.10); 8 taksonów (z trawami), ambrozja/pokrzywowate niezweryfikowane |
| #81 | Alerty ↔ obszar (TASK-9.5 część, ADR-013): `app/alert_geo.py` (województwo → TERYT, fail-safe `unresolved`), `?geo_area_id=` w `/alerts/latest`, `geo_match`, `local_alerts` w dashboardzie, kontrakt zregenerowany; ADR-013 = granica Measurement/Forecast/Event/Alert/Notification (`Event`/`Notification` nie powstały) — 🟡 |
| #78 | Stany stale/no-data dla air i weather (TASK-7.3): `source_status` w blokach dashboardu, efektywna świeżość + etykieta wieku + przygaszenie w UI; prezentacja pól pogody na mobile (TASK-5.4) |
| #80 | Mobile: karta „Kalendarz pylenia — typowy sezon” (TASK-8.10 UI, `pollenCalendar.ts`/`PollenCalendarCard`, osobny fetch `/pollen/calendar`, pusty `active` ≠ „nic nie pyli”) + typy `index`/`alerts`/`hydro`/`outdoor`/`aqi` z kontraktu API (follow-up TASK-2.1) |
| #83 | Mobile: fundament UI — zakładki Dziś/Alerty/Ustawienia (Expo Router), tokeny designu + ciemny motyw (kontrast testowany), safe-area, a11y, stany pusty/błąd bez wskazówek deweloperskich w produkcji, rozbicie `index.tsx` na komponenty; ostrzeżenia i stany wody przeniesione na Alerty (nadal cała Polska) |
| #86 | Mobile: struktura ekranu Start wg Frontend UX/UI Spec v1 — zakładki Start/Alerty/Ustawienia, nagłówek, Hero Verdict, karty statusu (data-driven), status ostrzeżeń (brak ≠ nie sprawdzono), skeletony per moduł, stale/partial failure; bez zmian backendu |
| #84 | Docs: mapa ekranów UI (`docs/ui/screen-map.md`), ADR-028 (mocki UI, Proposed), zadania TASK-7.9, TASK-8.11, TASK-12.10–12.19 w BACKLOG — bez kodu |
| #82 | Wybór lokalizacji w API (TASK-6.2 (8), ADR-026): `/dashboard/latest?geo_area_id=`, `GET /areas`, `POST /geo/locate` (nearest active area ≤ 25 km jawnie, `out_of_range`), `weather_polling_active` w `DashboardArea`, kontrakt zregenerowany; bez klienta mobile — 🟡 |
| #85 | Dowolna miejscowość w Polsce (TASK-6.3, ADR-029): rejestr `places` (migracja `0014`, import GeoNames PL z lokalnego pliku), `GET /places`, `POST /places/{id}/activate` (limit z budżetu Open-Meteo, TTL 7 dni, pierwszy fetch w minuty), jawny `coverage` powietrza `exact/nearby/regional/none` + `grid` dla pogody/pyłków, polling GIOŚ do 100 km, `regional` poza werdyktem „Na dwór”, kontrakt zregenerowany; bez klienta mobile i bez danych (plik GeoNames do zaimportowania) — 🟡 |

| #87 | Silnik „Na dwór”: NO₂/O₃ (opcjonalne grupy, progi z `air_index.BANDS`) i burza (`weather_code` ≥95 → POOR); addendum ADR-016; kontrakt bez zmian |
| #88 | Prognoza godzinowa 48 h (TASK-5.6, ADR-030): `forecast.hours[]` w dashboardzie, `forecasts.granularity` (migracja `0015`), jedno żądanie Open-Meteo, retencja „najnowszy przebieg”, parser odporny na `null`; estymata budżetu 2→3 jedn. (`max_active_areas` 411→280) — zależny od #87 |
---

## Jak utrzymywać ten plik

**Zasada dla Claude (i każdego, kto pracuje nad tym repo): ten plik
aktualizuje się po każdym zmergowanym PR**, w tym samym PR-ze co zmiana albo
osobnym małym commitem zaraz po merge'u. Aktualizacja obejmuje: sekcję 1
(status jednym zdaniem, jeśli się zmienił), właściwą tabelę w sekcji 2-4 (nowy
✅/🟡/⛔ tam gdzie coś się zmieniło), sekcję 6 (nowe/rozwiązane blokady) i
sekcję 7 (nowy wiersz z numerem PR). Nie przepisywać całego pliku za każdym
razem — punktowa edycja, tak jak przy kodzie.
