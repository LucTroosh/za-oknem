# Za Oknem — Roadmap

**Ten plik odzwierciedla stan faktyczny kodu, nie plany.** Aktualizowany po
każdym zmergowanym PR (patrz przypis na końcu). Źródło wizji produktowej:
[`Development-Master-Plan-v1.2.md`](architecture/Development-Master-Plan-v1.2.md)
(§4–§11). Status źródeł danych ze szczegółami (licencja, rate limit,
attribution): [`source-registry.md`](data/source-registry.md).

**Ostatnia aktualizacja:** 2026-10-01 (po PR #73; stan main = 225ec08)

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
| temperatura, wilgotność, wiatr (prędkość+kierunek+porywy), kod warunków, odczuwalna, ciśnienie, zachmurzenie, opady/deszcz/śnieg | ✅ DONE — Open-Meteo, `GET /api/v1/weather/latest` + dashboard (12/15 pól MVP, PR #41) |
| punkt rosy, widoczność, UV | ✅ DONE — Open-Meteo `hourly` (osobny fetch nie był potrzebny, jeden request z `current`+`hourly`+`daily`), dopasowanie do godziny `current` w parserze (TASK-5.4) |
| prognoza (forecast, nie tylko current) | ✅ DONE — model `Forecast` (§30, ADR-010), `GET /api/v1/weather/forecast`, dzienna prognoza (temp max/min, opady, kod pogody) (TASK-5.3, PR #46); widoczna dla użytkownika w `dashboard_latest()` + mobile, 3 dni max/min z atrybucją i freshness (TASK-5.5) |

### 2.3. Pylenie (§6)

| Metryka | Status |
|---|---|
| olcha, brzoza, trawy, bylica, ambrozja | 🟡 PARTIAL — **backend ✅** (TASK-8.5–8.7, PR #71, ADR-020): connector `open_meteo_pollen` (CAMS Europe przez Open-Meteo Air Quality — **prognoza modelowa, nie pomiar**, `kind=model_forecast`), `PollenSnapshot` (5 gatunków, NULL ≠ 0), scheduler 24 h z `source_status`, provenance, `GET /api/v1/pollen/latest`. **Brak** karty mobile (TASK-8.8) i bloku `pollen` w `dashboard_latest()` (TASK-8.9) — w toku w osobnym PR, nie DONE. Rzeczywiste pomiary (OBAŚ) niezweryfikowane |

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
| istotne lokalne zagrożenia / zweryfikowane zdarzenia | ⬜ TODO — model `Event` (§31) nie istnieje |
| geo-matching alertu → lokalizacja użytkownika | ⬜ TODO — świadomy non-goal ADR-009; `/alerts/latest` zwraca WSZYSTKIE aktywne ostrzeżenia w Polsce, bez filtrowania |
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
| Freshness | 🟡 PARTIAL — per-wiersz freshness (FRESH/RECENT/STALE) dla `/air`, `/hydro`, `/alerts`, `/weather`; **source-level freshness z UNAVAILABLE (ADR-012, TASK-7.4)** dla ostrzeżeń (#59, #61) i hydrologii (#62): tabela `source_status` zapisywana przez scheduler i ręczne CLI, `source_status` w `/alerts/latest`, `/hydro/latest` i agregacie; mobile nie pokazuje „brak ostrzeżeń/alarmów”, gdy źródło milczy lub status zestarzał się na urządzeniu (>6h); dla `air`/`weather` w agregacie jeszcze nie (TASK-7.3); pyłki mają `source_status` w `/pollen/latest` (PR #71). Widok operatorski: `GET /api/v1/health/sources` (TASK-13.1, PR #69) |
| Provenance / raw ingestion (§33-34) | ✅ DONE — `source_fetches` (surowy payload, endpoint, wersja parsera, status walidacji) + nullable FK `source_fetch_id` na `Measurement`/`Alert`/`WeatherSnapshot`/`Forecast`; wszystkie connectory istniejące w PR #65 (4; pyłki dołączyły w PR #71); retencja payloadu 7/14/30 dni, metadane zostają; zapis best-effort, awaria nie psuje ingestu (ADR-014, TASK-3.1, PR #65). Rekordy sprzed migracji 0009 mają FK NULL |
| Outdoor Interpretation Engine (§52) | 🟡 PARTIAL — `app/outdoor.py`: deterministyczny GOOD/MODERATE/POOR/UNKNOWN + `reasons[]`/`missing[]` (ADR-016, PR #64); progi PM/UV/wiatr ze źródłami, temperatura/opady/widoczność oznaczone „do kalibracji”. Podłączony: blok `outdoor` per obszar w `dashboard_latest()` i `OutdoorCard` na mobile (TASK-7.7/7.8, PR #68); preferencje „outdoor” użytkownika (TASK-12.4) nie istnieją |
| Geo matching | 🟡 PARTIAL — nearest-station GIOŚ↔geo_area (ADR-006, próg 50 km) oraz **point-in-polygon lat/lon → gmina** (`app/geo.py::resolve_gmina`, `POST /api/v1/geo/resolve`, TASK-6.2 punkty 1–6, PR #70, ADR-019). Resolver bez danych zwraca `None` (granice gmin niezaładowane). Nie zrobione: odkrywanie stacji GIOŚ per gmina (6.2/7), zawężenie dashboardu do lokalizacji (6.2/8), dopasowanie alertów (TASK-9.5) |
| Alert Engine | ⬜ TODO |
| Notification Engine | ⬜ TODO |
| REST API | 🟡 PARTIAL — `/air`, `/weather`, `/hydro`, `/alerts`, `/pollen`, `/dashboard/latest`, `/geo/resolve`, `/devices`, `/health`, `/health/sources`; wersjonowane pod `/api/v1/`. Brak `/water` (kąpieliska ⛔) i typowanego `response_model` dla `/dashboard/latest` (TASK-2.1) |
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
| Home / Dashboard | 🟡 PARTIAL — jeden ekran (`apps/mobile/app/index.tsx`), lista lokalizacji z pełnym zestawem parametrów GIOŚ + pogodą + prognozą, sekcje „Ostrzeżenia — cała Polska” i „Stany wody — cała Polska” (stacje WARNING/ALARM, osobny fetch `/hydro/latest`; TASK-7.2, PR #58/#62), pull-to-refresh, freshness z backendu, `OutdoorCard` (TASK-7.7/7.8, PR #68), `AirIndexBadge` (PR #63). Brak karty pyłków (TASK-8.8). |
| Alerts (ekran) | ⬜ TODO |
| Settings | ⬜ TODO |
| foreground location | ⬜ TODO — obecnie statyczna lista 7 zaseedowanych miast, brak geolokalizacji urządzenia |
| ręczny wybór lokalizacji | ⬜ TODO |
| push notifications | ⬜ TODO — (backend rejestracji urządzeń 🟡 w sekcji 3; klient mobilny i wysyłka nie istnieją) |
| profil użytkownika | ⬜ TODO |
| podstawowe preferencje | ⬜ TODO |
| source transparency | ✅ DONE — `dashboard_latest()` zwraca `source`+`attribution`+`observed_at` dla air i weather, mobile renderuje atrybucję pod każdą sekcją (TASK-7.1, PR #49) |
| freshness (UI) | ✅ DONE — etykieta freshness pokazywana per sekcja |
| loading / error / stale / no-data states | 🟡 PARTIAL — loading/error/ready obsłużone; stale i no-data nie mają jeszcze dedykowanych stanów UI (§59, §80) |

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
| Geo-matching alertów do lokalizacji | Fundament Geo Engine jest (PR #70); brakuje danych (granice gmin, niżej) i samego dopasowania alertów | TASK-9.5 |

### Blokady po stronie człowieka (kod nie przesunie tego dalej)

| Do zrobienia | Czego dotyczy | Task / źródło |
|---|---|---|
| Zatwierdzić licencję PRG (GUGiK) w Source Approval Gate i pobrać `00_jednostki_administracyjne.zip` → GeoJSON gmin → import (`python -m app.connectors.prg_gminy.ingest`) | Bez tego `POST /geo/resolve` zwraca `None`, a 6.2 zostaje 🟡 | TASK-6.2, `docs/tasks/TASK-6.2-geo-engine-foundation.md` |
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

---

## Jak utrzymywać ten plik

**Zasada dla Claude (i każdego, kto pracuje nad tym repo): ten plik
aktualizuje się po każdym zmergowanym PR**, w tym samym PR-ze co zmiana albo
osobnym małym commitem zaraz po merge'u. Aktualizacja obejmuje: sekcję 1
(status jednym zdaniem, jeśli się zmienił), właściwą tabelę w sekcji 2-4 (nowy
✅/🟡/⛔ tam gdzie coś się zmieniło), sekcję 6 (nowe/rozwiązane blokady) i
sekcję 7 (nowy wiersz z numerem PR). Nie przepisywać całego pliku za każdym
razem — punktowa edycja, tak jak przy kodzie.
