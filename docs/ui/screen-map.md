# Za Oknem — mapa ekranów i kontrakt danych UI

**Do czego to służy.** Właściciel przygotowuje design wizualny osobno. Ten dokument NIE
projektuje wyglądu — opisuje **strukturę informacji**: jakie są ekrany, co na nich stoi, skąd
bierze się każdy element (endpoint + pole kontraktu), co jest już **LIVE**, a co wejdzie jako
**MOCKUP do podmiany na live**. Uwzględnia „Frontend UX/UI Specification v1” właściciela (jedna lokalizacja, Welcome + tematy, kąpieliska poza UI, powiadomienia ukryte, zakładki Start/Alerty/Ustawienia, karty aktywności). Stan faktyczny = kod `apps/mobile` + `packages/api-contract/openapi.json`
+ `docs/ROADMAP.md` na `main` = f6d7ece (po PR #83). Niczego tu nie zgadujemy: pole, którego nie ma w
`openapi.json`, jest zapisane jako „wymagane pole kontraktu” z zadaniem backendu (sekcja 4).

Powiązane: Master Plan §10, §24–25, §55–61, §80; ADR-026 (lokalizacja), ADR-027 (StyleSheet +
tokeny), ADR-028 (mocki UI, Proposed, razem z tym dokumentem); `docs/tasks/BACKLOG.md` (Phase 12,
zadania `TASK-7.9`, `TASK-8.11`, `TASK-12.10`–`12.19` dodane razem z tym dokumentem; wybór miejscowości: PR #85 (ADR-029, otwarty, niezmergowany — jego pola są tu traktowane jako „planowane”, nie istniejące na `main`)).

## 0. Legenda i zasady

| Znak | Status | Znaczenie |
|---|---|---|
| ✅ | LIVE | realne dane z naszego backendu, widoczne w aplikacji dziś |
| 🟡 | LIVE-częściowo | backend ma dane/endpoint, ale UI ich nie pokazuje w całości albo zakres danych jest niepełny |
| 🧪 | MOCK | dane przykładowe (fixture) do czasu, aż backend/źródło dostarczy kontrakt; widoczne tylko w dev/preview (sekcja 3) |
| ⛔ | BLOCKED | zatrzymane na konkretnym warunku (źródło, klucze, decyzja); BEZ mocka danych |
| ⬜ | TODO | do zrobienia, bez mocka (dane są w kontrakcie albo ekran jest statyczny) |

Reguły MVP, które zawężają strukturę (CLAUDE.md, Master Plan §11, §24, §62): **bez mapy, bez konta,
bez profilu osobowego, bez background location (tylko jednorazowa lokalizacja na pierwszym planie), bez monetyzacji, bez
Green Index, jedna aktywna lokalizacja (bez zapisanych: Dom/Praca/Ulubione)**. Konfigurujemy wyłącznie lokalizację + obserwowane tematy; są lokalne (device-based), nie kontem. Mobile czyta wyłącznie z naszego API
(reguła #14); wszystkie sekcje niosą `source`/`attribution`/freshness (reguły #6, #8).

**Stany do zaprojektowania** (Master Plan §59/§80), skrót używany w tabelach:
`L` loading · `E` empty (poprawnie brak danych) · `Er` error (backend/źródło nie odpowiada) ·
`S` stale (dane stare: znacznik czasu + oznaczenie) · `U` unavailable (źródło milczy/nigdy nie
zadziałało — NIE „brak zagrożeń”) · `P` brak uprawnień (lokalizacja odrzucona → wybór ręczny).
Dziś w kodzie jest wspólny zestaw: `LoadingState`, `EmptyState`, `Notice`, `FreshnessBadge`
(świeże/niedawne/nieaktualne/brak danych, glif + słowo + kolor). Nie ma jeszcze `Skeleton`
(Master Plan §58 i spec UI §40: ładowanie per moduł, bez globalnego spinnera; dziś loading = spinner z etykietą).

---

## 1. Drzewo nawigacji

```text
Root Stack (app/_layout.tsx)
│
├── Welcome (S0)            ← tylko pierwsze uruchomienie              ✅ TASK-12.17
├── Lokalizacja (S4)        ← onboarding i zmiana, JEDEN ekran         ✅ TASK-12.17/12.7 (tematy S10: ⛔ usunięte w production-ui-v1)
│
├── (tabs)                  ← dolna nawigacja, dokładnie 3 zakładki: Start | Alerty | Ustawienia
│   ├── Start           S1   🟡 jest jako „Dziś” (app/(tabs)/index.tsx) — do przebudowy TASK-12.18
│   │     [nagłówek] nazwa miejscowości ⌄ ──────────► S4 Zmiana lokalizacji ✅
│   │     karta werdyktu „Na dwór” ─────────────────► szczegóły werdyktu (reasons[]) ⬜
│   │     karta Powietrze ──────────────────────────► S5 Szczegóły: Powietrze          ✅ TASK-12.12
│   │     karta Pogoda ─────────────────────────────► S6 Szczegóły: Pogoda             ✅ TASK-12.12
│   │     karta Pyłki ──────────────────────────────► S7 Szczegóły: Pyłki              🧪 TASK-12.14
│   │     karty aktywności ─────────────────────────► powód po tapnięciu               ⬜ TASK-7.9 + 12.18
│   │     podgląd alertu ───────────────────────────► S3 Szczegół alertu
│   │
│   ├── Alerty          S2   🟡 jest (app/(tabs)/alerts.tsx; cała Polska)
│   │     pozycja alertu ───────────────────────────► S3 Szczegół alertu               ✅ TASK-9.7
│   │     stacje wodowskazowe (rzeki) ──────────────► S8 Stany rzek
│   │
│   └── Ustawienia      S9   🟡 jest jako placeholder (app/(tabs)/settings.tsx)
│         ├── Lokalizacja ────────────────────────► S4                                  ✅ TASK-12.7/12.17
│         ├── Obserwowane tematy ─────────────────► S10                                 ⬜ TASK-12.13
│         ├── Wygląd (Systemowy | Jasny | Ciemny) ► (przełącznik w wierszu)             ⬜ TASK-12.19
│         ├── Dostępność (respektuj ustawienia systemu)                                 ⬜ TASK-12.19
│         ├── Prywatność i dane ──────────────────► S13                                 ⛔/⬜ TASK-12.6, 14.2
│         ├── Źródła i licencje ──────────────────► S12                                 🟡 TASK-12.6
│         └── O aplikacji ────────────────────────► S14                                 🟡 TASK-12.6
│
└── Poza UI w tym wydaniu (NIE rysujemy, NIE „wkrótce”):
      Powiadomienia (ukryte do czasu FCM/APNs) · Kąpieliska · Woda pitna · Mapa · Konto/Profil
```

Uwagi do drzewa (decyzje otwarte są w sekcji 5):

- Nazwy zakładek wg spec UI: **Start | Alerty | Ustawienia**, ikony Home / Bell / Settings (dziś: „Dziś”, ikona ostrzeżenia).
  Żadnego hamburgera, zakładki „Więcej”, „Profil”, „Mapa”.
- **Jedna aktywna lokalizacja** (spec §3). Zmiana: Ustawienia → Lokalizacja albo tap w nagłówku Start. Brak listy zapisanych.
  Dziś Home pokazuje wszystkie 7 obszarów pod rząd — to zniknie (Start = jeden obszar, `/dashboard/latest?geo_area_id=`, ADR-026).
- **Nie nazywamy tego „profilem”** i nie pytamy o wiek, płeć, zdrowie, rodzinę (spec §2.3). Wcześniejszy profil
  alergika (gatunki pyłków, „rodzina”) jest wycofany (superseded) — zostają tylko tematy.
- Trasy to propozycja struktury Expo Router (np. `app/welcome.tsx`, `app/onboarding.tsx`, `app/location.tsx`,
  `app/details/air.tsx`, `app/alerts/[id].tsx`, `app/settings/*.tsx`).
- **Kąpieliska i woda pitna nie istnieją w UI** — ani jako sekcja, ani „wkrótce”, ani nieaktywny kafelek, ani wzmianka w
  Welcome (spec §8, §48). Komponent wody może istnieć w kodzie, ale o obecności decyduje data availability / feature flag.
- Dashboard jest **data-driven** (spec §50): pokazuje dostępne moduły (dziś Powietrze, Pogoda, Pyłki), układ dopasowuje się do liczby kart.

---

## 2. Ekrany — element po elemencie

Kolumna **Źródło** to endpoint + pole kontraktu z `openapi.json`/`schema.ts` (na `main`). **Task** = pozycja w BACKLOG.

### P0 wg spec UI §55 — gdzie to jest w tym dokumencie

| P0 | Ekran | Status dziś | Task |
|---|---|---|---|
| 1 Welcome | S0 | 🟡 finalny układ wg mockupu (PR #111–#117): panorama w kadrze, logo + intro + „Za Oknem” (Nunito), kapsuła 4 domen, CTA, stopka; lokalny scrim; niezweryfikowane na urządzeniu | TASK-12.17 |
| 2 Lokalizacja | S4 | ✅ wyszukiwarka `/places` + aktywacja + lista miast z `/areas`, jedna lokalizacja w pamięci urządzenia; **GPS: „Użyj mojej lokalizacji” → najbliższa miejscowość do potwierdzenia (PR #106, `POST /places/nearest`)**; Back do Welcome na pierwszym uruchomieniu (PR #110) | TASK-12.7, 12.17 |
| 3 Wybór zainteresowań | S10 (w onboardingu i Ustawieniach) | ✅ | TASK-12.13 |
| 4 Bottom Navigation (Start/Alerty/Ustawienia, ikony) | tabs | 🟡 jest, inne nazwy/ikona | TASK-12.18 |
| 5 Dashboard | S1 | 🟡 | TASK-12.18 |
| 6 Hero Verdict | S1 | ✅ dane i karta (LIVE, bez mocka) | TASK-7.8 ✅ |
| 7 Powietrze | S1/S5 | ✅ / ✅ szczegóły | TASK-12.12 |
| 8 Pogoda | S1/S6 | ✅ / ✅ szczegóły | TASK-12.12 |
| 9 Pyłki | S1/S7 | ✅ (prognoza CAMS) / 🧪 wykres | TASK-12.14 |
| 10 Rekomendacje aktywności | S1 | ⬜ **backend nie istnieje** (nie ma endpointu ani silnika) | **TASK-7.9** + 12.18 |
| 11 Alerty | S2/S3 | ✅ | TASK-9.7 |
| 12 Settings | S9 | 🟡 | TASK-12.6, 12.19 |
| 13 Light/Dark/System | S9 | 🟡 (dziś tylko wg systemu; brak przełącznika) | TASK-12.19 |
| 14 Accessibility fundamentals | wszystkie | 🟡 (role/labele, min. dotyk 44, glif + słowo + kolor, kontrast testowany; przegląd kodu Dynamic Type/Reduce Motion: [`a11y-review.md`](a11y-review.md); **TalkBack i skalowanie na urządzeniu niezweryfikowane**) | TASK-12.19 |
| 15 Loading/error/unavailable | wszystkie | 🟡 (spinner globalny; skeleton per moduł ⬜) | TASK-12.18 |

### S0. Welcome — ✅ (statyczny)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Nazwa, nagłówek „Sprawdź, co dzieje się wokół Ciebie”, tekst „Powietrze, pogoda, pyłki i lokalne alerty w jednym miejscu.”, „Bez konta. Bez zbędnych danych.”, CTA „Zaczynamy” | statyczne (copy ze spec UI §6) | ✅ | TASK-12.17 | brak sieci nie blokuje; **bez wzmianki o wodzie/kąpieliskach**; pojawia się raz (flaga lokalna „onboarding zakończony”) |
| Obraz hero | zasób graficzny od właściciela | ⬜ (dziś neutralny placeholder z tokenów; design po stronie właściciela) | — | — |

### S1. Start (Home) — 🟡 istnieje jako „Dziś”

Dziś: pełna lista obszarów, karty „Na dwór → Powietrze → Pogoda → Prognoza → Pyłki”, kalendarz pylenia, banery. Docelowa kolejność wg spec §17:
nagłówek lokalizacji → werdykt → karty statusu → „Co możesz dziś robić?” → aktywne alerty (spec §16 mówi też, że istotny alert ma być „relatywnie wysoko” — decyzja w sekcji 5).

| Element UI | Źródło (endpoint · pole) | Status | Task | Stany do zaprojektowania |
|---|---|---|---|---|
| Nagłówek: miejscowość ⌄, data | zapamiętana lokalizacja (nazwa) + `GET /dashboard/latest?geo_area_id=`; data z zegara urządzenia | ✅ (tap → S4) | TASK-12.7, 12.17, 12.18 | L (skeleton nagłówka), Er |
| Nagłówek: temperatura teraz, max/min dnia | `areas[].weather.params.temperature_2m`(wg `lib/weather.ts`), `areas[].forecast.days[0].params` (`temperature_2m_max/min`) | 🟡 dane ✅, UI ⬜ | TASK-12.18 | brak pogody/prognozy ⇒ pomijamy element, nie 0 |
| Baner/podgląd alertu | `dashboard.alerts.items[]`, `alerts.source_status`; `GET /hydro/latest` · `stations[].status` | ✅ cała Polska (banery); lokalnie: `areas[].local_alerts`, `geo_match` backend ✅, mobile nieużyte | TASK-9.7, 9.5 | „✓ Brak aktywnych ostrzeżeń” TYLKO przy potwierdzonym zero (źródło FRESH/RECENT); „? Nie udało się sprawdzić ostrzeżeń” przy U/S (ADR-012; `alertsBanner.ts`) — to dwa różne stany |
| Powiadomienie „nie udało się odświeżyć” | stan klienta | ✅ | — | Er przy istniejących danych |
| **Hero Verdict „Na dwór”** | `areas[].outdoor` · `level` (GOOD/MODERATE/POOR/UNKNOWN), `reasons[]`, `missing[]`, `valid_until` | ✅ LIVE (progi temperatura/opady/widoczność „do kalibracji”, ADR-016; **pyłków nie uwzględnia**); **zakaz mocka w każdym buildzie** | TASK-7.8 ✅ | UNKNOWN, starzenie na zegarze urządzenia, brak bloku (starszy backend); tap → szczegóły (powody z `reasons[]`, braki z `missing[]`) |
| Karta statusu „Powietrze” (stan + PM2.5) | `areas[].air` · `index.level`, `params`, `source_status`, `attribution` | ✅ | TASK-4.1/4.2/7.3 ✅ | indeks znika przy U/STALE (jest); „stacja ≤ 50 km” a nie „w Twoim mieście” (`distance_km`, `assignment_method`) |
| Karta statusu „Pogoda” (temperatura, opis) | `areas[].weather` · `params`, `source_status` | ✅ | TASK-5.4/7.3 ✅ | L, E, U, S |
| Karta statusu „Prognoza pyłków” | `areas[].pollen` · `current`, `unit`, `valid_at`, `freshness`, `source_status`, `kind="model_forecast"` | ✅ (prognoza modelu CAMS, nie pomiar; progi = sezon/szczyt EAACI, **nie ryzyko objawów** — ADR-020; etykieta „Niskie” to tylko „poniżej progu sezonu”) | TASK-8.8/8.9 ✅ | S/U ⇒ „Dane chwilowo niedostępne” bez poziomów; `null` = „brak danych”, nigdy 0 |
| Karty statusu dla pozostałych modułów (np. woda) | — | ⬜ renderowane tylko, gdy dane dostępne i włączona flaga (spec §50); **woda nie jest renderowana** | TASK-12.18 | layout dostosowany do liczby kart |
| „Co możesz dziś robić?” — karty aktywności (spacer, bieganie/rower, wietrzenie, wieczorny wysiłek) | **brak**: `outdoor` daje jeden werdykt + powody, nie rekomendacje per aktywność; brak przedziałów czasu (brak prognozy godzinowej powietrza i pogody) | ⬜ wymaga backendu — **bez mocka** (rekomendacja to interpretacja zbliżona do werdyktu; zakaz mockowania) | **TASK-7.9** (backend), TASK-12.18 (UI) | GOOD ✓ / CAUTION ! / AVOID × / UNKNOWN ? (glif + słowo, nie sam kolor); powód po tapnięciu; przedział czasu opcjonalny, dziś nieobecny |
| Kalendarz pylenia | `GET /pollen/calendar` | 🟡 (8 taksonów; ambrozja/pokrzywowate `not_covered`) | TASK-8.10 ✅ | pusty `active` ≠ „nic nie pyli” (karta „Typowy sezon” jest na S7, szczegóły na S7a) |
| Prognoza dobowa | `areas[].forecast` · `days[].params`, `freshness`, `fetched_at` | ✅ dane; blok `forecast` nie ma własnego `source_status`, ale pochodzi z tego samego pobrania Open-Meteo co pogoda (źródło `open_meteo`, ADR-010), więc **używamy `source_status.weather`**: efektywna świeżość = najgorsza z `forecast.freshness` i `source_status.weather.freshness` (`worstFreshness`, ADR-012), `fetched_at` jako wiek | TASK-12.18 | S/U ⇒ „Prognoza mogła się zmienić / niedostępna”, bez max/min w nagłówku; brak bloku `forecast` ⇒ pomijamy |
| Obszar bez pollingu / miejscowość bez pokrycia | `areas[].weather_polling_active=false`; `coverage` exact/nearby/regional/none, `grid_description` | ✅ | TASK-12.7 | Start: „Pogoda i pyłki dla tej miejscowości są chwilowo niedostępne. Powietrze może pochodzić ze stacji w okolicy.”; nearby/regional: „Dane ze stacji X, N km stąd” / „Stan dla obszaru w promieniu ok. 100 km — stacja X, N km”; `none` = UNAVAILABLE „Brak stacji pomiarowej w okolicy”; opis siatki w szczegółach pogody i pyłków |
| Stan ekranu: ładowanie / błąd / pusty / częściowa awaria | stan `DashboardProvider` | 🟡 (globalny spinner; każdy moduł ma własny stan, ekran nie blokuje się przy awarii jednego — spec §42) | TASK-12.18 | skeleton per moduł; „Nie udało się pobrać aktualnych danych. Spróbuj ponownie” bez błędów technicznych |
| Sekcja Woda / Kąpieliska | — | **poza UI** (nie rysujemy, nie „wkrótce”) | — | — |

### S2. Alerty — ✅ lista wg lokalizacji (województwo, ADR-013) / 🟡 bez chipów kategorii (jedna kategoria)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Ostrzeżenia hydrologiczne IMGW (lista) | `GET /dashboard/latest` · `alerts.items[]` (`event_type`, `severity_raw`, `areas[]`, `valid_until`, `issuing_office`, `freshness`), `alerts.scope="national"`, `alerts.source_status` | ✅ ogólnokrajowe, treść źródłowa (reguła #10) | TASK-7.2 ✅ | „Brak aktywnych ostrzeżeń” TYLKO gdy źródło FRESH/RECENT; inaczej „lista może być nieaktualna” / „niedostępne”; L, Er |
| Filtr „dla mojej lokalizacji” | `areas[].local_alerts[]`, `AlertOut.geo_match` (`voivodeship` / `unresolved`); alternatywnie `GET /alerts/latest?geo_area_id=` | ✅ mobile: „Dla Twojej lokalizacji” (`local_alerts`, `voivodeship`), „Do sprawdzenia” (`unresolved`, zawsze widoczne), „Pozostałe w Polsce”; brak `local_alerts` (starszy backend) ⇒ lista krajowa z jawną etykietą | TASK-9.7, 9.5 | etykieta zakresu („Twoje województwo” / „cała Polska” / „obszar nierozpoznany”) |
| Ostrzeżenia meteorologiczne | brak (`imgw_warningsmeteo` bez `normalize()`) | ⛔ BLOCKED — czeka na żywy przykład aktywnego ostrzeżenia (TASK-9.2) | TASK-9.2 | sekcji nie rysujemy jako „0 ostrzeżeń”; zob. sekcja 3 (zakaz mocka) |
| Zamknięcia kąpielisk | brak | ⛔ BLOCKED (zależy od źródła, ADR-021; TASK-11.3) | TASK-11.3 | j.w. |
| „Stany wody” (stacje WARNING/ALARM) | `GET /hydro/latest` · `stations[]` (`status` NORMAL/WARNING/ALARM/UNKNOWN, `water_level_cm`, `warning_level_cm`, `alarm_level_cm`, `observed_at`, `freshness`), `source_status` | ✅ cała Polska, limit 5 + „i N więcej” | TASK-7.2 ✅ | niezależne stany od ostrzeżeń (rule #1); stacje bez progów nie są oceniane (jest informacja) |
| …stacja najbliższa wybranej lokalizacji | brak parametru lokalizacji w `/hydro/latest` | ⬜ wymaga backendu (nearest-station, wzorzec ADR-006) | TASK-9.5 | — |
| Stan ekranu | j.w. | ✅ (L/Er/E, `Notice` przy odświeżeniu) | — | — |
| Filtry (chipy) Wszystkie / Pogoda / Powietrze / Woda / Inne | `AlertOut` nie ma pola kategorii (`event_type`, `source`) — kategoria wynikałaby z `source` po stronie klienta | ⬜ dziś jeden rodzaj alertów (hydro) | TASK-9.7 | pokazujemy tylko kategorie z danymi; przy jednej kategorii bez chipów; nazwa kategorii dla ostrzeżeń hydrologicznych — decyzja (sekcja 5) |
| Karta alertu (źródło, ważność, stopień) | `event_type`, `severity_raw`, `valid_until`, `issuing_office`, `fetched_at`, `source` | 🟡 (dziś: typ, stopień, obszary, „do”, biuro, freshness; brak „Źródło: IMGW” jako osobnej linii i godziny wydania) | TASK-9.7 | S: „Dane mogą być nieaktualne” |

### S3. Szczegół alertu — ✅ (bez „Co to oznacza?”: brak treści od właściciela)

Wszystkie pola potrzebne do szczegółu **już są** w `AlertOut` — to praca czysto UI (bez mocka, bez nowego
endpointu; wyszukiwanie po `external_id` dojdzie dopiero z deep linkiem, TASK-10.4).

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Tytuł: typ + stopień | `event_type`, `severity_raw` (surowe, bez tłumaczenia stopni własnym tekstem) | ✅ | TASK-9.7 | — |
| Treść źródłowa, komentarz | `description`, `comment` — **dosłownie**, bez streszczenia LLM (reguła #10) | ✅ | TASK-9.7 | pole `null` = nie rysujemy wiersza |
| Obszary | `areas[]` + `geo_match` | ✅ | TASK-9.7 | `unresolved` = jawna informacja |
| Ważność, wydano, pobrano | `valid_from`, `valid_until`, `published_at`, `fetched_at`, `freshness` | ✅ | TASK-9.7 | S (alert wygasły/nieaktualny) |
| Prawdopodobieństwo | `probability_pct` (nullable) | ✅ | TASK-9.7 | `null` = pomijamy |
| Biuro wydające, źródło, atrybucja | `issuing_office`, `source`, `GET /dashboard/latest · alerts.attribution` | ✅ | TASK-9.7 | — |
| „Co to oznacza?” — interpretacja Za Oknem (spec §20) | **brak**: nie ma pola ani źródła treści | ⬜ wymaga decyzji o treści (statyczne teksty per rodzaj ostrzeżenia, redagowane przez ludzi; **bez LLM**, reguła #10) | decyzja w sekcji 5 → osobny task po decyzji | wizualnie i słownie oddzielona od „Oficjalny komunikat”; nigdy jako komunikat urzędowy; bez tekstu = sekcji nie ma |

### S4. Lokalizacja: onboarding i zmiana (S4a: uprawnienie GPS) — ✅ wyszukiwarka i lista / 🟡 GPS (PR #106, bez weryfikacji na urządzeniu)

Jedna aktywna lokalizacja. Ten sam ekran w onboardingu (razem z tematami, S10) i jako Ustawienia → Lokalizacja / tap w nagłówku Start.
Backend na `main` (ADR-026): `GET /areas`, `POST /geo/locate`, `GET /dashboard/latest?geo_area_id=` — dziś **7 miast**; granice PRG niezaładowane.
ADR-029 (PR #85, `main`): wyszukiwanie dowolnej miejscowości (`GET /places?q=`, `GET /places/{id}`,
`POST /places/{id}/activate`, `coverage`) — UI zrobione w TASK-12.7. Bez zaimportowanego pliku GeoNames `/places` zwraca `[]` (ekran pokazuje „Nie znaleziono…”, a pod spodem lista miast z `/areas`).

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Lista dostępnych obszarów („Większe miasta”, dziś 7) | `GET /areas` · `geo_area_id`, `slug`, `name`, `weather_polling_active` | ✅ pokazywana przy pustym polu; błąd listy nie blokuje wyszukiwania | TASK-12.11 | L, E, Er (nie blokuje reszty aplikacji) |
| Pole „Wpisz miejscowość” | `GET /places?q=` (q ≥ 2, debounce 300 ms, latest-wins z anulowaniem) + `POST /places/{id}/activate` (429/503 → `GET /places/{id}`; `capacity_reached`/`budget_exhausted` = idź dalej, Start tłumaczy brak pogody) | ✅ live, **bez mocka** | TASK-12.7 | E („Nie znaleziono miejscowości …”), L, Er (bez technikaliów, „Spróbuj ponownie”); atrybucja GeoNames pod wynikami i w „Źródła danych” w Ustawieniach; `coverage` opisane na Start |
| „Użyj mojej lokalizacji” + wyjaśnienie (S4a) | `expo-location` (nowa zależność, uzasadnić w PR) → `POST /geo/locate` · `status`, `area`, `assignment_method`, `distance_km` | 🧪 stub **tylko dev/preview**; **w produkcji CTA nie pokazujemy**, dopóki TASK-12.3 nie działa (spec §7: żadnego CTA prowadzącego donikąd); backend ✅ | TASK-12.11 (stub), TASK-12.3 (live) | P: nie pytano / zgoda / odmowa → wybór ręczny (§25) / odmowa trwała; timeout GPS |
| Wynik lokalizacji | `GeoLocateResponse` | 🧪 j.w. | TASK-12.3 | trzy komunikaty: `point_in_polygon`, `nearest_area` („najbliższy obszar z danymi: X, N km” — NIE „Twoja gmina”), `out_of_range` |
| Zapamiętanie jednej aktywnej lokalizacji | AsyncStorage (`@react-native-async-storage/async-storage`): `{v:1, onboardingDone, location:{geoAreaId, placeId|null, name, label, latitude, longitude, attribution|null}}` — współrzędne to ŚRODEK wybranej miejscowości (dane publiczne), nie pozycja użytkownika | ✅ | TASK-12.17 | błąd/uszkodzenie odczytu ⇒ wartości domyślne (Welcome), uszkodzona lokalizacja ⇒ wybór ponownie bez Welcome; 404 dashboardu ⇒ wybór z komunikatem |
| Aktywacja obszaru / heartbeat | `POST /places/{id}/activate` przy wyborze i przy każdym otwarciu aplikacji z wybraną miejscowością (odświeża TTL); heartbeat instalacji (TASK-12.2) nadal ⬜ | ✅ aktywacja | TASK-12.7 | odmowa aktywacji (budżet) = obszar bez pogody, nie błąd |

Nie ma: mapy, wielu zapisanych lokalizacji, śledzenia w tle (reguła #11).

### S5. Szczegóły: Powietrze — ✅ (live, bez mocka; niezweryfikowane na urządzeniu)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Pełna lista parametrów z wiekiem pomiaru | `areas[].air.params{}` (wartość, jednostka, `observed_at`, `freshness`) | ✅ | TASK-12.12 | S per parametr, brak parametru = „brak”, nie 0 |
| Indeks EAQI: składowe i decydujący parametr | `air.index` · `level`, `params`, `dominant[]`, `missing{}`, `complete`, `valid_until` | ✅ | TASK-12.12 | `complete=false` ⇒ jawnie „niepełny”; U/S ⇒ bez indeksu |
| Stacja: nazwa, odległość, metoda | `station_name`, `distance_km`, `assignment_method` | ✅ | TASK-12.12 | — |
| Źródło, atrybucja, status źródła | `source`, `attribution`, `source_status{freshness,last_success_at}` | ✅ | TASK-12.12 | Er/U źródła |
| Trend / historia 24 h | brak w kontrakcie | poza MVP (Master Plan §11: pełna historia) | — | nie rysujemy |

### S6. Szczegóły: Pogoda i prognoza — ✅ (live: pola bieżące + prognoza dobowa; niezweryfikowane na urządzeniu)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Wszystkie pola pogody z jednostkami | `weather.params{}` | ✅ | TASK-12.12 | S per pole |
| Prognoza dobowa (dni) | `forecast.days[].params`, `valid_from/until`, `freshness`, `fetched_at` | ✅ | TASK-12.12 | S, E |
| Prognoza godzinowa / wykres | brak — Open-Meteo `hourly` jest pobierane, ale zapisywana jest tylko godzina zgodna z `current` | ⬜ wymaga backendu (nowa tabela/migracja); NIE mockujemy, dopóki właściciel nie zdecyduje, że chce | brak taska — decyzja, sekcja 5 | — |
| Źródło, atrybucja | `weather.attribution`, `forecast.attribution` | ✅ | TASK-12.12 | — |

### S7. Szczegóły: Pyłki — 🧪 (część live)

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Wartości „teraz” (5 gatunków) i poziomy sezon/szczyt | `pollen.current`, `unit`, `valid_at` | ✅ (jak na S1) | — | S/U ⇒ bez poziomów |
| Maksima dobowe na kolejne dni | `pollen.days[]` · `date`, `max{5 gatunków}` | ⬜ (dane ✅, nieużyte w UI) | TASK-12.14 | `null` = „brak danych” |
| **Wykres godzinowy** | brak: baza ma 96 wierszy/obszar/dobę (ADR-020), ale API wystawia tylko `current` + `days` | 🧪 MOCK (typ proponowany `PollenHourly`) → live po TASK-8.11 | TASK-12.14 (mock), TASK-8.11 (backend) | zawsze jako **model_forecast** (tytuł „prognoza modelu CAMS, nie pomiar”), wersja tekstowa/tabela dla a11y, S/U ⇒ bez wykresu |
| **Typowy sezon** — kompaktowa karta: jeden status sezonu (ikona + tytuł), jedno zdanie, jedno zdanie kontekstu, link „Zobacz kalendarz sezonów” | `GET /pollen/calendar` · `active[]` (`phase`, `name_pl`) + poziom aktualnej prognozy (nagłówek karty Pyłki) | ✅ | — | 5 stanów: poza sezonem / początek / trwa / szczyt / dobiega końca (priorytet: szczyt; wspólna faza = ta faza; mieszanka = „trwa”). **Kalendarz to kontekst dla prognozy, nie jej zamiennik** (reguła #7): poza sezonem nigdy „nic nie pyli”, a gdy prognoza pokazuje pyłki, karta mówi to wprost. Bez metodologii, dekad, taksonów i dłuższych disclaimerów |
| Atrybucja CAMS + Open-Meteo, `forecast_reference_time` | `pollen.attribution`, `forecast_reference_time`, `model` | ✅ | — | — |

### S7a. Kalendarz sezonów (szczegóły typowego sezonu) — ✅

Ukryty ekran (`/pollen-calendar`), otwierany linkiem z karty „Typowy sezon” na S7. Te same dane co karta (jedno żądanie `GET /pollen/calendar` w `DashboardProvider`), nic nowego z sieci.

| Element UI | Źródło | Status | Stany |
|---|---|---|---|
| „Teraz w typowym sezonie”: alergen, faza (początek / szczyt / koniec), okres sezonu, okno szczytu | `active[]` · `phase`, `season_*`, `peak_*` | ✅ | pusty `active` ⇒ „Żaden z ujętych alergenów nie jest teraz w typowym sezonie” |
| „Nadchodzące” (start w ciągu 30 dni) | `upcoming[]` | ✅ | brak ⇒ sekcja ukryta |
| „Jak działa kalendarz?”: typowy przebieg, nie pomiar i nie prognoza; ograniczenia (`coverage_warning`, `not_covered`), `disclaimer` | `coverage_warning`, `not_covered[]`, `disclaimer`, `active_message` | ✅ (teksty serwera dosłownie) | — |
| Źródło | `attribution` | ✅ | — |

### S7b. Twoja okolica (dane historyczne o lokalizacji, ADR-032) — 🟡 (hałas; reszta sekcji ⬜)

Ukryty ekran (`/neighborhood`), otwierany wierszem „Twoja okolica” na Start (pod podglądem alertów). Wiersz jest widoczny **tylko**, gdy `GET /api/v1/neighborhood?geo_area_id=` zwraca `enabled=true` (flaga sekcji po stronie serwera); przy błędzie, ładowaniu i starszym backendzie nie ma go wcale. Bez nowej zakładki, mapy, konta i push. To nie jest stan na dziś ani ostrzeżenie (reguła #7): bez znaczka świeżości, bez porad.

| Element UI | Źródło | Status | Stany |
|---|---|---|---|
| Nagłówek sekcji + jedno zdanie odpowiedzi („Najbliższe punkty pomiarowe”) | `sections[].availability`, `title` | ✅ | `available` / `no_coverage` („W pobliżu nie ma punktu pomiarowego” + promień) / `no_records` / `unavailable` („Dane chwilowo niedostępne” — nie „brak”) / `pending_verification` |
| Najbliższy punkt na kategorię: miejscowość, odległość „ok. X km”, okres pomiaru, wyniki wg pory doby (dB, przecinek) | `items[]` | ✅ | pusta lista przy `available` ⇒ stan pusty, nie pusta karta |
| Przekroczenie | `measurements[].exceedance_db` | ✅ | pokazane tylko gdy > 0, słowami źródła; 0/null nie znaczy „w normie” |
| Ostrzeżenie o nieudanym ostatnim pobraniu (dane starsze zostają) | `retrieval_status = degraded` | ✅ | okres danych nadal = okres źródła, nigdy „teraz” |
| Cel pomiaru, ograniczenia, atrybucja CC BY 4.0 z oznaczeniem przetworzenia, linki do źródła i licencji | `purpose`, `limitations[]`, `attribution`, `source_url`, `license_url` | ✅ (tekst atrybucji składa serwer) | — |

### S8. Stany rzek (hydrologia) — ✅ pełna lista (bez kąpielisk i wody pitnej) / ⬜ stacja najbliższa lokalizacji

Kąpieliska i woda pitna **nie występują w UI** (spec §8, §48): brak sekcji, „wkrótce”, nieaktywnego kafelka i placeholdera; kąpieliska wracają
przed sezonem jako osobny etap. Tabela dotyczy wyłącznie rzek.

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Stacje w stanie ostrzegawczym/alarmowym | `GET /hydro/latest` · `stations[]` | ✅ cała Polska | TASK-7.2 ✅ | jak S2 |
| Pełna lista stacji z poziomem i progami | `GET /hydro/latest` · `stations[]` (`water_level_cm`, `warning_level_cm`, `alarm_level_cm`, `status`, `observed_at`, `freshness`) | ✅ `app/(tabs)/rivers.tsx` (wejście: „Wszystkie stacje” w Alertach): grupy alarm / ostrzegawczy / poniżej progów / odczyt nieaktualny / bez progów („nie oceniamy”), wyszukiwanie po nazwie (bez diakrytyków), paginacja | TASK-12.16 | stary odczyt NORMAL nie mówi „poniżej progów”; stary ALARM/WARNING dalej widoczny z wiekiem; źródło milczące ⇒ baner |
| Stacja najbliższa wybranej lokalizacji | brak parametru lokalizacji w `/hydro/latest` | ⬜ wymaga backendu | TASK-9.5 | — |
| Kąpieliska (status, E. coli, enterokoki, sinice, daty badań), woda pitna | brak `/water`; ADR-021 (⛔), `sanepid_water` ⛔ | ⛔ **poza UI** | TASK-11.x | nie renderować |

### S9. Ustawienia (hub) — 🟡 placeholder

Dziś: trzy karty (O aplikacji + wersja, Źródła danych z `attribution`, Prywatność — zdanie). Docelowo wg spec §22–29:

| Wiersz | Prowadzi do | Status | Task |
|---|---|---|---|
| Lokalizacja (bieżąca miejscowość) | S4 | ✅ | TASK-12.7 |
| Obserwowane tematy (Powietrze, Pogoda, Pyłki, Alerty, Aktywność) | S10 | ⬜ | TASK-12.13 |
| Wygląd: Systemowy / Jasny / Ciemny (domyślnie Systemowy) | przełącznik w wierszu | ⬜ (dziś wyłącznie wg systemu) | TASK-12.19 |
| Dostępność | preferujemy ustawienia systemowe zamiast własnych duplikatów (Większy tekst, Wysoki kontrast, Ogranicz animacje) | ⬜ | TASK-12.19 |
| Prywatność | S13 | ⛔ treść prawna / ⬜ | TASK-12.6, 14.2 |
| Źródła i licencje | S12 | 🟡 | TASK-12.6 |
| O aplikacji | S14 | 🟡 | TASK-12.6 |
| Powiadomienia | — | **ukryte w produkcji** (spec §25 wariant A, preferowany; brak FCM/APNs) | TASK-12.15 |

### S10. Obserwowane tematy — ✅ (lokalne, bez backendu, bez mocka; Aktywność dopiero po TASK-7.9)

To NIE jest profil (spec §3). Lokalna preferencja urządzenia: które moduły widać na Start. Nie zmienia faktów źródłowych (Master Plan §61)
i **nie może ukryć alertów/danych bezpieczeństwa** poza wyborem „Alerty”. Ten sam komponent kafelków w onboardingu („Co chcesz śledzić?”) i w Ustawieniach.

| Element UI | Źródło | Status | Task | Stany |
|---|---|---|---|---|
| Kafelki multi-select: Powietrze, Pogoda, Pyłki, Alerty (i zagrożenia), Aktywność na zewnątrz | lokalne | ⛔ USUNIĘTE (production-ui-v1): brak kroku „Co chcesz śledzić?” i pickera w Ustawieniach; `Settings.topics` ignorowane przy odczycie | TASK-12.13, 12.17 | pusty wybór = wszystkie dostępne; brak kafelków dla Woda pitna/Kąpieliska |
| Dostępność tematu zależy od danych | dostępność modułu (dane/flaga) | ✅ (kafelka Aktywność nie ma) | TASK-12.13 | „Aktywność” pojawia się dopiero po TASK-7.9 |
| Skutek na Start | lokalne | ⛔ USUNIĘTE (`lib/topics.ts`); Start pokazuje wszystkie dostępne moduły | TASK-12.13 | wyłączony temat = brak karty, nie „0”; **baner realnego ostrzeżenia nigdy nie jest ukrywany** (decyzja do pkt 9 z sekcji 5.2: temat „Alerty” steruje tylko cichą linią „brak/nie sprawdzono”) |
| Dawny zakres „profil alergika” (gatunki pyłków, „rodzina”, „outdoor” jako profil; TASK-12.4 v1) | **SUPERSEDED** przez spec UI v1: zostają wyłącznie tematy | wycofane | — | brak decyzji do podjęcia |

### S11. Powiadomienia — ukryte w produkcji

Spec §25: bez FCM/APNs nie pokazujemy przełączników sugerujących działającą funkcję; preferowany wariant A = ekran i wiersz w ogóle nie istnieją
w buildzie produkcyjnym. Backend rejestracji urządzeń (`POST /devices`, TASK-10.1 🟡) jest gotowy, wysyłki nie ma.

| Element UI | Źródło | Status | Task |
|---|---|---|---|
| Wiersz „Powiadomienia” w Ustawieniach, zgoda systemowa, kategorie | `expo-notifications`; preferencje: brak modelu | ⛔ klucze FCM/APNs (TASK-10.1), model preferencji (TASK-10.3a) | TASK-10.3/10.5; do tego czasu **ukryte** (TASK-12.15) |

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
- rekomendacje aktywności („Co możesz dziś robić?”), werdykt „Na dwór” oraz indeks jakości powietrza (liczone przez backend z realnych danych; ich mock
  mógłby wyglądać jak zalecenie zdrowotne).

Zamiast mocka: **sekcja nie istnieje w UI** (ani „wkrótce”, ani nieaktywny kafelek, ani placeholder — spec UI §8, §25, §48). Sekcje ⛔ w sekcji 2 tak wyglądają.
Pozostałe mocki dotyczą wyłącznie kształtów danych niezwiązanych z bezpieczeństwem (lista gmin,
wynik lokalizacji, prognoza pyłków modelowa, preferencje).

### 3.2. Mechanizm w kodzie (do wdrożenia w TASK-12.10)

| Element | Zasada |
|---|---|
| Flaga | `EXPO_PUBLIC_UI_MOCKS` (`"1"` włącza, `"0"` wyłącza) oraz `EXPO_PUBLIC_APP_ENV` (`development`/`preview`/`production`; brak = production — fail-safe). Funkcja `mocksEnabled()` w `lib/mock/flag.ts`: **dev** (`__DEV__`) domyślnie włączone, `=0` wyłącza (żeby sprawdzać live); **preview** wyłączone, chyba że profil ustawia `=1` (build do oglądania makiet przez właściciela); **production zawsze wyłączone** — flaga jest ignorowana. Wartości `EXPO_PUBLIC_*` są wypiekane w bundlu (README), więc zmiana wymaga przebudowy. |
| Fixture'y | tylko w `apps/mobile/lib/mock/`; każdy plik fixture typowany typami z kontraktu (`schema.ts`, np. `satisfies AreaOut[]`). Pola spoza kontraktu mają typy `Proposed*` w `lib/mock/proposed.ts`, każdy z komentarzem „wymagane pole kontraktu — TASK-…” (sekcja 4). Gdy backend dostarczy pole, typ `Proposed*` zastępuje wygenerowany z `schema.ts` i kompilator wskazuje fixture'y do poprawy. |
| Adapter | wspólny hook per źródło danych: `useX(): Sourced<T>` gdzie `Sourced<T> = { data: T \| null; state: LoadState; origin: "live" \| "mock" }`. Hook sam decyduje o źródle (`mocksEnabled()` ⇒ fixture, inaczej API); **komponent dostaje ten sam typ `T` i nie wie, skąd** — podmiana na live to zmiana źródła w hooku, nie komponentu. |
| Dane bezpieczeństwa | hooki `useAlerts`, `useHydro`, `useActivities`, `useWater*` budowane fabryką **bez parametru `mock`** (typ nie pozwala go podać). Test `lib/mock/policy.test.ts` dodatkowo pilnuje, że w `lib/mock/**` nie ma nazw/eksportów z listy zakazanych (alert, hydro, water, bath, kąpiel, ostrzeż, ALARM, WARNING…). |
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

Mocki istnieją tylko tam, gdzie brakuje kontraktu, a mock nie jest danymi bezpieczeństwa ani werdyktem. Reszta idzie od razu live albo czeka na backend.

| # | Task | Co | Dlaczego w tej kolejności |
|---|---|---|---|
| 0 | TASK-12.10 UI-MOCK-0 | flaga, `lib/mock/`, `Sourced<T>`, `MockBadge`/`MockBanner`, testy polityki | bez tego każdy mock wymyślałby własny mechanizm; ADR-028 |
| 1 | TASK-12.11 UI-MOCK-1 | Lokalizacja: lista 7 miast **live**; wyszukiwarka i GPS-stub tylko dev/preview | największa luka (P0), backend gotowy; produkcja bez udawanego searcha i bez CTA donikąd; po merge PR #85 wyszukiwarka idzie live (TASK-12.7) |
| 2 | TASK-12.12 UI-LIVE-1 | Szczegóły Powietrze/Pogoda — **live, bez mocka** | kontrakt ma wszystko poza trendem |
| 3 | TASK-12.14 UI-MOCK-3 | wykres godzinowy pyłków, `model_forecast` | jedyny mock z polem spoza kontraktu (`hourly`) → TASK-8.11; poza P0 (spec §56) |
| — | TASK-12.13, 12.17, 12.18, 12.19 | tematy, Welcome/onboarding, przebudowa Start, motyw | **live/lokalne, bez mocków** (P0) |
| — | TASK-7.9 | rekomendacje aktywności | **backend, nie mock** (P0 #10) |
| — | TASK-12.15, 12.16 | powiadomienia ukryte; ekran rzek | bez mocków |

## 4. Kontrakt danych dla przyszłych endpointów

Mock nie wyprzedza rzeczywistości: każde pole, które fixture albo UI zakłada, a którego nie ma w `openapi.json` na `main`, jest tu zapisane z zadaniem backendu.

| Wymagane pole / endpoint | Potrzebne dla | Dziś w backendzie | Task | Uwagi |
|---|---|---|---|---|
| `areas[].activities[]` (`activity`, `status` GOOD/CAUTION/AVOID/UNKNOWN, `reasons[]` z kodem/parametrem/progiem, `missing[]`, `valid_until`, `window` = `null` do czasu danych godzinowych) | Start: „Co możesz dziś robić?” | brak; `outdoor` to jeden werdykt | **TASK-7.9** (dodany) | deterministyczny silnik (jak ADR-016), bez LLM, bez pyłków (progi ADR-020 to nie ryzyko objawów), wymaga ADR; **bez mocka** |
| przedziały czasu aktywności („najlepiej przed 17:00”, „po 18:00”) | karty aktywności | brak prognozy godzinowej powietrza i pogody (zapisywana tylko godzina `current`; powietrze to pomiary GIOŚ, CAMS Air = MVP+) | **brak taska** — decyzja właściciela (sekcja 5) | `window` zostaje `null`; nie rysujemy „wieczorny wysiłek” bez danych |
| `GET /pollen/latest?geo_area_id=` oraz `areas[].hourly[]` (`valid_at` + 5 gatunków `number\|null`) | S7 wykres godzinowy | `GET /pollen/latest` nie ma parametru (funkcja `latest_pollen(db, geo_area_id)` go wspiera); `hourly` nie jest wystawione | **TASK-8.11** | brak snapshotu ⇒ `areas: []` + `source_status`, to stan „niedostępne”, nie „puste”; NULL ≠ 0 |
| `GET /places?q=`, `GET /places/{id}`, `POST /places/{id}/activate`, `coverage` | S4 wyszukiwanie dowolnej miejscowości | ✅ `main` (PR #85) | UI ✅ TASK-12.7 | dane: wymagany import GeoNames na serwerze |
| `GET /areas?q=&limit=&offset=` (wyszukiwanie gmin) | S4 | zastąpione ścieżką `/places` (PR #85); granice PRG nadal ⛔ człowiek | TASK-12.2, 6.2 | — |
| nearest-station hydro per lokalizacja | S2/S8 | `/hydro/latest` bez lokalizacji | TASK-9.5 | deterministyczne po stronie serwera (reguła #9) |
| kategoria alertu (pogoda/powietrze/woda/inne) | S2 chipy | brak pola; wynika z `source` | TASK-9.7 (po stronie klienta albo pole w kontrakcie) | tylko kategorie z danymi |
| treść „Co to oznacza?” per rodzaj ostrzeżenia | S3 | brak | decyzja właściciela | statyczne, redagowane przez ludzi |
| trend powietrza (spec §2.2) | S5 | brak endpointu historii | **brak taska** — decyzja (Master Plan §11: pełna historia poza MVP) | nie rysujemy |
| `GET /water/latest`, ostrzeżenia meteo w `alerts`, preferencje powiadomień | — | ⛔ | TASK-11.4, 9.2, 10.3a | **poza UI** / bez mocka |
| lokalne ustawienia (aktywna lokalizacja, tematy, motyw, flaga onboardingu) | S0, S4, S9, S10 | n/d — wyłącznie urządzenie | TASK-12.17 | bez backendu, bez konta |

Pola, które **są** w kontrakcie, a UI ich jeszcze nie używa (nie wymagają backendu ani mocka):
`air.station_name`, `air.distance_km`, `air.assignment_method`, `air.index.params`, `pollen.days[]`,
`pollen.forecast_reference_time`, `areas[].local_alerts`, `AlertOut.{description,comment,probability_pct,published_at,geo_match}`,
`AreaOut.weather_polling_active`, wszystkie stacje z `/hydro/latest` poza WARNING/ALARM, `forecast.days[0]` (max/min do nagłówka).

## 5. Macierz „co live dziś” i decyzje właściciela

### 5.1. Macierz (jednym rzutem oka)

| Obszar | Backend / API | UI mobile dziś | Docelowo |
|---|---|---|---|
| Powietrze: parametry GIOŚ + EAQI | ✅ | ✅ (bez nazwy stacji/odległości) | ✅ szczegóły S5 (live) |
| Pogoda bieżąca (15 pól MVP) | ✅ | ✅ | ✅ szczegóły S6 (live) |
| Prognoza dobowa (3 dni) | ✅ (dostępność z `source_status.weather`) | 🟡 (tylko etykieta freshness) | max/min w nagłówku Start |
| Prognoza godzinowa pogody / powietrza | ⬜ | ⬜ | decyzja właściciela |
| Werdykt „Na dwór” | ✅ (progi do kalibracji) | ✅ | tap → powody |
| **Rekomendacje aktywności** | ⬜ nie istnieje | ⬜ | TASK-7.9 → 12.18 (bez mocka) |
| Pyłki: prognoza modelu CAMS (`current`, `days`) | ✅ | ✅ (`current`) | ⬜ `days` w S7 |
| Pyłki: wykres godzinowy | 🟡 dane w bazie, brak w API | ⬜ | 🧪 TASK-12.14 → TASK-8.11 (poza P0) |
| Kalendarz pylenia | 🟡 (8 taksonów) | ✅ | — |
| Ostrzeżenia hydrologiczne (cała Polska) | ✅ | ✅ | — |
| Ostrzeżenia lokalne (województwo) | ✅ | ⬜ nieużyte | TASK-9.7 |
| Ostrzeżenia meteorologiczne | ⛔ TASK-9.2 | ⛔ | po żywym przykładzie IMGW |
| Stany rzek (cała Polska) | ✅ | ✅ (WARNING/ALARM) | ⬜ pełna lista (TASK-12.16) |
| Stany rzek po lokalizacji | ⬜ | ⬜ | TASK-9.5 |
| Kąpieliska, woda pitna | ⛔ | **poza UI** | po decyzji o źródle, przed sezonem |
| Lokalizacja: 7 miast | ✅ `/areas`, `?geo_area_id=` | ✅ lista „Większe miasta” | TASK-12.11 |
| Lokalizacja: dowolna miejscowość | ✅ `main` (PR #85) | ✅ | TASK-12.7 |
| Lokalizacja: GPS jednorazowy | ✅ `POST /places/nearest` (PR #106; `POST /geo/locate` czeka na granice PRG) | 🟡 (PR #106) | 🧪 dev/preview → TASK-12.3 (bez CTA w produkcji do czasu live) |
| Welcome + onboarding (lokalizacja) | — | ✅ | TASK-12.17 |
| Tematy „Co chcesz śledzić?” (lokalne) | — | ⛔ zastąpione przez production-ui-v1 | TASK-12.13 |
| Motyw Systemowy/Jasny/Ciemny, dostępność | — | ✅ wybór w Ustawieniach → Wygląd (zapis lokalny); dostępność wg [`a11y-review.md`](a11y-review.md) | TASK-12.19 |
| Powiadomienia push | 🟡 rejestracja urządzeń; ⛔ klucze | ⬜ | **ukryte** (TASK-12.15) |
| Źródła i licencje | ✅ `attribution` | 🟡 | TASK-12.6 |
| Polityka prywatności | — | ⛔ brak dokumentu | TASK-14.2 |
| Szczegół alertu (fakt) / „Co to oznacza?” | ✅ pełne `AlertOut` / ⬜ treść | ⬜ | TASK-9.7 / decyzja |

### 5.2. Decyzje

**Rozstrzygnięte specyfikacją UI właściciela:** nazwy zakładek (Start | Alerty | Ustawienia); jedna lokalizacja; kąpieliska i woda pitna poza UI (bez „wkrótce”);
powiadomienia ukryte; loading = skeleton per moduł; „profil” zastąpiony tematami; produkcja bez udawanego searcha i bez CTA GPS, dopóki nie działa.

**Otwarte (dla właściciela):**

1. **Alert na Start: wysoko czy niżej?** Spec §17 stawia Active Alerts na 5. miejscu, §16 mówi „relatywnie wysoko” przy istotnym alercie. Proponowana reguła: istotny alert (FRESH/RECENT, ostrzeżenie/alarm) nad werdyktem, brak alertów = subtelny wiersz na dole.
2. **Zakres banera/podglądu po wyborze lokalizacji:** tylko województwo użytkownika, czy też „cała Polska”? (`unresolved` jest zawsze pokazywane, nie ukrywane.)
3. **Kategoria ostrzeżeń hydrologicznych w chipach Alerty:** spec ukrywa „Woda”, ale ostrzeżenia hydrologiczne są LIVE. Jak je nazwać (Woda / Hydrologia / Pogoda)?
4. **Przedziały czasu w kartach aktywności** („Najlepiej przed 17:00”, „wieczorny wysiłek po 18:00”) wymagają prognozy godzinowej powietrza i pogody, której nie mamy (powietrze: tylko pomiary GIOŚ). Wersja 1: status + powód bez przedziałów (`window=null`)? Czy zakładamy zadanie prognozy godzinowej (migracja + ADR)?
5. **Lista aktywności i progi** (spacer, bieganie/rower, wietrzenie, wieczorny wysiłek): kto zatwierdza progi? Dziś progi „Na dwór” PM/UV/wiatr mają źródła, temperatura/opady/widoczność są „do kalibracji”.
6. **„Co to oznacza?” w szczegółach alertu:** statyczne teksty per rodzaj ostrzeżenia redagowane przez ludzi (bez LLM) — czy tak, i kto pisze?
7. **Trend w szczegółach powietrza** (spec §2.2) — brak danych historycznych w API; pomijamy w v1?
8. **Gatunki pyłków do śledzenia** — spec UI ich nie przewiduje (tylko temat „Pyłki”). Zostaje bez wyboru gatunków?
9. ~~**Tematy a bezpieczeństwo**~~ — **rozstrzygnięte w kodzie (TASK-12.13)**: temat „Alerty” można wyłączyć, ale baner istotnego ostrzeżenia na Start jest zawsze widoczny (wyłączenie ukrywa tylko ciche „brak aktywnych ostrzeżeń / nie udało się sprawdzić”); zakładka Alerty zawsze istnieje. Zgodne z AC TASK-12.13 i rekomendacją.
10. **Ekran startowy po Welcome bez GPS i bez wyboru:** dziś to lista 7 miast (+ wyszukiwarka dopiero po PR #85); czy dopuszczamy domyślny obszar?
11. **Preview-build z `EXPO_PUBLIC_UI_MOCKS=1`:** dla Ciebie czy dla testerów; które mocki chcesz zobaczyć (wyszukiwarka, GPS-stub, wykres pyłków)?
12. **Etykieta „Niskie” na karcie pyłków:** spec używa „Niskie”; dane to „poniżej progu sezonu” wg modelu CAMS (nie ryzyko objawów, ADR-020). Dopuszczasz „Niskie (prognoza modelu)”?

> **Aktualizacja 2026-10-02 (po PR #117):** stan ekranów Welcome, Lokalizacja (GPS, nawigacja) i usunięcie tematów
> odzwierciedla kod na `main`; reszta dokumentu to wcześniejsza mapa (część wierszy o mockach jest historyczna —
> produkcyjny UI nie używa mocków danych bezpieczeństwa). Źródło prawdy dla UI: `production-ui-v1.md`.
