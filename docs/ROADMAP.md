# Za Oknem — Roadmap

**Ten plik odzwierciedla stan faktyczny kodu, nie plany.** Aktualizowany po
każdym zmergowanym PR (patrz przypis na końcu). Źródło wizji produktowej:
[`Development-Master-Plan-v1.2.md`](architecture/Development-Master-Plan-v1.2.md)
(§4–§11). Status źródeł danych ze szczegółami (licencja, rate limit,
attribution): [`source-registry.md`](data/source-registry.md).

**Ostatnia aktualizacja:** 2026-10-01 (po PR #65; PR #63 w toku)

Legenda: ✅ DONE · 🟡 PARTIAL (częściowo, mniej niż pełny zakres MVP) ·
⛔ BLOCKED (zatrzymane na konkretnym warunku) · ⬜ TODO (nie zaczęte)

---

## 1. Gdzie jesteśmy (jednym zdaniem)

Pierwszy cel z CLAUDE.md — **Vertical Slice: GIOŚ → Connector → PostgreSQL →
FastAPI → React Native → PM2.5 na ekranie** — jest zrobiony i rozszerzony o
kolejne źródła (pogoda, poziom wody, ostrzeżenia hydrologiczne). Nie jesteśmy
jeszcze przy pełnym zakresie danych z §4 Master Planu (pyłki, woda/kąpieliska
w ogóle nie zaczęte) ani przy pełnym MVP mobile (tylko jeden ekran, bez
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
| olcha, brzoza, trawy, bylica, ambrozja | ⬜ TODO — brak connectora, brak Source Approval Gate |

### 2.4. Woda / kąpieliska (§7)

| Metryka | Status |
|---|---|
| status kąpieliska (dopuszczone/niedopuszczone), przyczyna zamknięcia, sezon kąpielowy, lokalizacja kąpieliska | ⬜ TODO — brak connectora, brak Source Approval Gate |
| E. coli, enterokoki, sinice | ⬜ TODO — brak connectora, brak Source Approval Gate |
| data ostatniego / następnego badania próbki | ⬜ TODO — brak connectora, brak Source Approval Gate |

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
| zamknięcia kąpielisk | ⬜ TODO — zależne od connectora wody (2.4) |
| istotne lokalne zagrożenia / zweryfikowane zdarzenia | ⬜ TODO — model `Event` (§31) nie istnieje |
| geo-matching alertu → lokalizacja użytkownika | ⬜ TODO — świadomy non-goal ADR-009; `/alerts/latest` zwraca WSZYSTKIE aktywne ostrzeżenia w Polsce, bez filtrowania |
| Alert Engine (§47) / Notification Engine (§50) | ⬜ TODO — poza scope'em dotychczasowych tasków, świadomie odłożone |

---

## 3. Backend — checklist z §10 (MVP zawiera)

| Element | Status |
|---|---|
| FastAPI | ✅ DONE |
| PostgreSQL | ✅ DONE |
| PostGIS | ⬜ TODO — nie używane; geo-matching robi zwykły haversine w Pythonie (`app/geo.py`, ADR-006), celowo wąski zakres (7 zaseedowanych lokalizacji vs stacje GIOŚ), nie ogólny silnik geo |
| Redis (cache/stan krótkotrwały) | ⬜ TODO — nie wdrożone; obecnie wszystko czyta z PostgreSQL bezpośrednio |
| Connector framework (fetch/parse/validate/normalize) | ✅ DONE — wzorzec ustalony i powtórzony w 5 connectorach (`gios`, `open_meteo`, `imgw_hydro`, `imgw_warningshydro`, `imgw_warningsmeteo` częściowo) |
| Scheduler | ✅ DONE — ADR-007, loop-based, per-job interval gating, izolacja awarii (rule #1, `_run_job_safely`) |
| Workers (oddzielny proces/kolejka) | ⬜ TODO — świadomie NIE zrobione (ADR-007): scheduler w jednym procesie wystarcza przy obecnej skali, przejście na worker/queue dopiero gdy realnie potrzebne |
| Normalization / validation | 🟡 PARTIAL — wzorzec (fetch/parse/validate/normalize) wdrożony w pełni w 4 connectorach (`gios`, `open_meteo`, `imgw_hydro`, `imgw_warningshydro`); `imgw_warningsmeteo` ma tylko `client.py` + dispatch pustego stanu, brak `normalize()`/`ingest.py` (patrz 2.6, blocker) |
| Freshness | 🟡 PARTIAL — per-wiersz freshness (FRESH/RECENT/STALE) dla `/air`, `/hydro`, `/alerts`, `/weather`; **source-level freshness z UNAVAILABLE (ADR-012, TASK-7.4)** dla ostrzeżeń (#59, #61) i hydrologii (#62): tabela `source_status` zapisywana przez scheduler i ręczne CLI, `source_status` w `/alerts/latest`, `/hydro/latest` i agregacie; mobile nie pokazuje „brak ostrzeżeń/alarmów”, gdy źródło milczy lub status zestarzał się na urządzeniu (>6h); dla `air`/`weather` w agregacie jeszcze nie (TASK-7.3) |
| Provenance / raw ingestion (§33-34) | ✅ DONE — `source_fetches` (surowy payload, endpoint, wersja parsera, status walidacji) + nullable FK `source_fetch_id` na `Measurement`/`Alert`/`WeatherSnapshot`/`Forecast`; wszystkie 4 connectory; retencja payloadu 7/14/30 dni, metadane zostają; zapis best-effort, awaria nie psuje ingestu (ADR-014, TASK-3.1, PR #65). Rekordy sprzed migracji 0009 mają FK NULL |
| Outdoor Interpretation Engine (§52) | 🟡 PARTIAL — `app/outdoor.py`: deterministyczny GOOD/MODERATE/POOR/UNKNOWN + `reasons[]`/`missing[]` (ADR-016, PR #64); progi PM/UV/wiatr ze źródłami, temperatura/opady/widoczność oznaczone „do kalibracji”. Niepodłączony do dashboardu ani mobile (TASK-7.7/7.8) |
| Geo matching | 🟡 PARTIAL — tylko nearest-station GIOŚ↔geo_area (ADR-006, próg 50km); brak dopasowania alertów do województw/lokalizacji |
| Alert Engine | ⬜ TODO |
| Notification Engine | ⬜ TODO |
| REST API | 🟡 PARTIAL — `/air`, `/weather`, `/hydro`, `/alerts`, `/dashboard/latest`, `/health`; wersjonowane pod `/api/v1/` |
| Logging | ✅ DONE — `logging` per connector/scheduler, ustandaryzowane |
| Monitoring | 🟡 PARTIAL — dzienny licznik wywołań per źródło + WARNING przy 70% limitu (TASK-13.1a, PR #55); brak zewnętrznego monitoringu/alertingu (TASK-13.2) |
| Provider config Free→Paid (TASK-13.4, ADR-022) | ✅ DONE — endpointy Open-Meteo i `OPEN_METEO_API_KEY` w env (domyślnie Free), klucz maskowany w wyjątkach/logach/provenance; przejście na plan komercyjny = tylko config. **Przed monetyzacją: checklista w ADR-003** (plan komercyjny Open-Meteo, env produkcyjne, licencje pozostałych źródeł). Host `customer-air-quality-api…` niezweryfikowany wprost |
| Backup | 🟡 PARTIAL — `backup.sh`/`restore_test.sh`/`test_backup_restore.sh` gotowe i przetestowane na Postgres 16 (dump+sekrety szyfrowane age bez plaintextu na dysku, spójna migawka dump+manifest, walidacja manifestu, limit wieku backupu, hasło poza argv); brak: realny off-VPS storage provider, zaplanowane uruchamianie na produkcji (TASK-15.2/15.3), wydzielony host weryfikacyjny |

---

## 4. Mobile — checklist z §10 (MVP zawiera)

| Element | Status |
|---|---|
| Home / Dashboard | 🟡 PARTIAL — jeden ekran (`apps/mobile/app/index.tsx`), lista lokalizacji z pełnym zestawem parametrów GIOŚ + pogodą + prognozą, sekcje „Ostrzeżenia — cała Polska” i „Stany wody — cała Polska” (stacje WARNING/ALARM, osobny fetch `/hydro/latest`; TASK-7.2, PR #58/#62), pull-to-refresh, freshness z backendu. Brak karty outdoor i pyłków. |
| Alerts (ekran) | ⬜ TODO |
| Settings | ⬜ TODO |
| foreground location | ⬜ TODO — obecnie statyczna lista 7 zaseedowanych miast, brak geolokalizacji urządzenia |
| ręczny wybór lokalizacji | ⬜ TODO |
| push notifications | ⬜ TODO |
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
| Geo-matching alertów do lokalizacji | Decyzja o metodzie (statyczna mapa 7 lokalizacji→województwo, czy pełny Geo Engine z TERYT, §27, Phase 6) | brak (non-goal ADR-009) |

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
| #63 | Europejski indeks jakości powietrza EAQI/EEA (ADR-015, TASK-4.2): `air_index.py`, `index` w `/air/latest` i dashboardzie, mobile `AirIndexBadge`; indeks GIOŚ odłożony |
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
