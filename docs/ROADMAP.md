# Za Oknem — Roadmap

**Ten plik odzwierciedla stan faktyczny kodu, nie plany.** Aktualizowany po
każdym zmergowanym PR (patrz przypis na końcu). Źródło wizji produktowej:
[`Development-Master-Plan-v1.2.md`](architecture/Development-Master-Plan-v1.2.md)
(§4–§11). Status źródeł danych ze szczegółami (licencja, rate limit,
attribution): [`source-registry.md`](data/source-registry.md).

**Ostatnia aktualizacja:** 2026-10-03 (GIOŚ #146–149 scalone; pierwszy etap IMGW w PR, pod flagami)

Legenda: ✅ DONE · 🟡 PARTIAL (częściowo, mniej niż pełny zakres MVP) ·
⛔ BLOCKED (zatrzymane na konkretnym warunku) · ⬜ TODO (nie zaczęte)

---

## 1. Gdzie jesteśmy (jednym zdaniem)

Vertical Slice z CLAUDE.md (GIOŚ → connector → PostgreSQL → FastAPI → React Native) działa end-to-end i
jest rozszerzony o pogodę, prognozę godzinową, pyłki (CAMS przez Open-Meteo), poziomy wody i
ostrzeżenia hydrologiczne IMGW (adaptery zachowane, publikacja teraz off wg researchu), EAQI i ocenę „Na dwór”. Backend wybiera dla każdej lokalizacji
najbliższą stację GIOŚ **z bieżącymi danymi, jeśli dostępna**, dopasowuje alerty do lokalizacji (kod TERYT gminy albo województwo
miejscowości) i ma rejestr dowolnych miejscowości (GeoNames) oraz „najbliższą miejscowość” dla GPS.
Mobile (Android, produkcyjny UI v1): Welcome → Lokalizacja (wyszukiwarka, lista miast, GPS jednorazowy) →
Start / Alerty / Ustawienia plus ekrany Pogoda, Powietrze, Pyłki, Alert, Rzeki. **Niezweryfikowane na
urządzeniu** (brak zrzutów, TalkBack, 130/200% fontu, APK po stronie właściciela). Nie ma jeszcze:
push (klienta ani wysyłki), granic gmin (PRG), kąpielisk (źródło zablokowane — sekcja 6), wdrożenia na VPS.

---

## 2. Dane / metryki — zakres z Master Planu §4-9 vs stan faktyczny

### 2.1. Powietrze (§4.1)

| Metryka (MVP wg Master Planu) | Status |
|---|---|
| PM2.5, PM10, NO2, SO2, O3, CO, C6H6 | ✅ DONE — GIOŚ, pełny zestaw parametrów MVP (TASK-4.1, PR #48), `GET /api/v1/air/latest`, w dashboardzie |
| indeks jakości powietrza + indeksy cząstkowe | ✅ DONE — **Europejski Indeks Jakości Powietrza (EAQI, EEA)**, nie natywny indeks GIOŚ: `app/air_index.py` (progi EEA zweryfikowane 2026-09-30, najgorszy z cząstkowych, minimalny zestaw, STALE/inna jednostka = brak), pole `index` w `/air/latest` i w bloku `air` dashboardu, mobile `AirIndexBadge` (TASK-4.2, ADR-015, PR #63). Indeks GIOŚ `aqindex/getIndex` jest osobnym dodatkiem scalonym w PR #148 (ADR-033), z flagą rollout domyślnie off; migracja i uruchomienie produkcyjne pozostają do wykonania. Nasze decyzje poza specyfikacją EEA (granice dla wartości ułamkowych, typ stacji, polskie nazwy pasm) w ADR-015 |
| Sensor.Community, CAMS Air (MVP+) | ⬜ TODO (poza MVP na razie) |

### 2.2. Pogoda (§5)

| Metryka (MVP wg Master Planu) | Status |
|---|---|
| temperatura, wilgotność, wiatr (prędkość+kierunek+porywy), kod warunków, odczuwalna, ciśnienie, zachmurzenie, opady/deszcz/śnieg | ✅ DONE — Open-Meteo, `GET /api/v1/weather/latest` + dashboard (12/15 pól MVP, PR #41); na mobile `WeatherCard` pokazuje wszystkie zwracane pola z jednostkami (TASK-5.4, PR #78) |
| punkt rosy, widoczność, UV | ✅ DONE — Open-Meteo `hourly` (osobny fetch nie był potrzebny, jeden request z `current`+`hourly`+`daily`), dopasowanie do godziny `current` w parserze (TASK-5.4) |
| prognoza (forecast, nie tylko current) | ✅ DONE — model `Forecast` (§30, ADR-010), `GET /api/v1/weather/forecast`, dzienna prognoza (temp max/min, opady, kod pogody) (TASK-5.3, PR #46); widoczna dla użytkownika w `dashboard_latest()` + mobile, 3 dni max/min z atrybucją i freshness (TASK-5.5); prognoza godzinowa 48 h w `forecast.hours[]` (TASK-5.6, ADR-030, PR #89; niewyświetlana w UI, silnik „najlepszego okna” = TASK-7.10, godzinowe powietrze = TASK-7.11) |

### 2.3. Pylenie (§6)

| Metryka | Status |
|---|---|
| olcha, brzoza, trawy, bylica, ambrozja | 🟡 PARTIAL — **backend ✅** (TASK-8.5–8.7, PR #71, ADR-020): connector `open_meteo_pollen` (CAMS Europe przez Open-Meteo Air Quality — **prognoza modelowa, nie pomiar**, `kind=model_forecast`), `PollenSnapshot` (5 gatunków, NULL ≠ 0), scheduler 24 h z `source_status`, provenance, `GET /api/v1/pollen/latest`, blok `pollen` w `dashboard_latest()` (TASK-8.9, PR #75, izolowany, freshness). **Mobile ✅ (🟡 bez weryfikacji na urządzeniu):** kafelek „Pyłki” na Start (poziom z prognozy) i ekran „Pyłki” (PR #102). Rzeczywiste pomiary (OBAŚ) niezweryfikowane |
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
| ostrzeżenia meteorologiczne | 🟡 IMPLEMENTED UNDER GATES — aktywna fixture 2026-10-03 odblokowała parser; atomowy ingest/reconcile, scheduler, exact-county matching i mobile15min; domyślnie off do potwierdzenia czasu/approval. ADR-034, `docs/data/imgw/README.md` |
| zamknięcia kąpielisk | ⛔ BLOCKED — zależne od źródła statusu bieżącego kąpielisk (2.4, ADR-021) |
| istotne lokalne zagrożenia / zweryfikowane zdarzenia | ⬜ TODO — model `Event` (§31) nie istnieje; granica Alert ≠ Event ≠ Notification opisana w ADR-013 (PR #81), `Event` czeka na decyzję człowieka o źródle (TASK-9.4) |
| geo-matching alertu → lokalizacja użytkownika | 🟡 PARTIAL — backend (TASK-9.5 część, PR #81, ADR-013): nazwa województwa z `obszary` → kod TERC → prefiks kodu obszaru (`app/alert_geo.py`, bez LLM), `GET /api/v1/alerts/latest?geo_area_id=`, `AlertOut.geo_match` (`voivodeship`/`unresolved`), `local_alerts` per obszar w `dashboard_latest()`. Siedem miast z seedów ma kody TERYT gmin (migracja `0016`, PR #103); miejscowości z rejestru `places` (bez gminy) dopasowane po **województwie z GeoNames** (`places.alert_match_codes`, PR #105). **Poziom = województwo** (IMGW hydro nie podaje TERYT/powiatów/gmin, tylko `kod_zlewni`). Nierozpoznane obszary i miejscowość bez znanego województwa → `unresolved` (pokazane, nie ukryte). Mobile: sekcje „Dla Twojej lokalizacji” / „Do sprawdzenia” / „Pozostałe w Polsce” + szczegół alertu (PR #94, #102). Brak: `/hydro/latest` po lokalizacji, meteo (⛔) |
| Alert Engine (§47) / Notification Engine (§50) | ⬜ TODO — poza scope'em dotychczasowych tasków, świadomie odłożone |

### 2.7. Twoja okolica — dodatkowe dane GIOŚ (ADR-032, pakiet `docs/data/gios/`)

**Kierunek produktu (decyzja właściciela 2026-10-03):** „Za Oknem” = aktualny stan, to, co będzie (prognoza), i krótka
historia. Dane ogólne/historyczne to **ciekawostki** (np. trendy przez lata) i nie mają pierwszeństwa przed bieżącymi;
błędy i podejrzane odczyty zgłaszamy do GIOŚ. Dlatego moduł historyczny jest **on hold, także hałas** (kod pozostaje, flaga domyślnie off).
Pierwszeństwo ma GIOS-03; aktualne taski: `docs/data/gios/09-current-data-plan.md` (ADR-033).
Kolejność: implementacja danych → Design Lead → finalny UI → build i testy urządzenia.

Moduł addytywny: wiersz na Start → ukryty ekran; bez nowej zakładki, mapy, konta i push. Każda sekcja ma własną flagę
(domyślnie wyłączoną), źródło, okres danych i stany braku pokrycia / rekordów / awarii. Historyczne dane nie są Alertami.
Szczegóły bramek: `docs/data/gios/07-operation-gates.md`. Weryfikacja na żywo `dane.gios.gov.pl` nie jest możliwa z
środowiska agenta (egress) — robi ją operator (`--validate-only`).

| Zadanie | Zakres | Status |
|---|---|---|
| GIOS-00 | evidence i bramki per operacja, wpisy `gios_*` w Source Registry | 🟡 PARTIAL — rejestr i macierz gotowe (PR-A), **żywa weryfikacja po stronie operatora** (B-8) |
| GIOS-01 | ADR-032, kontrakt `/neighborhood`, flagi | ✅ ADR-032 (kontrakt OpenAPI przy pierwszej implementacji) |
| GIOS-02 | wspólny fundament ingestu (`app/gios_open/`): klient (BLAD przy HTTP 200, retry ≤ 2, limiter na każdą próbę), paginacja (pętla / nakładanie / limit stron = błąd, koniec = potwierdzona pusta strona), snapshoty staging → active z blokadą per usługa w bazie, kwarantanna, `probe` dla operatora | ✅ DONE (PR-B, migracja 0017); bez żadnego connectora; paginację na żywo rozstrzyga `probe` (B-6) |
| GIOS-03 | rozszerzenie bieżącego powietrza GIOŚ (audyt connectora, wielostronicowe sensory, indeks) | 🟡 PARTIAL — **03a ✅** zapis wszystkich niepustych wartości z odpowiedzi `getData` (`size`, okno ok. 66 h, luki uzupełniane, zmiana czasu 02:00 ×2); **03b ✅** `GET /api/v1/air/history?geo_area_id=&param=&hours=` (jeden parametr, ta sama stacja co `/air/latest`, z naszej bazy, luki jawne `gaps`, `availability`: available / no_station / no_data); 🟡 03c mini-wykres 24–48 h na ekranie Powietrze — kod scalony w PR #147/#148: wybór 7 parametrów, oś czasu z lukami, jawne zero, jednostka/stacja/aktualność, lista pomiarów dla dostępności; QA na urządzeniu po nowym UI, zgodnie z decyzją właściciela. Indeks GIOŚ, paginacja sensorów i preferencja bieżącej stacji: scalone w PR #148 (ADR-033); CI backend/mobile zielone, indeks pod flagą off, migracja i rollout do wykonania |
| GIOS-04 | hałas — pomiary historyczne (import ręczny, najbliższy punkt do 10 km) | ⏸ ON HOLD — 🟡 PARTIAL — backend gotowy (parser, import `--validate-only`/`--file`, kwarantanna, migracja 0018); probe paginacji zaliczony na prawdziwym GIOŚ (346 rekordów / 7 stron, Droga × ŚLĄSKIE × 2024); `--validate-only` zaliczony (346/346, 0 odrzuconych); pełny import kraju odnotowany w `07-operation-gates.md`; otwarte bramki i QA pozostają w tym dokumencie|
| GIOS-05 | hałas — zasięgi i ekspozycja punktu | ⏸ ON HOLD — ⛔ BLOCKED — próbka polygonu + CRS (B-2) |
| GIOS-06 | PRTR — lista zakładów w obszarze administracyjnym | ⏸ ON HOLD — ⛔ BLOCKED — brak słownika powiat → TERYT (B-9); liczby emisji dodatkowo — jednostki (B-1) |
| GIOS-07 | rejestr ZZR/ZDR i historia zdarzeń | ⏸ ON HOLD — ⬜ TODO; zdarzenia UNVERIFIED (brak próbki)|
| GIOS-08 | wody powierzchniowe — plan monitoringu + discovery wyników | ⏸ ON HOLD — ⛔ BLOCKED dla UI — brak niepustego rekordu i wyników/geometrii (B-3, B-4) |
| GIOS-09 | wody podziemne | ⏸ ON HOLD — ⛔ BLOCKED dla geo — CRS i polygony JCWPd (B-2, B-3) |
| GIOS-10 | powietrze historyczne (16 operacji) | ⏸ ON HOLD — brak bieżących pomiarów w tym zakresie |
| GIOS-11 | NEC (ekosystemy) | ⏸ ON HOLD — ⬜ TODO; stanowiska IMPLEMENTABLE (gate niezaliczony), wyniki UNVERIFIED |
| GIOS-12 | pozostałe obszary (gleby, PEM, promieniowanie, przyroda, morze, CLC, INSPIRE) | ⏸ ON HOLD — ⬜ TODO — tylko discovery |
| GIOS-13 | API `/neighborhood` + ekran + flagi + runbook | ⏸ ON HOLD — 🟡 PARTIAL — `GET /api/v1/neighborhood` + flaga `NEIGHBORHOOD_NOISE_ENABLED` (domyślnie off) i ekran „Twoja okolica” (wiersz na Start tylko przy `enabled`) gotowe; niezweryfikowane na urządzeniu i na prawdziwych danych GIOŚ|

---

## 3. Backend — checklist z §10 (MVP zawiera)

| Element | Status |
|---|---|
| FastAPI | ✅ DONE |
| PostgreSQL | ✅ DONE |
| PostGIS | 🟡 PARTIAL — fundament gotowy (TASK-6.2, PR #70, ADR-019): migracja `0011` (`postgis`, `geo_areas.teryt_code`/`boundary`/`weather_polling_active`), obraz `postgis/postgis:16-3.4` w CI/compose. **Brak danych**: granice gmin PRG nie są załadowane — licencja zatwierdzona przez właściciela 2026-10-02, **import czeka na operatora** (`docs/data/prg-import.md`, sekcja 6) |
| Redis (cache/stan krótkotrwały) | ⬜ TODO — nie wdrożone; obecnie wszystko czyta z PostgreSQL bezpośrednio |
| Connector framework (fetch/parse/validate/normalize) | ✅ DONE — wzorzec ustalony i powtórzony w 6 connectorach (`gios`, `open_meteo`, `open_meteo_pollen`, `imgw_hydro`, `imgw_warningshydro`, `imgw_warningsmeteo` częściowo); `prg_gminy` to importer jednorazowy z lokalnego pliku, nie connector sieciowy |
| Scheduler | ✅ DONE — ADR-007, loop-based, per-job interval gating, izolacja awarii (rule #1, `_run_job_safely`) |
| Workers (oddzielny proces/kolejka) | ⬜ TODO — świadomie NIE zrobione (ADR-007): scheduler w jednym procesie wystarcza przy obecnej skali, przejście na worker/queue dopiero gdy realnie potrzebne |
| Normalization / validation | 🟡 PARTIAL — wzorzec (fetch/parse/validate/normalize) wdrożony w pełni w 5 connectorach (`gios`, `open_meteo`, `open_meteo_pollen`, `imgw_hydro`, `imgw_warningshydro`); `imgw_warningsmeteo` i `imgw_weather` mają implementację pod flagami (ADR-034); nowe API czasu/jednostek nadal oczekują weryfikacji |
| Freshness | 🟡 PARTIAL — per-wiersz freshness (FRESH/RECENT/STALE) dla `/air`, `/hydro`, `/alerts`, `/weather`; **source-level freshness z UNAVAILABLE (ADR-012, TASK-7.4)** dla ostrzeżeń (#59, #61) i hydrologii (#62): tabela `source_status` zapisywana przez scheduler i ręczne CLI, `source_status` w `/alerts/latest`, `/hydro/latest` i agregacie; mobile nie pokazuje „brak ostrzeżeń/alarmów”, gdy źródło milczy lub status zestarzał się na urządzeniu (>6h); `air`/`weather` w agregacie też niosą `source_status` (TASK-7.3, PR #78); pyłki mają `source_status` w `/pollen/latest` (PR #71). Widok operatorski: `GET /api/v1/health/sources` (TASK-13.1, PR #69) |
| Provenance / raw ingestion (§33-34) | ✅ DONE — `source_fetches` (surowy payload, endpoint, wersja parsera, status walidacji) + nullable FK `source_fetch_id` na `Measurement`/`Alert`/`WeatherSnapshot`/`Forecast`; wszystkie connectory istniejące w PR #65 (4; pyłki dołączyły w PR #71); retencja payloadu 7/14/30 dni, metadane zostają; zapis best-effort, awaria nie psuje ingestu (ADR-014, TASK-3.1, PR #65). Rekordy sprzed migracji 0009 mają FK NULL |
| Outdoor Interpretation Engine (§52) | 🟡 PARTIAL — `app/outdoor.py`: deterministyczny GOOD/MODERATE/POOR/UNKNOWN + `reasons[]`/`missing[]` (ADR-016, PR #64); progi PM/UV/wiatr ze źródłami (PM/NO₂/O₃ czytane z `air_index.BANDS`), temperatura/opady/widoczność oznaczone „do kalibracji”; NO₂/O₃ (grupy opcjonalne) i burza WMO ≥95 → POOR w silniku (addendum ADR-016, PR #87). Podłączony: blok `outdoor` per obszar w `dashboard_latest()` i `OutdoorCard` na mobile (TASK-7.7/7.8, PR #68); preferencje „outdoor” użytkownika (TASK-12.4) nie istnieją |
| Geo matching | 🟡 PARTIAL — nearest-station GIOŚ↔geo_area oraz **point-in-polygon lat/lon → gmina** (`app/geo.py::resolve_gmina`, `POST /api/v1/geo/resolve`, TASK-6.2 punkty 1–6, PR #70, ADR-019). Resolver bez danych zwraca `None` (granice gmin niezaładowane). Stacje GIOŚ (ADR-025): katalog `gios_stations` (≤ 1×/dobę), polling **3 najbliższych stacji na obszar** (≤ 100 km), API wybiera **najbliższą stację Z DANYMI** (`geo.pick_air_station`, PR #104; dystans i `coverage` dotyczą stacji faktycznie użytej), `assignment_method` w dashboardzie i `/air/latest?geo_area_id=`; `GIOS_STATION_IDS` nadal override. Alerty dopasowane do obszaru (patrz 2.6). Zawężenie do lokalizacji (ADR-026): `/dashboard/latest?geo_area_id=` (404 dla nieznanego; obszar bez pollingu → weather/forecast/pollen puste), `GET /areas`, `POST /geo/locate` (point-in-polygon → najbliższy aktywny obszar ≤ 25 km jawnie jako `nearest_area` → `out_of_range`); GPS używa `POST /places/nearest` (patrz niżej). Nie zrobione: `/hydro/latest` po lokalizacji (TASK-9.5), aktywacja pollingu wybranej gminy (TASK-12.2) |
| Dowolna miejscowość (TASK-6.3, ADR-029) | 🟡 PARTIAL — rejestr `places` (migracja `0014`, import GeoNames PL, nazwy powiatów/województw → `label`), `GET /api/v1/places?q=` (prefiks bez diakrytyków), `POST /places/{id}/activate` (limit aktywnych z budżetu Open-Meteo, po ADR-030 ~280, TTL 7 dni, pierwszy fetch w minuty), **`POST /places/nearest`** (najbliższa miejscowość ≤ 30 km dla GPS, bez zapisu współrzędnych, PR #106), jawny `coverage` powietrza (`exact` ≤ 10 / `nearby` ≤ 50 / `regional` ≤ 100 km / `none`; pogoda i pyłki = `grid`), `regional` poza werdyktem „Na dwór”. Rejestr zaimportowany lokalnie przez właściciela (smoke test 2026-10-02); **produkcja: import po wdrożeniu** i formalny gate `geonames_pl` (sekcja 6). UI wyboru ✅ (TASK-12.7, PR #88), GPS 🟡 (PR #106) |
| Alert Engine | ⬜ TODO |
| Notification Engine | ⬜ TODO |
| REST API | 🟡 PARTIAL — `/air`, `/weather`, `/hydro`, `/alerts`, `/pollen` (+ `/pollen/calendar`), `/dashboard/latest` (`?geo_area_id=`), `/areas`, `/places`, `/places/{id}`, `/places/{id}/activate`, `/places/nearest`, `/geo/resolve`, `/geo/locate`, `/devices`, `/health`, `/health/sources`; wersjonowane pod `/api/v1/`. Brak `/water` (kąpieliska ⛔). Kontrakt OpenAPI + typy TS generowane i sprawdzane w CI (TASK-2.1, ADR-024) |
| Logging | ✅ DONE — `logging` per connector/scheduler, ustandaryzowane |
| Source health (TASK-13.1) | 🟡 PARTIAL — `GET /api/v1/health/sources` (freshness FRESH/RECENT/STALE/UNAVAILABLE, ostatnia próba/sukces, zsanityzowany `last_error`, budżet dzienny), scheduler loguje raz na zmianę stanu (PR #69; ADR-012). **Brak** historii runów i telemetrii §44 (duration, records processed, validation errors, duplicate/stale rate) — wymaga osobnego ADR i migracji; pyłki w rejestrze dołączone w PR #71 |
| Device registration (TASK-10.1, ADR-017) | 🟡 PARTIAL — backend: `POST/DELETE /api/v1/devices` bez konta, sekret urządzenia (SHA-256), rate limit in-memory, migracja `0010` (PR #67). Realna wysyłka push wymaga kluczy FCM/APNs (sekcja 6); klient mobilny (10.5), preferencje (10.3a) i Notification Engine (10.2) ⬜ |
| Monitoring | 🟡 PARTIAL — dzienny licznik wywołań per źródło + WARNING przy 70% limitu (TASK-13.1a, PR #55) i source health (wiersz wyżej); brak zewnętrznego monitoringu/alertingu (TASK-13.2) |
| Provider config Free→Paid (TASK-13.4, ADR-022) | 🟡 PARTIAL — (kod gotowy, PR #73; do ✅ po pierwszym żądaniu testowym z prawdziwym kluczem komercyjnym i potwierdzeniu hosta Air Quality) endpointy Open-Meteo i `OPEN_METEO_API_KEY` w env (domyślnie Free), klucz maskowany w wyjątkach/logach/provenance; przejście na plan komercyjny = tylko config. **Open-Meteo APPROVED dla obecnej architektury (pisemne potwierdzenie, ADR-031, 2026-10-02)** — plan komercyjny wymagany dopiero przed reklamami lub płatnymi/premium funkcjami (`docs/release/business-gates.md`); darowizny na Free dozwolone. **Przed monetyzacją: checklista w ADR-003** (plan komercyjny Open-Meteo, env produkcyjne, licencje pozostałych źródeł). Host `customer-air-quality-api…` niezweryfikowany wprost |
| Backup | 🟡 PARTIAL — `backup.sh`/`restore_test.sh`/`test_backup_restore.sh` gotowe i przetestowane na Postgres 16 (dump+sekrety szyfrowane age bez plaintextu na dysku, spójna migawka dump+manifest, walidacja manifestu, limit wieku backupu, hasło poza argv); brak: realny off-VPS storage provider, zaplanowane uruchamianie na produkcji (TASK-15.2/15.3), wydzielony host weryfikacyjny |

---

## 4. Mobile — checklist z §10 (MVP zawiera)

| Element | Status |
|---|---|
| Home / Dashboard | 🟡 PARTIAL — zakładka „Start” wg production-ui-v1 (PR #102; logika `lib/home.ts`, `lib/start.ts`): kompaktowy nagłówek (miejscowość ⌄, data, temperatura + ikona pogody, min/max) → **HeroVerdict** „Na dwór” LIVE z ludzkim copy i rozwijanymi powodami (techniczne braki tylko w szczegółach, brak mocków) → **kafelki** Powietrze / Pogoda / Pyłki / UV (UV tylko przy realnej wartości; niedostępne = neutralne „Niedostępne”; tint domeny na całym kafelku) → podgląd alertów (lokalny / do sprawdzenia / nieznany / brak — tytuł i „Stopień X” dosłownie, bez własnej skali kolorów) → źródło i licencje. Skeletony, stany offline/brak danych, odświeżanie; stare dane oznaczone jako stare. Sekcja „Co możesz dziś robić?” NIE jest renderowana (brak backendu). **Niezweryfikowane na urządzeniu** |
| Nawigacja + design system | 🟡 PARTIAL — Expo Router, tab bar tylko Start / Alerty / Ustawienia (Ionicons; etykiety skalowane z fontem, pasek rośnie z `fontScale`), ekrany szczegółowe jako ukryte zakładki; tokeny (`lib/theme.ts`, kontrast ≥ 4,5:1 sprawdzany testem w obu paletach), wspólne komponenty (Card, IconBox, SectionHeader, StatusTile, SettingsRow…), jasny/ciemny motyw (wybór Systemowy/Jasny/Ciemny), safe-area, a11y (role/etykiety, **min. dotyk 48 dp**, status = glif + słowo + kolor; `docs/ui/a11y-review.md`). Bez NativeWind (ADR-027) — StyleSheet + tokeny. **Niezweryfikowane na urządzeniu** (TalkBack, 130/200% fontu, Back) |
| Mapa ekranów UI i polityka mocków | 🟡 PARTIAL — dokumentacja: [`docs/ui/screen-map.md`](ui/screen-map.md) (część historyczna, odświeżona adnotacją po PR #117) + kontrakt wizualny [`docs/ui/production-ui-v1.md`](ui/production-ui-v1.md) i `production-components-v1.md`; ADR-028 (mocki UI za flagą, zakaz mocków danych bezpieczeństwa). Produkcyjny UI nie używa mocków danych; tematy „Co chcesz śledzić?” usunięte decyzją production-ui-v1 |
| Alerts (ekran) | 🟡 PARTIAL — zakładka Alerty (PR #94, #102): sekcje „Dla Twojej lokalizacji” (`local_alerts`), „Do sprawdzenia” (`unresolved`, nigdy ukryte) i „Pozostałe w Polsce” (zwinięte); „brak ostrzeżeń” tylko przy potwierdzonym świeżym źródle; karta alertu (neutralny styl, chip „Dotyczy Twojej lokalizacji”, „stopień X” dosłownie — ADR-009), ekran szczegółu z treścią źródłową verbatim (reguła #10), stany wody IMGW. Bez powiadomień push. **Niezweryfikowane na urządzeniu** |
| Ekrany szczegółowe: Powietrze, Pogoda, Pyłki, Rzeki | 🟡 PARTIAL — Powietrze (stacja, odległość, metoda, skala EAQI, parametry; informacja o parametrze, którego stacja nie przekazuje — PR #123), Pogoda (godzinowa prognoza 48 h z realnych danych, dobowa), Pyłki (prognoza CAMS + kalendarz pylenia), Stany rzek (lista stacji IMGW z progami) — PR #93, #95, #102; źródło i atrybucje na każdym; **niezweryfikowane na urządzeniu** |
| Settings | 🟡 PARTIAL — lista pozycji: Lokalizacja (zmiana miejscowości), Wygląd (Systemowy/Jasny/Ciemny), Dostępność, Prywatność (opis zgodny z kodem; pełna polityka: szkic `docs/privacy/privacy-policy-draft.md`, 🟡 do uzupełnienia i publikacji), Źródła danych (atrybucje z backendu), O aplikacji. Brak kont, powiadomień i profilu (poza MVP / ⬜) |
| foreground location (GPS) | 🟡 PARTIAL — „Użyj mojej lokalizacji” na ekranie Lokalizacja: jednorazowy odczyt foreground (`expo-location`, tylko coarse; FINE/background/foreground-service zablokowane w `app.config.js`) → `POST /api/v1/places/nearest` (najbliższa miejscowość z rejestru `places` w 30 km, bez zapisu współrzędnych) → użytkownik potwierdza wybór. Wymaga zaimportowanych GeoNames; poza zasięgiem/bez importu = uczciwy komunikat. **Niezweryfikowane na urządzeniu** |
| ręczny wybór lokalizacji + Welcome | 🟡 PARTIAL — Welcome (pierwsze uruchomienie, copy wg kontraktu asset packu v2: tło-zdjęcie + natywny znak/tekst/CTA/scrim; rastry zainstalowane, PR #90) → „Ustaw lokalizację” (wyszukiwarka `/places` + lista miast z `/areas`, aktywacja, jedna lokalizacja w AsyncStorage) → Start; zmiana z nagłówka Start / Ustawień; zapamiętany obszar wygasły/404 → wybór z komunikatem (TASK-12.7, 12.17, PR #88); Back z Lokalizacji do Welcome i reset historii po pierwszym wyborze (PR #110); finalny Welcome (PR #111–#117); GPS: patrz wiersz niżej. **Niezweryfikowane na urządzeniu/emulatorze** (brak środowiska w PR). Brak: heartbeat instalacji (TASK-12.2); tematy „Co chcesz śledzić?” usunięte decyzją production-ui-v1 (TASK-12.13 SUPERSEDED), dane miejscowości na serwerze do czasu importu GeoNames (`geonames_places.ingest --download`) |
| push notifications | ⬜ TODO — (backend rejestracji urządzeń 🟡 w sekcji 3; klient mobilny i wysyłka nie istnieją) |
| profil użytkownika | ⬜ TODO |
| podstawowe preferencje | ⬜ TODO |
| source transparency | ✅ DONE — `dashboard_latest()` zwraca `source`+`attribution`+`observed_at` dla air i weather, mobile renderuje atrybucję pod każdą sekcją (TASK-7.1, PR #49) |
| freshness (UI) | ✅ DONE — etykieta freshness pokazywana per sekcja |
| loading / error / stale / no-data states | ✅ DONE dla powietrza i pogody — loading/error/ready + FRESH/RECENT/STALE/UNAVAILABLE i „brak danych” (etykieta wieku, przygaszenie, efektywna świeżość = worst z danych i `source_status`; TASK-7.3, PR #78). Prognoza dzienna: tylko etykieta freshness |

---

## 4a. Prywatność / sklepy

Szkic polityki prywatności: [`privacy/privacy-policy-draft.md`](privacy/privacy-policy-draft.md) — 🟡 szkic do
przeglądu właściciela (pola administratora, hostingu i logów do uzupełnienia; wymagana publikacja pod stałym
adresem https przed Google Play).

## 4b. Wdrożenie (VPS)

Zestaw gotowy, **niewdrożony** (brak VPS): [`../docker-compose.prod.yml`](../docker-compose.prod.yml),
`.env.prod.example`, `infrastructure/caddy/Caddyfile`, runbook [`release/vps-runbook.md`](release/vps-runbook.md).
Statyczna walidacja compose OK; Caddyfile i całość niezweryfikowane na serwerze. Wejście na produkcję
nadal wymaga TASK-15.0 (wszystkie źródła `APPROVED`) i decyzji właściciela (VPS, domena, hosting).

## 5. Poza MVP (§11) — celowo nietykane

Zgodnie z Master Planem, świadomie NIE robimy: mapy, uniwersalnego Green
Index, background location, obowiązkowego konta, PWA, rozbudowanego
social/community, zaawansowanej monetyzacji, pełnej historii danych,
rozbudowanych funkcji premium. Nie zmieniać bez decyzji użytkownika + ADR.

Moduł „Twoja okolica” (ADR-032, decyzja właściciela 2026-10-03) jest rozszerzeniem poza pierwotnym MVP, ale nie łamie tej listy:
nie ma mapy, wspólnego wskaźnika (Green Index), konta ani background location, a dane historyczne to opublikowane rejestry z
okresem i źródłem, nie własna historia szeregów czasowych.

---

## 6. Aktywne blokady (wymagają decyzji lub zewnętrznego zdarzenia)

| Blokada | Co odblokuje | Task |
|---|---|---|
| Aktywacja nowych adapterów IMGW | Aktywna fixture już pozyskana; nadal potwierdzić timezone per API, jednostki/poziomy, wysokości lokalizacji i gate przed rolloutem | ADR-034, `docs/data/imgw/README.md` |
| Kąpieliska: brak źródła BIEŻĄCEGO statusu | Status BIEŻĄCY wymaga zgody/API od GIS (`sk.gis.gov.pl` to HTML bez API i licencji) lub innego zatwierdzonego źródła (dane.gov.pl/WIOŚ — kandydaci, niesprawdzeni). EEA po potwierdzeniu licencji wydania 2025, schematu i filtra PL odblokuje tylko rejestr + klasyfikację roczną, NIE status bieżący. Pełny Gate §38 (APPROVED) dla każdego wybranego źródła | TASK-11.1/11.2, ADR-021 |
| Geo-matching alertów — dokładność poniżej województwa | Dopasowanie na poziomie województwa jest (PR #81, #103, #105; ADR-013). Powiat/gmina wymaga, by źródło podawało TERYT (hydro: tylko `kod_zlewni`; meteo: fixture z kodami powiatów pozyskana, exact matching pod flagą, ADR-034) lub zbioru zlewnia↔gmina. Seedowe miasta mają kody TERYT (migracja `0016`), miejscowości z rejestru — województwo z GeoNames; granice gmin PRG nie wpłyną na to, dopóki źródło alertów nie poda dokładniejszego obszaru | TASK-9.5 |

### Blokady po stronie człowieka (kod nie przesunie tego dalej)

| Do zrobienia | Czego dotyczy | Task / źródło |
|---|---|---|
| ~~Zatwierdzić licencję PRG~~ ✅ zatwierdzone przez właściciela 2026-10-02 (`source-registry.md`); **do zrobienia: import** wg `docs/data/prg-import.md`. Pobrać `00_jednostki_administracyjne.zip` → GeoJSON gmin → import (`python -m app.connectors.prg_gminy.ingest`). **Po co:** granice gmin pozwalają zamienić współrzędne (GPS/miejscowość) na dokładną gminę (point-in-polygon, reguła #9) i nadać miejscowościom z rejestru kod TERYT gminy; dziś alerty dla nich dopasowujemy tylko po województwie (PR #105), a to jedyny poziom, który IMGW hydro i tak podaje. Plik trzeba przygotować i przekonwertować (SHP/GML → GeoJSON WGS84) | Bez tego `POST /geo/resolve` zwraca `None`, a 6.2 zostaje 🟡; dopasowanie alertów zostaje na poziomie województwa | TASK-6.2, `docs/tasks/TASK-6.2-geo-engine-foundation.md` |
| GeoNames: import u właściciela wykonany lokalnie (smoke test 2026-10-02: wyszukiwarka i `places/nearest` działają); **na VPS** powtórzyć import (`geonames_places.ingest --download`) i formalnie przejść Source Approval Gate (`geonames_pl`, CC BY 4.0) | Bez importu na serwerze produkcyjnym `GET /places` zwraca pustą listę (wybór dowolnej miejscowości i GPS nie działają) | TASK-6.3, ADR-029, `source-registry.md` |
| Kontakt z GIS ws. udostępnienia API/danych o kąpieliskach (albo wybór innego zatwierdzonego źródła); potwierdzić licencję EEA 2025, jeśli wystarczy rejestr + klasyfikacja roczna | Odblokowanie 2.4 | TASK-11.1/11.2, ADR-021, `docs/tasks/TASK-11-bathing-water.md` |
| IMGW: ustalić, czy hydro/ostrzeżenia to dane o wysokiej wartości (HVD, rozp. UE 2023/138) i jak ma się CC BY-NC-ND 4.0 zbioru plikowego do API; w razie potrzeby umowa (biznes@imgw.pl) | Przed monetyzacją (checklista ADR-003) | ADR-003, `source-registry.md` |
| Open-Meteo: ~~pisemne potwierdzenie dla Patronite~~ ✅ otrzymane 2026-10-02 (ADR-031; **uzupełnić datę/wątek korespondencji** w `docs/business/provider-licensing.md`); nadal: ceny planów komercyjnych (niezweryfikowane), potwierdzenie hosta Air Quality (`customer-air-quality-api…`) i pierwsze żądanie z prawdziwym kluczem — dopiero przed reklamami/premium (`docs/release/business-gates.md`) | TASK-13.4 🟡 → ✅; przed monetyzacją | ADR-003, ADR-022 |
| OBAŚ — nawiązać kontakt (rzeczywiste pomiary pyłków; dziś kandydat, nic niezweryfikowane) | Opcjonalne uzupełnienie pyłków pomiarami (osobny byt Measurement) | `source-registry.md` (`obas`), ADR-022 |
| Klucze FCM/APNs (konta deweloperskie Google/Apple) jako zmienne środowiskowe | Realna wysyłka push; walidacja iOS wymaga konta Apple Developer | TASK-10.1 🟡, 10.2 |
| Skasować pusty plik `pr.json` w katalogu głównym repo, jeśli jest w lokalnej kopii (nie jest śledzony w `main`) | Higiena repo | — |
| Import granic gmin PRG wg `docs/data/prg-import.md` (zatwierdzone 2026-10-02) | `POST /geo/resolve` zwraca gminę; kody TERYT dla miejscowości | TASK-6.2 |
| VPS, domena API i hosting (kraj → polityka prywatności); uzupełnienie pól `[UZUPEŁNIĆ]` w `docs/privacy/privacy-policy-draft.md`, publikacja pod stałym adresem https; produkcyjny profil EAS z HTTPS | Wdrożenie (zestaw gotowy: `docs/release/vps-runbook.md`), Google Play | TASK-15.x, ROADMAP 4a/4b |
| GIOŚ „Twoja okolica”: (1) **weryfikacja na żywo** na maszynie z dostępem do `dane.gios.gov.pl` (`--validate-only`, gdy connector powstanie; wynik do Source Registry — status `IMPLEMENTABLE` → `APPROVED`); (2) **pytania techniczne do GIOŚ** (treść gotowa w `docs/data/gios/03-licensing-and-source-gates.md`): jednostki PRTR, semantyka `liczbaRekordow`, CRS wód podziemnych i hałasu, cykl i limity, strefa czasowa `wynik.data`, geometria zakładów, wyniki jakości wód powierzchniowych — **wysłanie to decyzja właściciela, nic nie zostało wysłane** | Zmiana `IMPLEMENTABLE` → `APPROVED`, odblokowanie liczb PRTR (B-1), geometrii (B-2, B-3, B-5), wyników wód (B-4), cyklicznego pollingu (B-6) | GIOS-00, `docs/data/gios/07-operation-gates.md` |
| Build APK i weryfikacja na telefonie: zrzuty (Welcome jasny/ciemny, Lokalizacja z GPS, Start, Pogoda, Powietrze, Alerty, Ustawienia, font 130/200%, ikona launchera), TalkBack, Back na Androidzie — lista w `docs/ui/a11y-review.md` i `docs/mobile/run-and-test.md` | Zamknięcie punktów DoD z PR #102 i zmiana wielu statusów 🟡 na ✅ | TASK-12.x, PR #102 |

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
| #47 | Backup + test odtworzenia (TASK-1.1, §68): age, spójna migawka, manifest, hasło poza argv |
| #48 | GIOŚ: pełny zestaw parametrów MVP (PM10/NO2/SO2/O3/CO/C6H6, TASK-4.1) + fix jednostki CO + izolacja awarii per-param |
| #49 | Source transparency w `dashboard_latest()` + mobile (TASK-7.1) |
| #50 | Open-Meteo: punkt rosy/widoczność/UV index z `hourly` dopasowane do godziny `current` (TASK-5.4), domyka pozostałe MVP pola §5; per-param freshness na `/weather/latest` |
| #51, #53, #54 | Typed `response_model` dla `/air/latest`, `/hydro/latest`, `/alerts/latest` (TASK-API-1/3/4) |
| #52 | Typed `response_model` dla `/weather/latest` i `/weather/forecast` (pola czasowe jako `datetime`) |
| #55 | Dzienny licznik wywołań per źródło + alert 70% (TASK-13.1a): jednostki rozliczeniowe Open-Meteo, każda próba HTTP liczona przed wysłaniem, atomowy inkrement |
| #56 | Per-param `observed_at`/`freshness` pogody w `dashboard_latest()` + mobile (Codex P1 z PR #50, rezydualny w agregacie) |
| #57 | Prognoza w `dashboard_latest()` + mobile (TASK-5.5), wspólny helper `forecasts_by_area()` z `/weather/forecast` |
| #58 | Ostrzeżenia IMGW w `dashboard_latest()` + mobile, jawnie ogólnokrajowe do czasu geo-matchingu (TASK-7.2) |
| #59 | Source-level freshness / UNAVAILABLE dla ostrzeżeń (ADR-012, TASK-7.4) |
| #60 | Docs: sync BACKLOG/ROADMAP po #45 #47 #57 #58 |
| #61 | Follow-up #59: status starzeje się na urządzeniu (6h, timer 60 s), brak `source_status` bez wyjątku, `last_success_at` z przyszłości = STALE |
| #62 | Hydrologia na mobile: „Stany wody — cała Polska” (WARNING/ALARM), `attribution` + `source_status` w `/hydro/latest`, CLI hydro zapisuje `source_status` (TASK-7.2) |
| #63 | Europejski indeks jakości powietrza EAQI/EEA (ADR-015, TASK-4.2): `air_index.py`, `index` w `/air/latest` i dashboardzie, mobile `AirIndexBadge`; indeks GIOŚ odłożony |
| #64 | Outdoor Interpretation Engine (ADR-016, TASK-7.6) — czysty moduł, niepodłączony do API |
| #65 | Provenance: `source_fetches` + `source_fetch_id`, retencja payloadów (ADR-014, TASK-3.1) |
| #66 | Sync ROADMAP/BACKLOG po #61 #62 #64 #65 (docs) |
| #67 | Rejestracja urządzeń pod push bez konta: `POST/DELETE /api/v1/devices`, model `Device`, migracja `0010`, rate limit (ADR-017, TASK-10.1) — 🟡, bez kluczy FCM/APNs |
| #68 | `outdoor` w `dashboard_latest()` + `OutdoorCard` na mobile (TASK-7.7/7.8) |
| #69 | Source health: `GET /api/v1/health/sources` + logi zmian stanu w schedulerze (TASK-13.1, ADR-012) — 🟡, bez historii runów/telemetrii §44 |
| #70 | Geo Engine — fundament (TASK-6.2, ADR-019): PostGIS, migracja `0011`, importer `prg_gminy`, `resolve_gmina`, `POST /api/v1/geo/resolve`, `weather_polling_active`; bez danych gmin — 🟡 |
| #71 | Pyłki backend (TASK-8.5–8.7, ADR-020): `open_meteo_pollen`, `PollenSnapshot`, scheduler, `GET /api/v1/pollen/latest`; karta mobile i agregat (8.8/8.9) osobno |
| #72 | Kąpieliska: research źródeł + ADR-021 (Proposed), registry; TASK-11.1 częściowo, 11.2 ZABLOKOWANE — bez kodu |
| #73 | Provider config Free→Paid (ADR-022, TASK-13.4): endpointy/klucz Open-Meteo w env, maskowanie klucza, FREE-FIRST (reguła #17), checklista przed monetyzacją (ADR-003) |
| #74 | Docs: sync ROADMAP/BACKLOG po #61–#73 (statusy, blokady po stronie człowieka) |
| #75 | Pyłki w dashboardzie: blok `pollen` w `dashboard_latest()` (TASK-8.9, izolowany, freshness + `source_status`) + karta mobile `PollenCard`/`pollen.ts` (TASK-8.8); progi sezon/szczyt EAACI wg CAMS/EEA (ADR-020) |
| #76 | Kalendarz pylenia: statyczne dane referencyjne + `GET /api/v1/pollen/calendar` (ADR-023, TASK-8.10); 8 taksonów (z trawami), ambrozja/pokrzywowate niezweryfikowane |
| #77 | Kontrakt API (TASK-2.1, ADR-024): `response_model` `DashboardResponse` dla `/dashboard/latest` (1:1 z dotychczasowym JSON-em), `openapi.json` + typy TS generowane bez zależności w `packages/api-contract`, kroki CI `--check`, `contract.test.ts` w mobile |
| #78 | Stany stale/no-data dla air i weather (TASK-7.3): `source_status` w blokach dashboardu, efektywna świeżość + etykieta wieku + przygaszenie w UI; prezentacja pól pogody na mobile (TASK-5.4) |
| #79 | Stacje GIOŚ per aktywny obszar (TASK-6.2 (7), ADR-025): katalog `gios_stations` (migracja `0013`, odświeżany ≤ 1×/dobę), `geo.select_stations` (nearest ≤ 50 km, tie-break po id), polling stacji przypisanych do `polling_areas` (`GIOS_STATION_IDS` = override), `assignment_method` w dashboardzie i `/air/latest?geo_area_id=` |
| #80 | Mobile: karta „Kalendarz pylenia — typowy sezon” (TASK-8.10 UI, `pollenCalendar.ts`/`PollenCalendarCard`, osobny fetch `/pollen/calendar`, pusty `active` ≠ „nic nie pyli”) + typy `index`/`alerts`/`hydro`/`outdoor`/`aqi` z kontraktu API (follow-up TASK-2.1) |
| #81 | Alerty ↔ obszar (TASK-9.5 część, ADR-013): `app/alert_geo.py` (województwo → TERYT, fail-safe `unresolved`), `?geo_area_id=` w `/alerts/latest`, `geo_match`, `local_alerts` w dashboardzie, kontrakt zregenerowany; ADR-013 = granica Measurement/Forecast/Event/Alert/Notification (`Event`/`Notification` nie powstały) — 🟡 |
| #82 | Wybór lokalizacji w API (TASK-6.2 (8), ADR-026): `/dashboard/latest?geo_area_id=`, `GET /areas`, `POST /geo/locate` (nearest active area ≤ 25 km jawnie, `out_of_range`), `weather_polling_active` w `DashboardArea`, kontrakt zregenerowany; bez klienta mobile — 🟡 |
| #83 | Mobile: fundament UI — zakładki Dziś/Alerty/Ustawienia (Expo Router), tokeny designu + ciemny motyw (kontrast testowany), safe-area, a11y, stany pusty/błąd bez wskazówek deweloperskich w produkcji, rozbicie `index.tsx` na komponenty; ostrzeżenia i stany wody przeniesione na Alerty (nadal cała Polska) |
| #84 | Docs: mapa ekranów UI (`docs/ui/screen-map.md`), ADR-028 (mocki UI, Proposed), zadania TASK-7.9, TASK-8.11, TASK-12.10–12.19 w BACKLOG — bez kodu |
| #85 | Dowolna miejscowość w Polsce (TASK-6.3, ADR-029): rejestr `places` (migracja `0014`, import GeoNames PL z lokalnego pliku), `GET /places`, `POST /places/{id}/activate` (limit z budżetu Open-Meteo, TTL 7 dni, pierwszy fetch w minuty), jawny `coverage` powietrza `exact/nearby/regional/none` + `grid` dla pogody/pyłków, polling GIOŚ do 100 km, `regional` poza werdyktem „Na dwór”, kontrakt zregenerowany; bez klienta mobile i bez danych (plik GeoNames do zaimportowania) — 🟡 |
| #86 | Mobile: struktura ekranu Start wg Frontend UX/UI Spec v1 — zakładki Start/Alerty/Ustawienia, nagłówek, Hero Verdict, karty statusu (data-driven), status ostrzeżeń (brak ≠ nie sprawdzono), skeletony per moduł, stale/partial failure; bez zmian backendu |
| #87 | Silnik „Na dwór”: NO₂/O₃ (opcjonalne grupy, progi z `air_index.BANDS`) i burza (`weather_code` ≥95 → POOR); addendum ADR-016; kontrakt bez zmian |
| #88 | Mobile: Welcome → „Ustaw lokalizację” → Start (TASK-12.17, 12.7): lokalna pamięć jednej lokalizacji (AsyncStorage, wersjonowana, odporna na uszkodzenie), wyszukiwarka `/places` (debounce 300 ms, latest-wins, stany pusty/błąd/loading), aktywacja `POST /places/{id}/activate` (429/503/budżet/limit → uczciwe komunikaty), zmiana lokalizacji z nagłówka Start i Ustawień, guard routingu, jawne `coverage` powietrza; bez GPS, bez tematów (TASK-12.13), bez zmian backendu — 🟡 |
| #89 | Prognoza godzinowa 48 h (TASK-5.6, ADR-030): `forecast.hours[]` w dashboardzie, `forecasts.granularity` (migracja `0015`), jedno żądanie Open-Meteo, retencja „najnowszy przebieg”, parser odporny na `null`; estymata budżetu 2→3 jedn. (`max_active_areas` 411→280) — zależny od #87 |
| #90 | Mobile: UI asset pack v2 (`docs/ui/asset-pack-v1.md`, `asset-implementation-v2.md`): Welcome z zatwierdzonym tłem JPG + natywny znak/tekst/wskaźniki domen/CTA/scrim (jasny/ciemny, `lib/welcome.ts` z testem kontrastu AA na scrimie), `app.json` (ikona, adaptive, monochrome), ilustracje stanów PNG (lazy `require`, `lib/stateArt.ts`: `no-alerts` tylko przy potwierdzonym zerze, `offline` tylko przy odrzuconym `fetch`, UNKNOWN → `no-data`); rastry zainstalowane (instalator dopasowany do paczki, hashe/wymiary OK); bez weryfikacji na urządzeniu — 🟡 |
| #91 | Docs: instrukcja uruchomienia i testu aplikacji mobilnej na telefonie (`docs/mobile/run-and-test.md`) |
| #92 | Mobile: dokończenie Start (TASK-12.18): max/min z `forecast.days[0]` (`todayRange`, fail-safe), tap werdyktu → powody, skeleton kalendarza pylenia; bez mocków, bez zmian backendu — 🟡 (bez weryfikacji na urządzeniu) |
| #93 | Mobile: szczegóły Powietrze (S5) i Pogoda (S6) (TASK-12.12): stacja/odległość/metoda, składowe EAQI, brak indeksu z powodem, prognoza dobowa, status źródła i atrybucje; live, bez mocków, bez zmian backendu — 🟡 (bez weryfikacji na urządzeniu) |
| #94 | Mobile: ekran Alerty wg lokalizacji + szczegół alertu (TASK-9.7): `local_alerts`/`unresolved` (nigdy ukryte)/pozostałe, treść źródłowa dosłownie (reguła #10), „brak ostrzeżeń” tylko przy potwierdzeniu; bez zmian backendu — 🟡 (bez weryfikacji na urządzeniu) |
| #95 | Mobile: ekran Stany rzek (TASK-12.16): pełna lista stacji IMGW z progami, grupy, wyszukiwanie, paginacja; stary odczyt nie twierdzi „poniżej progów”; test pilnujący braku kąpielisk/wody pitnej w UI; bez zmian backendu — 🟡 (bez weryfikacji na urządzeniu) |
| #96 | Mobile: wybór motywu Systemowy/Jasny/Ciemny (TASK-12.19): zapis lokalny (`theme` w ustawieniach, kompatybilny wstecz), `Appearance.setColorScheme`, pasek stanu wg efektywnego schematu; przegląd a11y kodu (`docs/ui/a11y-review.md`); bez zmian backendu — 🟡 (TalkBack/czcionki/zmiana na żywo niezweryfikowane na urządzeniu) |
| #97 | **(zastąpione w #102: Topics usunięte)** Mobile: tematy „Co chcesz śledzić?” (TASK-12.13): `lib/topics.ts`, `TopicsPicker`, krok w onboardingu i w Ustawieniach, lokalny zapis (`Settings.topics`, kompatybilny wstecz); wyłączony temat = brak karty, baner realnego ostrzeżenia nigdy ukryty; bez zmian backendu — 🟡 (bez weryfikacji na urządzeniu) |
| #98 | Docs: ocena TASK-12.3 (GPS) — bez PRG nie ma sensu, decyzja właściciela (potem GPS zrobiony przez „najbliższą miejscowość”, #106) |
| #99 | Mobile: profil EAS `preview` (test APK z ikoną/splashem, `eas.json`) + `app.config.js` włączający HTTP (cleartext) tylko dla tego profilu; nowa zależność `expo-build-properties` (SDK 52, uzasadnienie: lokalny backend po HTTP w teście bez VPS); bez zmian w produkcji — 🟡 (build niezweryfikowany) |
| #100, #101 | Fix buildu APK (EAS): zadeklarowane `expo-font`/`expo-constants`/`expo-linking`; zależności wyrównane do Expo SDK 52 (react-native 0.76.9, Kotlin/Compose) — ✅ |
| #102 | Mobile: Production UI v1 — pełna przebudowa warstwy wizualnej wg `docs/ui/production-ui-v1.md` + `production-components-v1.md`: tokeny/prymitywy, Start (HeroVerdict, QuickStatusGrid, podgląd alertów), Pogoda/Powietrze/Pyłki/Alerty/Ustawienia, nawigacja Start/Alerty/Ustawienia, usunięte Topics; bez zmian backendu — 🟡 (lint/typecheck/379 testów/bundle Android OK; screenshoty z urządzenia i APK po stronie właściciela) |
| #103 | Alerty ↔ seedowe miasta: migracja `0016` nadaje 7 miastom z seeda kody TERYT gmin (potwierdzone w rejestrze GUS), bo bez nich KAŻDY alert był `unresolved` (Wrocław nie widział ostrzeżeń dla dolnośląskiego jako lokalnych); test danych; addendum ADR-013; bez zmiany reguły dopasowania — 🟡 (migracja SQL weryfikowana w CI/Postgres) |
| #104 | API: najbliższa stacja GIOŚ **z danymi** (ADR-025 addendum): `geo.pick_air_station`, `/dashboard` i `/air/latest?geo_area_id=` używają stacji z pomiarami w 100 km (dystans i pasmo pokrycia dotyczą stacji faktycznie użytej), polling 3 najbliższych stacji na obszar; naprawia „Brak stacji” (Wrocław) — ✅ (CI) |
| #105 | API: alerty dla miejscowości z rejestru `places` (ADR-013 addendum): `places.alert_match_codes` — kod gminy, a bez niego województwo z `admin1_name`; wcześniej każdy alert był dla nich „do sprawdzenia” — ✅ (CI) |
| #106 | GPS: „Użyj mojej lokalizacji” (`POST /api/v1/places/nearest`, 30 km, bez zapisu współrzędnych; `expo-location`, tylko coarse, FINE/background/foreground-service zablokowane) — 🟡 (bez weryfikacji na urządzeniu) |
| #107, #108 | `infrastructure/scripts/smoke_data.py` — test, czy backend dociągnął dane dla miasta (działa na Pythonie 3.9) — ✅ |
| #109 | Docs: pisemne potwierdzenie Open-Meteo (ADR-031), source registry `open_meteo*` APPROVED dla obecnej architektury, `docs/release/business-gates.md`, `docs/business/provider-licensing.md` — ✅ (daty korespondencji do uzupełnienia przez właściciela) |
| #110 | Mobile: nawigacja pierwszego uruchomienia — Wstecz z Lokalizacji do Welcome, reset historii po wyborze, zmiana lokalizacji wraca do źródła (`lib/navigation.ts`) — 🟡 (Back na urządzeniu niezweryfikowany) |
| #111–#117 | Mobile: Welcome — seria iteracji wizualnych do finalnej wersji (kapsuła 4 domen, panorama w kadrze, welony i lokalny scrim, Nunito, kolory domen z czerwonymi Alertami, logo oryginalne, układ wg mockupu); tylko `app/welcome.tsx`, `lib/welcome.ts` — 🟡 (wygląd na urządzeniu niezweryfikowany) |
| #118 | Docs: synchronizacja ROADMAP z PR #103–#117 |
| #119 | Docs: PRG (granice gmin) zatwierdzone przez właściciela + procedura importu (`docs/data/prg-import.md`) |
| #120 | Docs: szkic polityki prywatności (`docs/privacy/`) — 🟡 pola do uzupełnienia przez administratora |
| #121 | Infra: zestaw wdrożeniowy na VPS (`docker-compose.prod.yml`, Caddy, `.env.prod.example`, runbook) — niewdrożony, niezweryfikowany na serwerze |
| #122 | Docs: odświeżony przegląd dostępności (`a11y-review.md`) i `screen-map.md` po production UI v1 |
| #123 | Mobile: Powietrze — informacja o parametrze, którego stacja nie przekazuje (np. PM10) |
| #124 | Docs/scripts: poprawna komenda ręcznego pobrania GIOŚ (`run_gios`, jak scheduler) |
| #125 | Docs: naprawa tabeli „Historia PR” i audyt statusów w ROADMAP |
| #126 | Mobile: adaptive icon — znak ×1,10 i wyśrodkowany (`*-fit-1024.png`, oryginały bez zmian); niezweryfikowane na urządzeniu |
| #127 | Docs: wiersze #125 i #126 w historii PR |
| #128 | Mobile: fonty (Ionicons + Nunito) ładowane z góry w głównym layoucie; błąd ładowania widoczny w APK `preview` |
| #129 | Mobile: brakujący `expo-file-system` (moduł natywny `AppDirectories`) — przyczyna braku ikon i Nunito na urządzeniu; ✅ **potwierdzone na urządzeniu** (zrzuty z 2026-10-03: ikony, wyszukiwanie miejscowości, Start z danymi) |
| #130 | Szybkie pierwsze dane nowej miejscowości: bootstrap powietrza (najbliższe stacje GIOŚ, 1 próba na stację, 3 stacje na tick), tick schedulera 15 s, auto-odświeżanie Startu; atrybucja GIOŚ wg regulaminu (`Źródło danych: GIOŚ - EKOINFONET`), limit ≤ 2 pobrania/h — 🟡 niezweryfikowane na prawdziwym GIOŚ i urządzeniu |
| #131 | Docs: wiersz #130 w historii PR, #129 potwierdzone na urządzeniu |
| #132 | Mobile: karta „Typowy sezon” (jeden status sezonu + kontekst względem prognozy) i ekran szczegółów „Kalendarz sezonów”; kalendarz pobierany ponownie przy zmianie dnia — 🟡 niezweryfikowane na urządzeniu |
| #134 | Docs: pakiet `docs/data/gios/` (specyfikacje, próbki, weryfikacja, plan prac) |
| #135 | ADR-032 „Twoja okolica”, 7 wpisów `gios_*` w Source Registry, macierz bramek operacji (`07-operation-gates.md`) |
| #136 | Fundament ingestu nowych API GIOŚ (`app/gios_open/`, migracja 0017) i `probe` dla operatora; bez connectora |
| #137 | Backend hałasu historycznego: connector `gios_noise` (parser, import ręczny, kwarantanna), `noise_measurements` (migracja 0018), `GET /api/v1/neighborhood`, flagi `NEIGHBORHOOD_NOISE_*` (domyślnie off) — 🟡 gate GIOŚ niezaliczony (B-6), jeszcze bez importu na prawdziwym GIOŚ |
| #138 | Mobile: wiersz „Twoja okolica” na Start (tylko gdy API zgłasza `enabled`) i ekran z sekcją hałasu (stany available / no_coverage / unavailable / degraded, atrybucja CC BY 4.0) — 🟡 niezweryfikowane na urządzeniu |
| #146 | Backend: `/air/history`, okno 24/48 h i wykluczenie przyszłych odczytów — scalony 2026-10-03; CI backend/mobile zielone |
| #147 | Mobile: historia powietrza z lukami i wyborem 7 parametrów — scalony 2026-10-03; QA urządzenia po nowym UI |
| #148 | Bieżąca stacja, paginacja sensorów, niezależny indeks GIOŚ, poprawki po osobnym review i brief Design Leada — scalony 2026-10-03; CI backend/mobile zielone; indeks off, migracja/rollout oczekują |

Pierwszy etap IMGW: `docs/data/imgw/README.md` (ADR-034) — nowe obserwacje i resolver w addytywnym kontrakcie, ostrzeżenia pod flagami; nowy UI/insights, NWP/radar, migration/rollout i QA pozostają otwarte.

---

## Jak utrzymywać ten plik

**Zasada dla Claude (i każdego, kto pracuje nad tym repo): ten plik
aktualizuje się po każdym zmergowanym PR**, w tym samym PR-ze co zmiana albo
osobnym małym commitem zaraz po merge'u. Aktualizacja obejmuje: sekcję 1
(status jednym zdaniem, jeśli się zmienił), właściwą tabelę w sekcji 2-4 (nowy
✅/🟡/⛔ tam gdzie coś się zmieniło), sekcję 6 (nowe/rozwiązane blokady) i
sekcję 7 (nowy wiersz z numerem PR). Nie przepisywać całego pliku za każdym
razem — punktowa edycja, tak jak przy kodzie.

### Aktualizacja zakresu — 2026-10-03: rzeki i hałas

Właściciel przywrócił oba tematy do realizacji. Branch `codex/rivers-noise-local` (na PR #150):
🟡 lokalne stacje IMGW hydro (domyślnie 50 km, distance/time/thresholds, Start entry) i jednoznaczne
wejście do istniejących pomiarów GIOŚ noise („Hałas w okolicy”). Implementacja oddzielona od aktywacji:
flagi nadal false; hydro: timezone/terms/warningshydro gate, noise: operator/import/remaining gates.
Szczegóły i AC: `docs/tasks/TASK-local-rivers-noise.md`; design: `docs/ui/gios-imgw-design-brief.md`.
Brak deploy, build urządzenia i nowych map. Hałas historyczny jest jawnym wyjątkiem od current-only;
nie jest prezentowany jako bieżący monitoring akustyczny.
