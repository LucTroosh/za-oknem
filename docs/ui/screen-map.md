# Za Oknem — mapa ekranów i kontrakt danych UI

**Do czego to służy.** Właściciel przygotowuje design wizualny osobno. Ten dokument NIE
projektuje wyglądu — opisuje **strukturę informacji**: jakie są ekrany, co na nich stoi, skąd
bierze się każdy element (endpoint + pole kontraktu), co jest już **LIVE**, a co wejdzie jako
**MOCKUP do podmiany na live**. Stan faktyczny = kod `apps/mobile` + `packages/api-contract/openapi.json`
+ `docs/ROADMAP.md` na `main` = f6d7ece (po PR #83). Niczego tu nie zgadujemy: pole, którego nie ma w
`openapi.json`, jest zapisane jako „wymagane pole kontraktu” z zadaniem backendu (sekcja 4).

Powiązane: Master Plan §10, §24–25, §55–61, §80; ADR-026 (lokalizacja), ADR-027 (StyleSheet +
tokeny), ADR-028 (mocki UI, Proposed, razem z tym dokumentem); `docs/tasks/BACKLOG.md` (Phase 12,
zadania `TASK-12.10`–`12.16` dodane razem z tym dokumentem).

## 0. Legenda i zasady

| Znak | Status | Znaczenie |
|---|---|---|
| ✅ | LIVE | realne dane z naszego backendu, widoczne w aplikacji dziś |
| 🟡 | LIVE-częściowo | backend ma dane/endpoint, ale UI ich nie pokazuje w całości albo zakres danych jest niepełny |
| 🧪 | MOCK | dane przykładowe (fixture) do czasu, aż backend/źródło dostarczy kontrakt; widoczne tylko w dev/preview (sekcja 3) |
| ⛔ | BLOCKED | zatrzymane na konkretnym warunku (źródło, klucze, decyzja); BEZ mocka danych |
| ⬜ | TODO | do zrobienia, bez mocka (dane są w kontrakcie albo ekran jest statyczny) |

Reguły MVP, które zawężają strukturę (CLAUDE.md, Master Plan §11, §24, §62): **bez mapy, bez konta,
bez background location (tylko jednorazowa lokalizacja na pierwszym planie), bez monetyzacji, bez
Green Index**. Preferencje są lokalne (device-based), nie kontem. Mobile czyta wyłącznie z naszego API
(reguła #14); wszystkie sekcje niosą `source`/`attribution`/freshness (reguły #6, #8).

**Stany do zaprojektowania** (Master Plan §59/§80), skrót używany w tabelach:
`L` loading · `E` empty (poprawnie brak danych) · `Er` error (backend/źródło nie odpowiada) ·
`S` stale (dane stare: znacznik czasu + oznaczenie) · `U` unavailable (źródło milczy/nigdy nie
zadziałało — NIE „brak zagrożeń”) · `P` brak uprawnień (lokalizacja odrzucona → wybór ręczny).
Dziś w kodzie jest wspólny zestaw: `LoadingState`, `EmptyState`, `Notice`, `FreshnessBadge`
(świeże/niedawne/nieaktualne/brak danych, glif + słowo + kolor). Nie ma jeszcze `Skeleton`
(wymieniony w Master Planie §58; dziś loading = spinner z etykietą).

---

## 1. Drzewo nawigacji

```text
Root Stack (app/_layout.tsx)
│
├── (tabs)                                         ← dolna nawigacja, 3 zakładki (Master Plan §57)
│   ├── Dziś            S1   ✅ jest (app/(tabs)/index.tsx)
│   │     [nagłówek] wybór lokalizacji ─────────────► S4 Wybór lokalizacji (modal)     ⬜ TASK-12.2/12.11
│   │     karta Powietrze  ─────────────────────────► S5 Szczegóły: Powietrze          ⬜ TASK-12.12
│   │     karta Pogoda / Prognoza ──────────────────► S6 Szczegóły: Pogoda             ⬜ TASK-12.12
│   │     karta Pyłki ──────────────────────────────► S7 Szczegóły: Pyłki              🧪 TASK-12.14
│   │     sekcja Woda ──────────────────────────────► S8 Woda i hydrologia             🟡/⛔ TASK-12.16
│   │     baner ostrzeżeń ──────────────────────────► zakładka Alerty (już jest)
│   │
│   ├── Alerty          S2   🟡 jest (app/(tabs)/alerts.tsx; cała Polska)
│   │     pozycja alertu ───────────────────────────► S3 Szczegół alertu               ⬜ TASK-9.7
│   │     stacja wodna ─────────────────────────────► S8 (sekcja Rzeki)
│   │
│   └── Ustawienia      S9   🟡 jest jako placeholder (app/(tabs)/settings.tsx)
│         ├── Lokalizacja ────────────────────────► S4
│         ├── Profil alergika i preferencje ──────► S10                                🧪 TASK-12.13
│         ├── Powiadomienia ──────────────────────► S11                                🧪 placeholder TASK-12.15
│         ├── Źródła i licencje ──────────────────► S12                                🟡 TASK-12.6
│         ├── Prywatność i dane ──────────────────► S13                                ⛔/⬜ TASK-12.6, 14.2
│         └── O aplikacji ────────────────────────► S14                                🟡 TASK-12.6
│
└── (pełnoekranowe/modalne, poza zakładkami)
      S4  Wybór lokalizacji           (+ S4a wyjaśnienie uprawnienia lokalizacji, §24)
      S3  Szczegół alertu             (cel deep linku z push, TASK-10.4)
      S5–S8  Szczegóły sekcji         (push na stos nad zakładką „Dziś”)
```

Uwagi do drzewa (decyzje otwarte są w sekcji 5):

- Nazwy tras to propozycja struktury plików Expo Router (np. `app/location.tsx`, `app/details/air.tsx`,
  `app/alerts/[id].tsx`, `app/settings/*.tsx`); `settings.tsx` stanie się katalogiem `settings/` z `index.tsx`.
- **Mapy nie ma nigdzie** (Master Plan §11, §57). Wybór lokalizacji to lista + wyszukiwarka + przycisk
  lokalizacji, nie mapa.
- **Dziś zakładka „Dziś” pokazuje wszystkie obszary pod rząd** (7 zaseedowanych miast, bez wyboru).
  Po S4 pokazuje JEDEN wybrany obszar (`/dashboard/latest?geo_area_id=`, ADR-026), a pozostałe
  obszary są dostępne tylko przez S4.
- Konto, logowanie, synchronizacja, „zapisane lokalizacje w chmurze”, premium, mapa, historia —
  poza MVP; nie rysujemy dla nich ekranów ani „wkrótce”.

---

## 2. Ekrany — element po elemencie

Kolumna **Źródło** to endpoint + pole kontraktu z `openapi.json`/`schema.ts`. **Task** = pozycja
w BACKLOG (istniejąca albo dodana tym PR).

### S1. Dziś (Home) — ✅ istnieje

Dziś: pełna lista obszarów jedna pod drugą; karty w kolejności „Na dwór → Powietrze → Pogoda/Prognoza →
Pyłki”; kalendarz pylenia na końcu; pull-to-refresh.

| Element UI | Źródło (endpoint · pole) | Status | Task | Stany do zaprojektowania |
|---|---|---|---|---|
| Nagłówek z nazwą obszaru + przełącznik lokalizacji | `GET /areas` · `name`, `geo_area_id`; wybór → `GET /dashboard/latest?geo_area_id=` | ⬜ (backend ✅ ADR-026; dziś nazwa obszaru to tytuł sekcji, brak przełącznika) | TASK-12.2, 12.11 | L, Er (lista obszarów), E |
| Baner „ostrzeżenia” (do 2 linii) | `GET /dashboard/latest` · `alerts.items[]`, `alerts.source_status`; `GET /hydro/latest` · `stations[].status`, `source_status` | ✅ cała Polska (lokalnie: `areas[].local_alerts`, `geo_match` — backend ✅, mobile nieużyte) | TASK-9.7 (lokalnie), 9.5 (hydro po lokalizacji) | brak/stare dane = neutralne „niedostępne”, nigdy cisza czytelna jako „spokój” (ADR-012, jest w `alertsBanner.ts`); U, S |
| Powiadomienie „nie udało się odświeżyć” | stan klienta (`state === "error"` przy istniejących danych) | ✅ | — | Er z jednoczesnym pokazaniem starych danych |
| Karta „Na dwór” | `areas[].outdoor` · `level` (GOOD/MODERATE/POOR/UNKNOWN), `reasons[]`, `missing[]`, `valid_until` | ✅ (progi temperatura/opady/widoczność „do kalibracji”, ADR-016; pyłków silnik NIE uwzględnia) | TASK-7.8 ✅; wpływ preferencji: 12.4 | UNKNOWN (brak rdzenia danych), stare (starzenie na zegarze urządzenia), brak bloku (starszy backend) |
| Karta „Powietrze” — parametry | `areas[].air` · `params{}` (wartość, jednostka, `observed_at`, `freshness`), `source_status`, `attribution` | ✅ | TASK-4.1/7.3 ✅ | L, E („brak stacji w pobliżu”), U, S (przygaszone), Er |
| …indeks jakości powietrza (EAQI) | `areas[].air.index` · `level`, `complete`, `dominant[]`, `missing{}`, `valid_until` | ✅ (EAQI/EEA, nie indeks GIOŚ — ADR-015) | TASK-4.2 ✅ | indeks znika, gdy źródło U/STALE (jest w kodzie) |
| …nazwa stacji, odległość, metoda przypisania | `areas[].air` · `station_name`, `distance_km`, `assignment_method` | 🟡 w kontrakcie, **nieużyte w UI** (source transparency: skąd pomiar) | TASK-12.12 | pokazać jako informację o źródle, nie jako „Twoje miasto” (stacja ≤ 50 km) |
| Karta „Pogoda” | `areas[].weather` · `params{}` (15 pól MVP, każde z jednostką i `freshness`), `source_status` | ✅ | TASK-5.4/7.3 ✅ | L, E, U, S |
| Karta „Prognoza” (3 dni: max/min, opad, kod) | `areas[].forecast` · `days[].params`, `freshness`, `fetched_at` | 🟡 (dobowa; brak `source_status` w bloku — follow-up 7.3; brak prognozy godzinowej) | follow-up TASK-7.3 | S (etykieta freshness bez przygaszenia), E |
| Karta „Pyłki — prognoza modelu CAMS” | `areas[].pollen` · `current{alder,birch,grass,mugwort,ragweed}`, `unit`, `valid_at`, `freshness`, `source_status`, `kind="model_forecast"` | ✅ (to **prognoza modelu, nie pomiar**; progi = sezon/szczyt EAACI, nie ryzyko objawów — ADR-020) | TASK-8.8/8.9 ✅ | S/U ⇒ BEZ poziomów (reguła #8), `null` = „brak danych”, nigdy 0 |
| Karta „Kalendarz pylenia — typowy sezon” | `GET /pollen/calendar` · `active[]`, `upcoming[]`, `not_covered[]`, `coverage_warning`, `disclaimer` | 🟡 (8 taksonów; ambrozja/pokrzywowate niezweryfikowane — `not_covered`) | TASK-8.10 ✅ | pusty `active` ≠ „nic nie pyli” (komunikat z API zawsze) |
| Sekcja „Woda” (kąpieliska) | brak endpointu `/water` | ⛔ BLOCKED — brak źródła BIEŻĄCEGO statusu (ADR-021, TASK-11.2) | TASK-11.x | „Wkrótce” bez danych (sekcja 3, TASK-12.16) albo ukryte — decyzja właściciela |
| Stan ekranu: ładowanie / błąd / brak obszarów | stan `DashboardProvider` | ✅ (`LoadingState`, `EmptyState` z przyciskiem) | — | L, Er, E; `devHint` tylko w dev |
| Obszar bez aktywnego pollingu pogody | `areas[].weather_polling_active=false` ⇒ `weather`/`forecast` null, `pollen` UNAVAILABLE, `air` wg stacji ≤ 50 km | 🟡 backend ✅ (ADR-026), UI nie odróżnia „nikt nie zbiera” od „źródło zepsute” | TASK-12.11 | osobny komunikat: „dla tej lokalizacji nie zbieramy jeszcze danych pogodowych” |

### S2. Alerty — 🟡 istnieje (cała Polska)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Ostrzeżenia hydrologiczne IMGW (lista) | `GET /dashboard/latest` · `alerts.items[]` (`event_type`, `severity_raw`, `areas[]`, `valid_until`, `issuing_office`, `freshness`), `alerts.scope="national"`, `alerts.source_status` | ✅ ogólnokrajowe, treść źródłowa (reguła #10) | TASK-7.2 ✅ | „Brak aktywnych ostrzeżeń” TYLKO gdy źródło FRESH/RECENT; inaczej „lista może być nieaktualna” / „niedostępne”; L, Er |
| Filtr „dla mojej lokalizacji” | `areas[].local_alerts[]`, `AlertOut.geo_match` (`voivodeship` / `unresolved`); alternatywnie `GET /alerts/latest?geo_area_id=` | 🟡 backend ✅ (województwo, ADR-013), mobile nieużyte; obszary `unresolved` mają być **pokazane, nie ukryte** | TASK-9.7, 9.5 | etykieta zakresu („Twoje województwo” / „cała Polska” / „obszar nierozpoznany”) |
| Ostrzeżenia meteorologiczne | brak (`imgw_warningsmeteo` bez `normalize()`) | ⛔ BLOCKED — czeka na żywy przykład aktywnego ostrzeżenia (TASK-9.2) | TASK-9.2 | sekcji nie rysujemy jako „0 ostrzeżeń”; zob. sekcja 3 (zakaz mocka) |
| Zamknięcia kąpielisk | brak | ⛔ BLOCKED (zależy od źródła, ADR-021; TASK-11.3) | TASK-11.3 | j.w. |
| „Stany wody” (stacje WARNING/ALARM) | `GET /hydro/latest` · `stations[]` (`status` NORMAL/WARNING/ALARM/UNKNOWN, `water_level_cm`, `warning_level_cm`, `alarm_level_cm`, `observed_at`, `freshness`), `source_status` | ✅ cała Polska, limit 5 + „i N więcej” | TASK-7.2 ✅ | niezależne stany od ostrzeżeń (rule #1); stacje bez progów nie są oceniane (jest informacja) |
| …stacja najbliższa wybranej lokalizacji | brak parametru lokalizacji w `/hydro/latest` | ⬜ wymaga backendu (nearest-station, wzorzec ADR-006) | TASK-9.5 | — |
| Stan ekranu | j.w. | ✅ (L/Er/E, `Notice` przy odświeżeniu) | — | — |

### S3. Szczegół alertu — ⬜

Wszystkie pola potrzebne do szczegółu **już są** w `AlertOut` — to praca czysto UI (bez mocka, bez nowego
endpointu; wyszukiwanie po `external_id` dojdzie dopiero z deep linkiem, TASK-10.4).

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Tytuł: typ + stopień | `event_type`, `severity_raw` (surowe, bez tłumaczenia stopni własnym tekstem) | ⬜ (dane ✅) | TASK-9.7 | — |
| Treść źródłowa, komentarz | `description`, `comment` — **dosłownie**, bez streszczenia LLM (reguła #10) | ⬜ (dane ✅) | TASK-9.7 | pole `null` = nie rysujemy wiersza |
| Obszary | `areas[]` + `geo_match` | ⬜ (dane ✅) | TASK-9.7 | `unresolved` = jawna informacja |
| Ważność, wydano, pobrano | `valid_from`, `valid_until`, `published_at`, `fetched_at`, `freshness` | ⬜ (dane ✅) | TASK-9.7 | S (alert wygasły/nieaktualny) |
| Prawdopodobieństwo | `probability_pct` (nullable) | ⬜ (dane ✅) | TASK-9.7 | `null` = pomijamy |
| Biuro wydające, źródło, atrybucja | `issuing_office`, `source`, `GET /dashboard/latest · alerts.attribution` | ⬜ (dane ✅) | TASK-9.7 | — |

### S4. Wybór lokalizacji (+ S4a uprawnienie lokalizacji) — ⬜ UI / 🟡 backend

Backend gotowy (ADR-026, PR #82): `GET /areas`, `POST /geo/locate`, `GET /dashboard/latest?geo_area_id=`.
Dziś `GET /areas` (domyślnie tylko obszary z aktywnym pollingiem) zwraca **7 zaseedowanych miast**;
granice gmin PRG nie są załadowane (blokada po stronie człowieka), więc rozpoznanie „gminy” nie działa.

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Lista dostępnych obszarów (dziś 7 miast) | `GET /areas` · `geo_area_id`, `slug`, `name`, `weather_polling_active` | ⬜ UI (backend ✅) → **live od razu** | TASK-12.2/12.11 | L, E, Er (lista miast nie ładuje się ⇒ powtórz; nie blokuje reszty aplikacji) |
| Wyszukiwarka gmin (~2,5 tys.) | brak: `GET /areas` nie ma `q`/paginacji (ADR-026: „to zakres TASK-12.2”); brak załadowanych granic PRG | 🧪 MOCK (fixture typu `AreaOut`) + ⛔ dane (PRG, licencja po stronie człowieka) | TASK-12.11 (mock), TASK-12.2 (endpoint), TASK-6.2 (PRG) | E („brak wyników”), L, Er; wynik z fixture zawsze z `weather_polling_active=false` |
| Przycisk „Użyj mojej lokalizacji” + wyjaśnienie (S4a) | `expo-location` (nowa zależność, uzasadnić w PR) → `POST /geo/locate` · `status`, `area`, `assignment_method`, `distance_km` | 🧪 MOCK (stub zwracający `GeoLocateResponse`; backend ✅) | TASK-12.11 (mock), TASK-12.3 (live) | P: nie pytano / zgoda / odmowa → wybór ręczny (§25) / odmowa trwała (odsyłacz do ustawień systemu); timeout GPS |
| Wynik lokalizacji | `GeoLocateResponse` | 🧪 j.w. | TASK-12.3 | trzy różne komunikaty: `point_in_polygon` („gmina X”), `nearest_area` („najbliższy obszar z danymi: X, N km” — NIE „Twoja gmina”), `out_of_range` („poza zasięgiem”; nigdy dalszy obszar) |
| Obszar bez pollingu po wyborze | `AreaOut.weather_polling_active=false` | 🟡 backend ✅ | TASK-12.2 (aktywacja), 12.11 (stan) | komunikat „dane pogodowe nie są jeszcze zbierane dla tej lokalizacji” |
| Zapamiętanie wyboru na urządzeniu | pamięć lokalna (`geo_area_id`; współrzędne NIE są zapisywane, ADR-002/026) | ⬜ (wymaga biblioteki do pamięci lokalnej — nowa zależność, uzasadnić w PR) | TASK-12.2 | pierwszy start bez wyboru = S4 jako ekran startowy albo domyślny obszar (decyzja właściciela) |
| Heartbeat instalacji (aktywność obszaru) | brak endpointu | ⬜ TODO backend + klient | TASK-12.2 (a)–(c) | bez UI poza wzmianką w S13 (dane pseudonimowe) |

Nie ma: mapy, zapisanych lokalizacji w chmurze, śledzenia w tle (reguła #11).

### S5. Szczegóły: Powietrze — ⬜ (dane ✅, bez mocka)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Pełna lista parametrów z wiekiem pomiaru | `areas[].air.params{}` (wartość, jednostka, `observed_at`, `freshness`) | ⬜ (dane ✅) | TASK-12.12 | S per parametr, brak parametru = „brak”, nie 0 |
| Indeks EAQI: składowe i decydujący parametr | `air.index` · `level`, `params`, `dominant[]`, `missing{}`, `complete`, `valid_until` | ⬜ (dane ✅) | TASK-12.12 | `complete=false` ⇒ jawnie „niepełny”; U/S ⇒ bez indeksu |
| Stacja: nazwa, odległość, metoda | `station_name`, `distance_km`, `assignment_method` | ⬜ (dane ✅) | TASK-12.12 | — |
| Źródło, atrybucja, status źródła | `source`, `attribution`, `source_status{freshness,last_success_at}` | ⬜ (dane ✅) | TASK-12.12 | Er/U źródła |
| Trend / historia 24 h | brak w kontrakcie | poza MVP (Master Plan §11: pełna historia) | — | nie rysujemy |

### S6. Szczegóły: Pogoda i prognoza — ⬜ (dane ✅ dobowe)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Wszystkie pola pogody z jednostkami | `weather.params{}` | ⬜ (dane ✅) | TASK-12.12 | S per pole |
| Prognoza dobowa (dni) | `forecast.days[].params`, `valid_from/until`, `freshness`, `fetched_at` | ⬜ (dane ✅) | TASK-12.12 | S, E |
| Prognoza godzinowa / wykres | brak — Open-Meteo `hourly` jest pobierane, ale zapisywana jest tylko godzina zgodna z `current` | ⬜ wymaga backendu (nowa tabela/migracja); NIE mockujemy, dopóki właściciel nie zdecyduje, że chce | brak taska — decyzja, sekcja 5 | — |
| Źródło, atrybucja | `weather.attribution`, `forecast.attribution` | ⬜ (dane ✅) | TASK-12.12 | — |

### S7. Szczegóły: Pyłki — 🧪 (część live)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Wartości „teraz” (5 gatunków) i poziomy sezon/szczyt | `pollen.current`, `unit`, `valid_at` | ✅ (jak na S1) | — | S/U ⇒ bez poziomów |
| Maksima dobowe na kolejne dni | `pollen.days[]` · `date`, `max{5 gatunków}` | ⬜ (dane ✅, nieużyte w UI) | TASK-12.14 | `null` = „brak danych” |
| **Wykres godzinowy** | brak: baza ma 96 wierszy/obszar/dobę (ADR-020), ale API wystawia tylko `current` + `days` | 🧪 MOCK (typ proponowany `PollenHourly`) → live po TASK-8.11 | TASK-12.14 (mock), TASK-8.11 (backend) | zawsze jako **model_forecast** (tytuł „prognoza modelu CAMS, nie pomiar”), wersja tekstowa/tabela dla a11y, S/U ⇒ bez wykresu |
| Filtr gatunków wg profilu alergika | profil lokalny (S10) | 🧪 (zależy od S10) | TASK-12.13/12.14 | profil pusty = wszystkie 5 |
| Kalendarz pylenia | `GET /pollen/calendar` | ✅ (jak na S1) | — | — |
| Atrybucja CAMS + Open-Meteo, `forecast_reference_time` | `pollen.attribution`, `forecast_reference_time`, `model` | ✅ | — | — |

### S8. Woda i hydrologia — 🟡 rzeki / ⛔ kąpieliska

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Rzeki: stacje w stanie ostrzegawczym/alarmowym | `GET /hydro/latest` · `stations[]` | ✅ cała Polska | TASK-7.2 ✅ | jak S2 |
| Rzeki: pełna lista stacji z poziomem i progami | to samo (`water_level_cm`, `warning_level_cm`, `alarm_level_cm`) — kontrakt zwraca WSZYSTKIE stacje, UI pokazuje tylko WARNING/ALARM | 🟡 dane ✅, brak ekranu | TASK-12.16 (struktura), TASK-9.5 (po lokalizacji) | stacje bez progów = „nie oceniamy” |
| Kąpieliska: status, E. coli/enterokoki, sinice, sezon, daty badań, powód zamknięcia | brak `/water` | ⛔ BLOCKED — brak źródła statusu bieżącego (ADR-021: GIS to HTML bez API i licencji; EEA daje tylko rejestr + klasyfikację roczną) | TASK-11.1–11.6 | **tylko „wkrótce” bez danych** (sekcja 3) |
| Woda pitna | brak źródła (`sanepid_water`: NIEZWERYFIKOWANE/BLOCKED) i **poza zakresem MVP** (Master Plan §7 wymienia wyłącznie kąpieliska) | ⛔ | — | rekomendacja: NIE pokazywać nawet „wkrótce” (sekcja 5) |

### S9. Ustawienia (hub) — 🟡 placeholder

Dziś: trzy karty (O aplikacji + wersja, Źródła danych z `attribution`, Prywatność — zdanie).
Docelowo (Master Plan §60): lokalizacja, profil, alergie, outdoor, powiadomienia, dane i prywatność, źródła, o aplikacji.

| Wiersz | Prowadzi do | Status | Task |
|---|---|---|---|
| Lokalizacja (bieżący obszar) | S4 | ⬜ | TASK-12.2 |
| Profil alergika i preferencje | S10 | 🧪 | TASK-12.13 |
| Powiadomienia | S11 | 🧪 placeholder / ⛔ push | TASK-12.15, 10.x |
| Źródła i licencje | S12 | 🟡 | TASK-12.6 |
| Prywatność i dane | S13 | ⛔ treść prawna / ⬜ | TASK-12.6, 14.2 |
| O aplikacji | S14 | 🟡 | TASK-12.6 |

### S10. Profil alergika i preferencje — 🧪 (zachowanie lokalne)

Profil jest **tylko lokalny** (Master Plan §62, reguła #11), wpływa wyłącznie na kolejność i istotność,
**nigdy na fakty źródłowe** (§61). Backend nie jest potrzebny, więc mock dotyczy tylko braku persystencji.

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Wybór gatunków pyłków (olcha, brzoza, trawy, bylica, ambrozja) | lokalne (`PollenSpecies` z `lib/pollen.ts`) | 🧪 (w mocku: stan w pamięci, bez zapisu) → live z zapisem w TASK-12.4 | TASK-12.13, 12.4 | pusty wybór = wszystkie |
| Przełącznik „pokazuj kartę Na dwór” | lokalne | 🧪 → live TASK-12.4 | TASK-12.13, 12.4 | — |
| „Rodzina” (§ Phase 12 Master Planu) | nieokreślone w repo poza nazwą | ⬜ decyzja właściciela (sekcja 5) | TASK-12.4 | — |
| Skutek preferencji na Home (kolejność/filtr kart) | lokalne | ⬜ | TASK-12.4 („zastosuj profil”) | filtr nie ukrywa alertów ani danych bezpieczeństwa |

### S11. Powiadomienia — placeholder (⛔ push)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Zgoda systemowa na powiadomienia | `expo-notifications` (nowa zależność) | ⛔ klucze FCM/APNs po stronie człowieka (TASK-10.1 🟡) | TASK-10.5 | P: nie pytano / zgoda / odmowa |
| Kategorie powiadomień (ostrzeżenia hydro, meteo, kąpieliska, pyłki?) | brak modelu preferencji | ⛔/⬜ (TASK-10.3a backend, 10.3 UI); kategorie meteo i kąpieliska zależą od ⛔ źródeł | TASK-10.3a, 10.3 | przełączniki **nieaktywne** z powodem, żadnych działających-na-oko |
| Rejestracja urządzenia | `POST /devices` · `installation_id`, `platform`, `push_token`, `observed_area_code`, `X-Device-Secret` | 🟡 backend ✅ (bez wysyłki), klient ⬜ | TASK-10.5, 12.5 | Er rejestracji nie blokuje aplikacji |

### S12. Źródła i licencje — 🟡

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Lista atrybucji dosłownie z backendu | `attribution` z bloków `alerts`, `air`, `weather`, `forecast`, `pollen`, `hydro`, `pollen/calendar` (`collectAttributions`) | ✅ (lista pojawia się po załadowaniu danych) | TASK-12.1 ✅ | E: „odśwież Home”; kolejność wg pierwszego wystąpienia |
| Typ danych przy źródle (pomiar / prognoza modelu / kalendarz sezonowy) | `pollen.kind`, `pollen_calendar.kind`; reszta wiadoma z domeny | ⬜ | TASK-12.6 | — |
| Licencje źródeł | `docs/data/source-registry.md` (nie ma w API) | ⬜ | TASK-12.6 | statyczna treść zatwierdzona w Source Registry; bez „TBD” przed release |
| Status źródeł dla użytkownika | `GET /health/sources` jest operatorski | poza zakresem (nie pokazujemy `last_error`) | — | — |

### S13. Prywatność i dane — ⛔ treść / ⬜ struktura

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Polityka prywatności | dokument nie istnieje w `docs/` | ⛔ do czasu TASK-14.2 (treść prawna) | TASK-14.2 | **bez zmyślonego tekstu prawnego** — placeholder z informacją „dokument w przygotowaniu” tylko w dev/preview |
| Co zbieramy (lokalizacja jednorazowa, `installation_id`, `observed_area_code`, token push) | opis zgodny z ADR-002/017 | ⬜ | TASK-12.6, 14.2 | tekst „nie korzysta z lokalizacji urządzenia” w obecnym S9 **przestaje być prawdziwy** z TASK-12.3 — zmienić razem |
| Reset identyfikatora instalacji | `DELETE /devices/{installation_id}` (+ `X-Device-Secret`); heartbeat TASK-12.2 | ⬜ | TASK-12.2, 12.6 | potwierdzenie przed wygenerowaniem nowego |

### S14. O aplikacji — 🟡

| Element UI | Źródło | Status | Task |
|---|---|---|---|
| Nazwa, opis, wersja | `app.json` (`name`, `version`) | ✅ | TASK-12.1 ✅ |
| Kontakt, strona, licencje bibliotek, uwagi prawne | brak decyzji o treści | ⬜ | TASK-12.6 |

---

## 3. Polityka mocków

**Zasada nadrzędna: mockup nie może być pomylony z danymi live.** Najważniejsza część dotyczy danych
bezpieczeństwa (reguła #10: alerty, zamknięcia kąpielisk, jakość wody) — tam mocków **nie ma w ogóle**.
Uzasadnienie architektoniczne: ADR-028.

### 3.1. Zakaz mocków danych bezpieczeństwa (twardy)

W buildzie produkcyjnym i preview, a docelowo także w dev, NIE istnieją fixture'y, które wyglądają jak:

- ostrzeżenia (hydro, meteo) i ich stopnie,
- stan alarmowy/ostrzegawczy stacji wodnych (`status` WARNING/ALARM),
- status kąpieliska, E. coli, enterokoki, sinice, zamknięcia, daty badań,
- jakość wody pitnej,
- werdykt „Na dwór” oraz indeks jakości powietrza (liczone przez backend z realnych danych; ich mock
  mógłby wyglądać jak zalecenie zdrowotne).

Zamiast mocka: **ekran „wkrótce” bez danych** (komponent `ComingSoon`: tytuł + jedno zdanie, zero liczb,
zero statusów, zero ikon sugerujących stan), albo sekcja ukryta. Sekcje ⛔ w sekcji 2 tak wyglądają.
Pozostałe mocki dotyczą wyłącznie kształtów danych niezwiązanych z bezpieczeństwem (lista gmin,
wynik lokalizacji, prognoza pyłków modelowa, preferencje).

### 3.2. Mechanizm w kodzie (do wdrożenia w TASK-12.10)

| Element | Zasada |
|---|---|
| Flaga | `EXPO_PUBLIC_UI_MOCKS` (`"1"` włącza, `"0"` wyłącza) oraz `EXPO_PUBLIC_APP_ENV` (`development`/`preview`/`production`; brak = production — fail-safe). Funkcja `mocksEnabled()` w `lib/mock/flag.ts`: **dev** (`__DEV__`) domyślnie włączone, `=0` wyłącza (żeby sprawdzać live); **preview** wyłączone, chyba że profil ustawia `=1` (build do oglądania makiet przez właściciela); **production zawsze wyłączone** — flaga jest ignorowana. Wartości `EXPO_PUBLIC_*` są wypiekane w bundlu (README), więc zmiana wymaga przebudowy. |
| Fixture'y | tylko w `apps/mobile/lib/mock/`; każdy plik fixture typowany typami z kontraktu (`schema.ts`, np. `satisfies AreaOut[]`). Pola spoza kontraktu mają typy `Proposed*` w `lib/mock/proposed.ts`, każdy z komentarzem „wymagane pole kontraktu — TASK-…” (sekcja 4). Gdy backend dostarczy pole, typ `Proposed*` zastępuje wygenerowany z `schema.ts` i kompilator wskazuje fixture'y do poprawy. |
| Adapter | wspólny hook per źródło danych: `useX(): Sourced<T>` gdzie `Sourced<T> = { data: T \| null; state: LoadState; origin: "live" \| "mock" }`. Hook sam decyduje o źródle (`mocksEnabled()` ⇒ fixture, inaczej API); **komponent dostaje ten sam typ `T` i nie wie, skąd** — podmiana na live to zmiana źródła w hooku, nie komponentu. |
| Dane bezpieczeństwa | hooki `useAlerts`, `useHydro`, `useWater*` budowane fabryką **bez parametru `mock`** (typ nie pozwala go podać). Test `lib/mock/policy.test.ts` dodatkowo pilnuje, że w `lib/mock/**` nie ma nazw/eksportów z listy zakazanych (alert, hydro, water, bath, kąpiel, ostrzeż, ALARM, WARNING…). |
| Tożsamość | mock **nie dziedziczy tożsamości live**: fixture używa wymyślonych nazw („Gmina Przykładowa”), nigdy prawdziwej nazwy miasta/stacji z wymyślonymi wartościami; mock nie jest nakładany na live obiekt (np. wymyślony szereg godzinowy obok prawdziwej nazwy wybranej gminy). Jeżeli ekran potrzebuje pola, którego live obiekt jeszcze nie ma, pole idzie do **osobnej karty** z własnym `MockBadge`. |
| Czas | mock nie udaje „świeżych” danych: `observed_at` w fixture jest stałe i oznaczone jako przykładowe; `freshness` fixture'a jest zawsze jawnie „PRZYKŁADOWE”, nie FRESH. |
| Sieć | mock nie wykonuje żądań do backendu; `GET /areas` pozostaje live nawet przy włączonych mockach (lista 7 miast jest prawdziwa). Miesza się tylko tam, gdzie kontrakt tego wymaga (S4 — wyszukiwarka). |

### 3.3. Oznaczenie w UI

- **`MockBadge`** — etykieta „PRZYKŁADOWE DANE” na KAŻDEJ karcie/sekcji z `origin="mock"`.
- **`MockBanner`** — pas „PRZYKŁADOWE DANE — to nie są dane z Twojej okolicy” na górze KAŻDEGO ekranu, który
  zawiera choć jedną kartę mockowaną (także gdy ekran jest w większości live).
- Komunikat niesie **glif + słowo + obrys**, nie sam kolor; kontrast ≥ 4.5:1 w obu motywach — nowe tokeny
  semantyczne w `lib/theme.ts` (`mockFg`/`mockBg`) dopisane do `TEXT_PAIRS`, więc `theme.test.ts` je sprawdza
  (ADR-027). Wygląd (kolor, hatching, typografia) wybiera właściciel; wymagania wyżej są niezbywalne.
- `accessibilityLabel` karty mockowanej zaczyna się od „Przykładowe dane:”.
- `MockBadge`/`MockBanner` nie da się „wyłączyć” per komponent: pojawiają się automatycznie z `origin` w `Sourced<T>`.

### 3.4. Wyłączenie w release

1. W produkcji `mocksEnabled()` zwraca `false` niezależnie od flagi; dla `APP_ENV=production` ustawienie
   `EXPO_PUBLIC_UI_MOCKS` jest błędem builda (sprawdzenie w CI/`eas.json`, gdy powstanie — TASK-16.x; do tego czasu test jednostkowy).
2. Kryterium odbioru TASK-12.10: bundel produkcyjny (`expo export`) **nie zawiera** znacznika fixture'ów
   (stały ciąg `__UI_MOCK_FIXTURE__` w każdym pliku `lib/mock/*`) — sprawdzane w CI.
3. Release Candidate (Master Plan §103) dostaje punkt „brak `MockBadge` w buildzie”.

### 3.5. Lista zadań mockowych — kolejność i uzasadnienie

| # | Task | Co | Dlaczego w tej kolejności |
|---|---|---|---|
| 0 | TASK-12.10 UI-MOCK-0 | flaga, `lib/mock/`, `Sourced<T>`, `MockBadge`/`MockBanner`, testy polityki | bez tego każdy kolejny mock wymyślałby własny mechanizm; wymaga ADR-028 |
| 1 | TASK-12.11 UI-MOCK-1 | Wybór lokalizacji: **lista 7 miast live** + wyszukiwarka gmin i GPS jako mock | największa luka funkcjonalna; backend gotowy od #82, a od wyboru zależą S1, S2 (lokalne alerty), S7, push; większość ekranu jest live, mock obejmuje tylko to, czego brakuje (PRG, `q`, `expo-location`) |
| 2 | TASK-12.12 UI-LIVE-1 | Szczegóły Powietrze/Pogoda — **bez mocka**, od razu live | kontrakt ma wszystko (stacja, odległość, indeks, 15 pól); mock byłby stratą |
| 3 | TASK-12.13 UI-MOCK-2 | Profil alergika (stan w pamięci) | zero zależności od backendu; odblokowuje filtr gatunków w S7; trwały zapis i skutek to TASK-12.4 |
| 4 | TASK-12.14 UI-MOCK-3 | Szczegóły pyłków + wykres godzinowy, zawsze jako `model_forecast` | jedyny mock, który zakłada pole spoza kontraktu (`hourly`) — dlatego po 12.10 i z TASK-8.11 backendu |
| 5 | TASK-12.15 UI-MOCK-4 | Powiadomienia jako placeholder (przełączniki nieaktywne) | pokazuje strukturę, ale nic nie udaje działającego push (klucze FCM/APNs ⛔) |
| 6 | TASK-12.16 UI-MOCK-5 | „Wkrótce” dla kąpielisk + ekran rzek | bez danych; kąpieliska ⛔ — żadnych fałszywych statusów; rzeki są live |

---

## 4. Kontrakt danych dla przyszłych endpointów

Mock nie wyprzedza rzeczywistości: każde pole, które fixture zakłada, a którego nie ma w `openapi.json`,
jest tu zapisane z zadaniem backendu. Typ `Proposed*` w `lib/mock/proposed.ts` odpowiada wierszowi poniżej.

| Wymagane pole / endpoint | Potrzebne dla | Dziś w backendzie | Task backendu | Uwagi |
|---|---|---|---|---|
| `pollen.hourly[]` (`valid_at` + 5 gatunków, każdy `number\|null`, `unit`, `kind="model_forecast"`) | S7 wykres godzinowy | baza ma 96 wierszy/obszar/dobę (`pollen_snapshots`, ADR-020), API wystawia tylko `current` + `days` | **TASK-8.11** (dodany) | wystawić w `GET /pollen/latest`, nie w `/dashboard/latest` (rozmiar odpowiedzi); NULL ≠ 0; czyta tylko z bazy (reguła #14) |
| `GET /areas?q=&limit=&offset=` (wyszukiwanie/paginacja gmin) | S4 wyszukiwarka | `GET /areas` bez `q`, limit ≤ 5000, bez paginacji (ADR-026) | TASK-12.2 (zakres wskazany w ADR-026) | użyteczne dopiero po imporcie granic PRG (TASK-6.2, człowiek) |
| nearest-station hydro per lokalizacja (`/hydro/latest?geo_area_id=` albo blok w `areas[]`) | S2/S8 „najbliższa stacja” | `/hydro/latest` bez lokalizacji | TASK-9.5 | geo-matching deterministyczny po stronie serwera (reguła #9) |
| `GET /water/latest` (kąpieliska) | S8 | brak | TASK-11.4 (⛔ na źródle, ADR-021) | **bez mocka**; UI „wkrótce” |
| ostrzeżenia meteo w `alerts` | S2 | brak (`normalize()` zablokowane) | TASK-9.2 (⛔) | **bez mocka** |
| preferencje powiadomień (endpoint + model) | S11 | brak | TASK-10.3a | placeholder bez przełączników działających |
| heartbeat instalacji + reset | S4, S13 | brak | TASK-12.2 (a)–(c) | dane pseudonimowe → inwentarz TASK-14.2 |
| prognoza pogody godzinowa (`forecast.hourly[]`) | S6 wykres godzinowy | brak; zapisywana tylko godzina `current` | **brak taska** — zakładany dopiero po decyzji właściciela (sekcja 5) | nie mockujemy |
| `source_status` w bloku `forecast` | S1 prognoza | brak (follow-up 7.3) | follow-up TASK-7.3 | nie wymagane przez żaden mock |

Pola, które **są** w kontrakcie, a UI ich jeszcze nie używa (nie wymagają backendu ani mocka):
`air.station_name`, `air.distance_km`, `air.assignment_method`, `air.index.params`, `pollen.days[]`,
`pollen.forecast_reference_time`, `areas[].local_alerts`, `AlertOut.{description,comment,probability_pct,published_at,geo_match}`,
`AreaOut.weather_polling_active`, wszystkie stacje z `/hydro/latest` poza WARNING/ALARM.

---

## 5. Macierz „co live dziś” i decyzje właściciela

### 5.1. Macierz (jednym rzutem oka)

| Obszar | Backend / API | UI mobile dziś | Docelowo |
|---|---|---|---|
| Powietrze: parametry GIOŚ + EAQI | ✅ | ✅ (bez nazwy stacji/odległości) | ⬜ szczegóły S5 (live) |
| Pogoda: bieżąca (15 pól MVP) | ✅ | ✅ | ⬜ szczegóły S6 (live) |
| Prognoza dobowa (3 dni) | ✅ | 🟡 (bez `source_status`) | ⬜ S6 |
| Prognoza godzinowa pogody | ⬜ | ⬜ | decyzja właściciela |
| „Na dwór” (werdykt) | ✅ (progi do kalibracji) | ✅ | wpływ preferencji TASK-12.4 |
| Pyłki: prognoza modelu CAMS (`current`, `days`) | ✅ | ✅ (`current`) | ⬜ `days` w S7 |
| Pyłki: wykres godzinowy | 🟡 dane w bazie, brak w API | ⬜ | 🧪 TASK-12.14 → live po TASK-8.11 |
| Kalendarz pylenia | 🟡 (8 taksonów) | ✅ | — |
| Ostrzeżenia hydrologiczne (cała Polska) | ✅ | ✅ | — |
| Ostrzeżenia hydrologiczne lokalne (województwo) | ✅ | ⬜ nieużyte | TASK-9.7 |
| Ostrzeżenia meteorologiczne | ⛔ TASK-9.2 | ⛔ | po żywym przykładzie IMGW |
| Stany wody — rzeki (cała Polska) | ✅ | ✅ (WARNING/ALARM) | ⬜ pełna lista S8 |
| Stany wody po lokalizacji | ⬜ | ⬜ | TASK-9.5 |
| Kąpieliska: status, badania, zamknięcia | ⛔ ADR-021 | ⛔ „wkrótce” | po decyzji o źródle |
| Woda pitna | ⛔ brak źródła, poza MVP | — | nie pokazywać |
| Wybór lokalizacji (7 miast) | ✅ `GET /areas`, `?geo_area_id=` | ⬜ | 🧪/live TASK-12.11 |
| Wyszukiwanie gmin (~2,5 tys.) | ⛔ brak PRG i `q` | ⬜ | 🧪 TASK-12.11 |
| Lokalizacja GPS (jednorazowa) | ✅ `POST /geo/locate` | ⬜ | 🧪 TASK-12.11 → live TASK-12.3 |
| Profil alergika / preferencje | — (lokalne) | ⬜ | 🧪 TASK-12.13 → TASK-12.4 |
| Powiadomienia push | 🟡 rejestracja urządzeń; ⛔ klucze FCM/APNs | ⬜ | 🧪 placeholder TASK-12.15 |
| Źródła i licencje | ✅ `attribution` | 🟡 (lista bez typu danych) | ⬜ TASK-12.6 |
| Polityka prywatności | — | ⛔ brak dokumentu | TASK-14.2 |
| Szczegół alertu | ✅ (pełne `AlertOut`) | ⬜ | ⬜ TASK-9.7 |

### 5.2. Decyzje otwarte dla właściciela

1. **Nazwy zakładek.** Dziś: „Dziś” / „Alerty” / „Ustawienia”; Master Plan §57: Home / Alerts / Settings.
   Zostajemy przy polskich nazwach? (Tytuł nagłówka zakładki „Dziś” to „Za Oknem”.)
2. **Baner ostrzeżeń na Home.** Dziś: do 2 linii (alarm/ostrzeżenie hydro + ostrzeżenia IMGW, cała Polska) z
   odnośnikiem do Alertów. Po lokalizacji: czy baner liczy tylko alerty dla wybranego województwa, czy też
   „cała Polska”? Czy ma być sticky na górze każdego obszaru? Czy brak alertów ma mieć stały (neutralny) wiersz?
3. **Kolejność sekcji na Home.** Dziś: Na dwór → Powietrze → Pogoda → Prognoza → Pyłki → Kalendarz. Master Plan
   §56: alerty → powietrze → pogoda → pyłki → outdoor → dodatkowe. Czy „Na dwór” zostaje na górze (dziś największy element)?
4. **Ekran startowy.** Pierwszy start bez wybranego obszaru: S4 jako ekran startowy (z wyjaśnieniem lokalizacji, §24)
   czy domyślny obszar (np. Warszawa) z przełącznikiem?
5. **Które mocki chcesz zobaczyć** (tabela 3.5): wszystkie z listy, czy tylko wybrane? Czy preview-build z
   `EXPO_PUBLIC_UI_MOCKS=1` ma być dla Ciebie, czy dla testerów?
6. **„Wkrótce” dla kąpielisk.** Pokazać sekcję „Kąpieliska — wkrótce” (bez danych) w buildzie produkcyjnym, czy ukryć
   do czasu źródła? Rekomendacja: ukryć w produkcji, pokazać w preview. Woda pitna: rekomendacja — w ogóle nie pokazywać.
7. **Profil „rodzina”.** Master Plan wymienia „family” w Phase 12, ale nigdzie nie definiuje, co to znaczy. Co ma
   zmieniać (np. progi „Na dwór” dla dzieci/seniorów)? Do czasu decyzji nie rysujemy.
8. **Prognoza godzinowa pogody.** Chcesz wykres godzinowy w S6 (wymaga zapisu `hourly` w bazie: migracja + ADR)?
   Jeśli tak — założę zadanie backendu przed mockiem.
9. **Ekran szczegółu pyłków.** Czy wykres godzinowy ma pokazywać też poziomy sezon/szczyt (progi EAACI), czy wyłącznie
   wartości? (Progi to demarkacje sezonu, nie ryzyko objawów — ADR-020.)
10. **Skeleton.** Master Plan §58/§80 mówi „Skeleton” dla loading; dziś spinner z etykietą. Czy projektujesz
    szkielet, czy zostaje spinner?
