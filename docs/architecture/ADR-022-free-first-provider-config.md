# ADR-022: FREE-FIRST + konfiguracja providera Open-Meteo (Free → Paid bez zmian w kodzie)

- **Date:** 2026-10-01
- **Status:** Accepted

## Context

Decyzje właściciela (2026-10-01): MVP na darmowych / open-data źródłach; przed jakąkolwiek
monetyzacją przejście na komercyjny plan Open-Meteo ma być **wyłącznie zmianą konfiguracji**.
Dotąd `BASE_URL` Open-Meteo był zahardkodowany w `connectors/open_meteo/client.py` i
`connectors/open_meteo_pollen/client.py`. ADR-003 (licencja niekomercyjna), ADR-001/-004
(snapshot, cykl źródła) i ADR-020 (pyłki jako prognoza modelowa) pozostają w mocy.

## Decision

### 1. Polityka FREE-FIRST

Jeśli funkcję można zbudować na wiarygodnym darmowym / open-data źródle, nie integrujemy
płatnego odpowiednika w MVP. Kierunek (tabela właściciela):

| Obszar | Źródło w MVP | Pomijamy | Monetyzacja |
|---|---|---|---|
| pogoda | Open-Meteo Free | — | wymaga planu komercyjnego Open-Meteo |
| pyłki | Open-Meteo / CAMS (prognoza modelowa) | Google Pollen API | plan komercyjny Open-Meteo (dane CAMS: OK z atrybucją) |
| powietrze (pomiary) | GIOŚ | Airly itp. | OK z atrybucją (CC BY 4.0) |
| model jakości powietrza | CAMS | — | OK z atrybucją Copernicus |
| kąpieliska | GIS / Sanepid — brak API/zgody, patrz ADR-021 | — | nieustalone |
| woda pitna | Sanepid / PSSE / WSSE — brak API/zgody, patrz ADR-021 | — | nieustalone |
| alerty | RCB (brak publicznego API) + źródła urzędowe | — | nieustalone |
| hydrologia | darmowe dane IMGW (po weryfikacji konkretnego datasetu) | — | wymaga umowy IMGW lub potwierdzenia HVD |
| wody powierzchniowe | GIOŚ | — | OK z atrybucją |
| geo | GUGiK / PRG / TERYT | — | PRG: OK wg brzmienia strony (brak formalnej licencji) |
| środowisko / awarie | GIOŚ, później EFFIS / Copernicus | — | OK z atrybucją (EFFIS CC BY 4.0) |

**FREE-FIRST ≠ approved ≠ dostępne.** Tabela to kierunek, nie zgoda. Każde źródło dalej
przechodzi Source Approval Gate (rule #15) i ma wpis w `docs/data/source-registry.md`.
Część wierszy ma jawne blokady dostępności lub licencji (kąpieliska — ADR-021; woda pitna;
`imgw_warningsmeteo` — brak żywego kształtu; PRG/TERYT — licencja UNKNOWN, patrz registry):
„darmowe” nie znaczy „mamy dane i prawo ich użycia”, ani „wolno monetyzować”. Rezerwa dostawcy pogody (MET Norway, CC BY 4.0, komercyjnie OK z atrybucją): registry `met_norway`. Darmowy ≠ komercyjnie wolny: IMGW i
Open-Meteo Free są niekomercyjne.

### 2. Konfiguracja providera (env), zero hardcode

`app/config.py` (`Settings`, env): `OPEN_METEO_FORECAST_BASE_URL`,
`OPEN_METEO_AIR_QUALITY_BASE_URL`, `OPEN_METEO_API_KEY` (opcjonalny). Domyślnie hosty Free
(`api.open-meteo.com/v1/forecast`, `air-quality-api.open-meteo.com/v1/air-quality`), brak klucza.
Gdy klucz jest ustawiony, `get_json()` (`connectors/open_meteo/client.py`, wspólny dla obu
connectorów — ten sam provider i klucz) dodaje go jako parametr `apikey`. Przejście na plan
komercyjny = ustawić w środowisku hosty `customer-*` + klucz; zero zmian w logice. Wartości
czytane przy każdym wywołaniu (nie przy imporcie).

**Zweryfikowane 2026-10-01 w oficjalnej dokumentacji** (WebFetch: open-meteo.com/en/pricing,
/en/docs, /en/docs/air-quality-api):
- parametr klucza to `apikey` („Only required to commercial use to access reserved API resources
  for customers”); na pricing: zapytania wyglądają jak `…&apikey=abc123`;
- plan płatny używa dedykowanego hosta `customer-api.open-meteo.com`; docs: „The server URL
  requires the prefix `customer-`”;
- darmowe API „exclusively for non-commercial use”, 10 000 wywołań/dzień, bez gwarancji
  uptime; plany: Standard 1 M / Professional 5 M / Enterprise 50 M+ wywołań/mies.; Air Quality
  API jest w „Basic APIs” dostępnych na każdym planie; plan płatny daje licencję komercyjną.

**NIE zweryfikowane:** dokładna nazwa hosta `customer-air-quality-api.open-meteo.com` —
dokumentacja podaje regułę prefiksu `customer-`, nie cytuje tego hosta wprost (wywnioskowane z
reguły); strona pricing nie wymienia osobno hostów per API. Brak próby na żywo z kluczem
(brak klucza i egressu). Odpowiedzi WebFetch są streszczeniami modelu małego, nie surowym
HTML. Przed przełączeniem na produkcji: sprawdzić host w panelu klienta Open-Meteo i wykonać
jedno żądanie testowe. Ceny planów — poza zakresem, nie sprawdzane.

### 3. Klucz nigdy poza env (rule #3)

- **Provenance:** `source_fetches.endpoint` = `client.base_url()` + współrzędne centroidu, nigdy
  `apikey`.
- **Wyjątki:** `get_json()` składa komunikat przez `redact()` (`app/redact.py`: maskuje
  `apikey=<cokolwiek>` i literalny klucz z configu) i rzuca `from None` — oryginalny wyjątek httpx
  (URL z query, w tym klucz) nie zostaje w `__cause__`, więc nie wyjdzie w tracebacku
  `logger.exception`.
- **Logi httpx:** httpx loguje na INFO pełny URL każdego żądania (`HTTP Request: GET …?apikey=…`).
  `app/redact.py` instaluje na loggerze `httpx` filtr z `redact()`.
- **`last_error` / `/health/sources`:** `sanitize_error()` w `source_health.py` już usuwa query
  string i wszystko od słowa kluczowego `api key`/`apikey`/`token`…; dołożony test pokrywa
  `apikey=` (z `?` i bez). `source_status.last_error` dostaje komunikat już po `redact()`.
- **Testy/snapshoty:** testy używają sztucznego klucza i sprawdzają jego brak; klucz nie trafia do
  repo (`.env.example` ma pustą wartość).

- **Walidacja configu:** przy ustawionym kluczu oba base URL muszą być `https://` (inaczej
  `ValueError` przy starcie); pusty/whitespace w `OPEN_METEO_*_BASE_URL` = wartość domyślna;
  pusty klucz = brak klucza; klucz ma `repr=False`. Przy starcie schedulera/CLI jedno
  `logger.warning` (bez wartości klucza), gdy klucz jest ustawiony, a host nie zaczyna się od
  `customer-` — miękko, bo nazwa hosta Air Quality jest niezweryfikowana.
- **Limit dzienny:** `OPEN_METEO_DAILY_CALL_LIMIT` (domyślnie 10 000 = Free) — po przejściu na
  plan komercyjny podnieść w env, inaczej alert 70% i `check_daily_budget` liczą się od limitu Free.
- **Znane ograniczenie:** `params` z kluczem (`apikey`) jest zmienną lokalną w `get_json()`.
  Narzędzia typu Sentry z `include_local_variables` mogłyby ją dołączyć do zdarzenia — przy
  wdrożeniu TASK-13.2 wyłączyć `include_local_variables` lub dodać scrubbing `apikey`.
  Szczelność ścieżek (provenance, `last_error`, logi) pokrywa test integracyjny
  `test_open_meteo_key_leak_integration.py` (httpx `MockTransport`, oba connectory, sukces i porażka).
- **Retry:** odpowiedź 4xx poza 429 (np. zły klucz) nie jest ponawiana; `httpx.InvalidURL` jest
  opakowywany i maskowany jak inne błędy.

### 4. Gdzie leży szew wymiany providera (bez nowej warstwy abstrakcji)

Wystarcza config + istniejący kontrakt connectora (fetch / parse / validate / normalize).
Szew: katalog `connectors/<provider>/` + `source_id` w tabelach i odpowiedziach API. Mobile
czyta wyłącznie nasze `/api/v1/*` (rule #14; grep `apps/mobile`: jedyny `fetch` to
`app/api.ts` → `API_URL`, zero odwołań do Open-Meteo). `source: Literal["open_meteo"]` w
`WeatherArea`/`ForecastArea` zmieniono na `str` (pyłki już miały `source: str`), więc zamiana
providera nie łamie kontraktu klienta; provider-neutralne pola: `source`, `model`, `kind`.
Nie budujemy interfejsu „WeatherProvider” — YAGNI do czasu realnego drugiego providera.

### 5. Pyłki = prognoza modelowa, nie pomiar; miejsce na pomiar

Potwierdzone w kodzie: `PollenSnapshot` (osobna tabela od `measurements`, ADR-020) i API
`kind: "model_forecast"` + `model` + `forecast_reference_time`. Jeśli kiedyś pozyskamy
rzeczywiste pomiary pyłków z polskiego źródła (kandydat: OBAŚ — nic niezweryfikowane, patrz
registry `obas`), wejdą jako **osobny byt Measurement** z własnym `source_id` (rule #7), w
osobnym polu/bloku odpowiedzi API obok prognozy modelowej, bez nadpisywania jej; wymaga
Source Approval Gate (rule #15). **Nie implementujemy tego teraz.**

### 6. Google Pollen API — odrzucony na MVP

REJECTED-for-MVP. Polityki Pollen API (developers.google.com/maps/documentation/pollen/policies,
sprawdzone 2026-10-01): „Content pre-fetching, caching, or storage is generally prohibited, with
the exception of place IDs” — to koliduje z modelem snapshotów (ADR-001, rule #14: API czyta
tylko z naszej bazy). Dodatkowo wymóg atrybucji „Source: Includes pollen data from Google” i
mapy Google przy wizualizacji na mapie. Możliwy powrót jako źródło on-demand/premium — wymaga
osobnego ADR (rule #14 zabrania wołania zewnętrznego API na żądanie użytkownika).

### 7. Gate monetyzacji (uzupełnienie ADR-003)

Darmowy tier Open-Meteo jest wyłącznie niekomercyjny. Checklista „przed monetyzacją” (reklamy,
subskrypcje, Patronite, premium) jest w ADR-003; pierwszy punkt: plan komercyjny Open-Meteo
aktywny i skonfigurowany przez env (ten ADR, pkt 2).

**Uzupełnienie 2026-10-02 (ADR-031):** wg pisemnego potwierdzenia Open-Meteo darowizny/Patronite
są dozwolone na Free; plan komercyjny jest wymagany przed **reklamami** i **płatnymi/premium
funkcjami**. Bramka wydaniowa: `docs/release/business-gates.md`. Zmienne env bez zmian
(`OPEN_METEO_FORECAST_BASE_URL`, `OPEN_METEO_AIR_QUALITY_BASE_URL` — osobne, bo różne hosty — oraz
opcjonalny `OPEN_METEO_API_KEY`); kodu nie zmieniamy.

## Consequences

- Free → Paid to zmiana `.env` na VPS (+ jedno żądanie testowe), bez deployu kodu.
- Jeden mały moduł (`redact.py`) i jedna wspólna funkcja HTTP zamiast dwóch kopii pętli retry.
- `from None` kosztuje diagnostykę (brak łańcucha przyczyn) — komunikat zachowuje typ i treść
  błędu z maskowaniem; to świadomy kompromis na rzecz rule #3.
- Wymiana providera pogody nadal wymaga nowego connectora + mapowania pól (ADR-001), ale nie
  zmian w mobile ani w kontrakcie API.
- Ryzyko: ustawienie klucza przy domyślnym hoście Free wysyła klucz na host Free (parametr
  zostanie zignorowany lub odrzucony) — operator musi ustawić oba (hosty `customer-*` + klucz).
