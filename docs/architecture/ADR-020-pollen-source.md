# ADR-020: Źródło pyłków — CAMS Europe przez Open-Meteo Air Quality API

- **Date:** 2026-10-01
- **Status:** Accepted (shape odpowiedzi API: niezweryfikowany na żywo — patrz niżej)

## Context

Master Plan §6 (MVP) wymaga pyłków 5 gatunków: olcha, brzoza, trawy, bylica,
ambrozja. Plan i ADR-003 zakładały bezpośrednie CAMS/Copernicus ADS, co wymaga
rejestracji i klucza API od człowieka (TASK-8.5 był zablokowany). Polecenie
właściciela: przy braku dostępu zbadać wiarygodne źródła i zaimplementować.
ADR-001 (opcja C) wymaga snapshotu per gmina w naszej bazie; ADR-004 — fetch
zgodny ze zweryfikowanym cyklem źródła; ADR-014 — provenance; ADR-012 — stan
UNAVAILABLE.

## Problem

1. Czy jest źródło pokrywające **wszystkie 5** gatunków MVP bez klucza?
2. Jaka licencja/atrybucja, czy wolno użycie komercyjne (rule #15)?
3. Jak modelować dane, które są **prognozą modelową**, nie pomiarem (rule #7)?
4. Jak często fetchować (rule #16) i jak liczyć budżet wywołań?

## Options

1. **CAMS ADS bezpośrednio** (NetCDF/GRIB, klucz). Zostaje blokadą człowieka,
   nie da się tego zaimplementować ani zweryfikować bez klucza.
2. **Open-Meteo Air Quality API (`cams_europe`)** — ten sam model CAMS, JSON
   per punkt, bez klucza w tierze niekomercyjnym.
3. **Inny dostawca pyłków** (np. Google Pollen API, Ambee) — płatne/inne
   licencje, poza zakresem bez decyzji właściciela. **Google Pollen API:
   REJECTED-for-MVP** (2026-10-01, ADR-022 pkt 6): polityki zabraniają
   pre-fetchingu/cache'owania/storage odpowiedzi („generally prohibited”), co
   wyklucza snapshoty w bazie (ADR-001, rule #14). Powrót tylko jako źródło
   on-demand/premium — osobny ADR.

## Decision

Opcja 2, connector `open_meteo_pollen` (osobny katalog `app/connectors/
open_meteo_pollen/`, nie rozszerzenie `open_meteo`): inny host
(`air-quality-api.open-meteo.com`), inny zestaw zmiennych, inny cykl (24h vs 3h),
osobny `source_id` (provenance, retencja, `source_status`, freshness) —
wspólne rozszerzenie zmieszałoby dwa cykle w jednym jobie i jednym wierszu
`source_status`. Kontrakt fetch / parse / validate / normalize jak w pozostałych.

### Zweryfikowane u źródła (2026-10-01, dokumentacja; bez żywej próby)

- **Endpoint:** `https://air-quality-api.open-meteo.com/v1/air-quality`,
  parametry `hourly`, `domains` (`auto` | `cams_europe` | `cams_global`),
  `forecast_days` (0–7, domyślnie 5), `timezone` (domyślnie GMT), `timeformat`
  (domyślnie iso8601) — open-meteo.com/en/docs/air-quality-api.
- **Zmienne godzinowe:** `alder_pollen`, `birch_pollen`, `grass_pollen`,
  `mugwort_pollen`, `olive_pollen`, `ragweed_pollen`, jednostka
  **grains/m³**. Pokrywa 5 gatunków MVP (olcha=alder, brzoza=birch,
  trawy=grass, bylica=mugwort, ambrozja=ragweed). Oliwka poza MVP — nie pytamy.
- **Zasięg:** „Only available in Europe … as provided by CAMS European Air
  Quality forecast”, „during pollen season with 4 days forecast”. Pyłki są tylko
  w domenie `cams_europe` (0,1° ≈ 11 km, godzinowo; CAMS Global nie ma pyłków) —
  dlatego `domains=cams_europe` jest przypięte, nie `auto`.
- **Cykl:** Open-Meteo: „Every 24 hours, 4 days forecast”. ADS (CAMS Europe
  air quality forecasts): produkt raz dziennie, dostępny 06:45 UTC (lead 0–48 h)
  i 08:30 UTC (lead 49–96 h). **Fetch raz na dobę** (ADR-004, rule #16).
- **Licencja:** Open-Meteo: CC BY 4.0, darmowy tier wyłącznie niekomercyjny
  (subskrypcja/reklamy = komercyjne; Patronite nieopisane — jak w ADR-003).
  Dane CAMS: CC-BY (ADS). Atrybucja: „clear attribution to CAMS ENSEMBLE data
  provider … as well as a reference to Open-Meteo” + link do open-meteo.com.
  Komercyjnie: płatny plan z kluczem (`customer-api.open-meteo.com`); endpointy i
  klucz są konfiguracją (env), nie kodem — ADR-022.
- **Limity:** 600/min, 5000/h, 10000/dzień, 300000/mies.; pricing page wymienia
  Air Quality API w tym samym tierze.
- **Jakość:** ADS: prognozy poza NO/NO₂/SO₂/O₃/PM2.5/PM10/pył „are unvalidated
  and should be considered experimental” — dotyczy też pyłków.

### NIE zweryfikowane (oznaczone jako takie w kodzie i registry)

- Żywy przykład odpowiedzi: egress do `air-quality-api.open-meteo.com` jest
  zablokowany z tego środowiska, a WebFetch nie dostał zgody. Parser używa
  wyłącznie pól z dokumentacji (`hourly.time`, tablice per zmienna,
  `hourly_units`, `utc_offset_seconds`) i **odrzuca** wszystko inne (status
  `invalid`, payload zachowany w `source_fetches` do analizy).
- Dokładny napis jednostki w `hourly_units` (przechowujemy taki, jaki zwraca
  źródło; wymagamy, by pięć gatunków miało tę samą).
- Czy poza sezonem wartość to `null` czy `0` — dokumentacja mówi tylko „only
  available during pollen season”. Parser zachowuje oba wiernie (`null` → NULL,
  `0` → 0.0); nigdy nie zamienia braku na 0.
- Czy limit/„koszt” wywołania liczy się dla Air Quality API jak dla forecast
  (>10 zmiennych / >14 dni = więcej niż 1). Żądanie ma 5 zmiennych i 4 dni, więc
  przy tej regule = 1 jednostka; przyjęte założenie (`UNITS_PER_CALL = 1`).
- Czy limity są wspólne dla wszystkich API Open-Meteo: zakładamy, że tak
  (konserwatywnie) — wywołania pyłkowe liczą się w **tym samym** liczniku
  `open_meteo` (TASK-13.1a), więc alert 70% odzwierciedla łączne zużycie.
- Godzina faktycznego uruchomienia modelu (00 UTC?) — Open-Meteo jej nie zwraca.

### Walidacja payloadu (kontrakt parsera)

Payload jest odrzucany (`invalid`, surowy zapis zostaje w `source_fetches`), gdy: brak
`utc_offset_seconds` lub ≠ 0; `hourly.time` ma duplikaty, nie jest tekstem
`YYYY-MM-DDTHH:MM`, ma offset albo nie jest wyrównany do pełnej godziny; jednostki nie są
jednakowymi niepustymi stringami ≤ 20 znaków; wartość nie jest liczbą ≥ 0 (NaN/inf/
przepełnienie też); długości serii się nie zgadzają. **Świeżość samego payloadu:** seria
musi zawierać dokładnie godzinę z `fetched_at` (zaokrągloną w dół) — `current` jest serwowany tylko z tego slotu, a prawdziwa seria biegnie ciągle od 00:00 dziś na 4 dni (okno tolerancji „godzina wcześniej” odrzucone: zastąpiłoby poprzedni bucket i zostawiło `current = null` do następnego przebiegu). Bez tego payload w całości z
przeszłości trafiłby pod dzisiejszy `forecast_reference_time`, wygrał ze starszym dobrym
przebiegiem i nie dał żadnego `current`. Seria samych `null` (poza sezonem), która
godzinę obejmuje, jest poprawna. CLI z `--slug` nie zapisuje `source_status` (podzbiór nic nie mówi o całym źródle). Zapis (`_store_batch`) jest upsertem całego bucketu
(obszar + `forecast_reference_time`) z blokadą wierszy i strażnikiem `fetched_at` (starszy,
równoległy fetch nie nadpisuje nowszego), z jednym retry po wyścigu pierwszego inserta.

### Model danych: `PollenSnapshot` = modelowa prognoza, nie Measurement

- Tabela `pollen_snapshots` (ADR-001 opcja C): **osobna** od `measurements`
  (rule #7) i od `forecasts` (pogoda, dzienne, `param_code`/NOT NULL value).
  Jeden wiersz = gmina (`geo_area_id`) × godzina (`valid_at`) × przebieg
  prognozy (`forecast_reference_time`), z pięcioma gatunkami **jawnie jako
  kolumny** (`alder`, `birch`, `grass`, `mugwort`, `ragweed`, `Float NULL`).
  Wariant „wiersz per gatunek” dałby 5× więcej wierszy i umożliwiał niepełny
  zestaw gatunków; kolumny wymuszają kontrakt MVP na poziomie schematu.
- `model` (`cams_europe` — wartość parametru, który sami wysyłamy) i
  `forecast_reference_time` są obowiązkowe: to *prognoza* modelu, niezwalidowana
  przez dostawcę. `forecast_reference_time` = nasz `fetched_at` zaokrąglony w dół
  do doby UTC (Open-Meteo nie podaje czasu przebiegu — to ten sam dokumentowany
  kompromis co w ADR-010, nie zmyślona precyzja).
- **NULL ≠ 0.** NULL = model nie dał wartości (typowo poza sezonem); 0.0 = modelowe
  zero. API nigdy nie podstawia 0 za brak danych.
- `unit` jak w payloadzie; `source_fetch_id` FK do `source_fetches` (ADR-014);
  unikalność `(source_id, source_record_id)`, gdzie id =
  `geo_area:valid_at:forecast_reference_time` (re-ingest w tej samej dobie to
  UPSERT: nowsze wartości, `fetched_at` i `source_fetch_id` zastępują starsze, więc
  fetch po porannej aktualizacji CAMS poprawia wcześniejszy). Tabela append-only; przebiegi z kolejnych dni się nawarstwiają.
- **Rozkład pobierania:** jedno żądanie na `geo_area` (współrzędne centroidu
  gminy, nigdy użytkownika) — ADR-001. 4 dni × 24 h = 96 wierszy na obszar na dobę.
  `# ponytail:` retencja starych przebiegów `pollen_snapshots` (kasowanie wierszy
  starszych niż N dni) — dodać, gdy rozmiar tabeli zacznie przeszkadzać; dziś
  ok. 35 tys. wierszy/obszar/rok.
- **Provenance (ADR-014):** surowy payload zapisany przed parsowaniem
  (`pending`), potem `valid`/`invalid`; `PARSER_VERSION = "1"`; endpoint =
  URL + współrzędne centroidu (brak danych wrażliwych). Retencja payloadu:
  **7 dni** (prognoza modelowa do ponownego pobrania, mały payload).

### Endpoint i świeżość

- `GET /api/v1/pollen/latest`: typowany `response_model`, per `geo_area`:
  `kind: "model_forecast"`, `model`, `unit`, `forecast_reference_time`,
  `fetched_at`, `freshness`, `valid_at` + `current` (godzina „teraz”, 5 gatunków,
  każdy `float | null`) oraz `days` (maksimum dobowe UTC per gatunek, `null` gdy
  cała doba bez wartości). Top-level: `source`, `attribution` (dosłownie z
  registry — test to sprawdza) i `source_status` (ADR-012). Czyta wyłącznie z
  bazy (rule #14).
- **Freshness** liczona z `fetched_at` (nie z `valid_at`, który jest z natury w
  przyszłości): FRESH ≤ 32 h, RECENT ≤ 64 h, STALE dalej — te same proporcje
  (~1,3× / ~2,7× cyklu) co pogoda (4 h / 8 h przy cyklu 3 h). Brak wierszy lub
  brak udanego przebiegu → `areas: []` + `source_status: UNAVAILABLE`. Gdy
  zapisany przebieg nie pokrywa bieżącej godziny (scheduler stoi > ~4 dni):
  `current: null`, `freshness: STALE`.
- **Scheduler:** job `open_meteo_pollen` co 24 h, na tych samych obszarach co pogoda
  (`polling_areas`, flaga `weather_polling_active` z ADR-019 — nigdy cała lista
  zaimportowanych gmin), `_run_job_safely`, wpis w
  `source_status`. `ingest_areas` rzuca wyjątek przy TOTALNEJ awarii (żadna
  gmina nie dała poprawnego payloadu), więc `last_success_at` nie kłamie (ADR-012);
  brak `geo_areas` = job pominięty (nie sukces). Awaria części gmin jest tylko
  logowana (rule #1), a per-area `fetched_at` pokazuje, która jest przeterminowana.
  Ograniczenie: pętla schedulera liczy interwał od startu procesu, nie od
  06:45–08:30 UTC, więc przebieg z wczesnej godziny może zawierać jeszcze dane
  z poprzedniego runu modelu. `# ponytail:` ustawić godzinę okna (np. 09:00 UTC),
  jeśli okaże się to problemem na produkcji.

## Consequences

- Pyłki MVP (5 gatunków) działają bez klucza i bez człowieka w pętli.
- **ADR-003 zostaje zaktualizowany:** pyłki nie są już niezależne od statusu
  komercyjnego Open-Meteo — ta ścieżka podlega tym samym warunkom (darmowy tier
  = wyłącznie niekomercyjnie, rewizja przed Patronite/reklamami/subskrypcją).
  Przy rewizji opcją pozostaje CAMS ADS bezpośrednio (CC-BY, bez rozróżnienia
  komercyjne/niekomercyjne) — wymaga klucza (blokada człowieka).
- Dane są modelową, „eksperymentalną” prognozą; UI (TASK-8.8) musi to pokazać
  i podać atrybucję CAMS + Open-Meteo.
- Kształt JSON do potwierdzenia przy pierwszym realnym uruchomieniu
  (`python -m app.connectors.open_meteo_pollen.ingest`): ewentualna różnica
  zostanie zatrzymana przez parser (`invalid`), a payload czeka w
  `source_fetches` — bump `PARSER_VERSION` po korekcie.
- Wspólny licznik `open_meteo` podnosi szybciej alert 70% (konserwatywnie).
- Nie dotyczy: karta mobile (TASK-8.8), agregat `dashboard_latest()` (TASK-8.9),
  profil alergika (TASK-12.4).


## Addendum 2026-10-01: dashboard i karta mobile (TASK-8.8/8.9)

- **Kontrakt `/dashboard/latest`:** każdy obszar ma blok `pollen` = pola jednego obszaru
  z `/pollen/latest` (`kind: "model_forecast"`, `model`, `unit`, `forecast_reference_time`,
  `fetched_at`, `freshness`, `valid_at`, `current`, `days`) + `source`, `attribution`
  (dosłownie jak wyżej) + `source_status` (ADR-012). Brak snapshotu dla obszaru:
  `freshness: "UNAVAILABLE"`, wartości `null`, `days: []` (nigdy 0). Czyta tylko z bazy
  (rule #14). Blok liczony na końcu i izolowany: wyjątek → wszystkie bloki `pollen` są
  `UNAVAILABLE`, reszta dashboardu działa (rule #1).
- **Mobile:** efektywna świeżość = gorsza z `freshness` obszaru i `source_status`. STALE/
  UNAVAILABLE nie pokazują poziomów (rule #8), null = „brak danych”. Karta zawsze nazywa dane
  „prognozą modelu CAMS (nie pomiar)” i pokazuje atrybucję.
- **Progi (zweryfikowane 2026-10-01):** EEA Climate-ADAPT, „CAMS pollen viewer”
  (climate-adapt.eea.europa.eu/…/cams-ground-level-pollen-forecast/cams-pollen-viewer):
  „For alder, birch, olive and mugwort, concentrations ≥ 10 pollen/m3 demarcate the pollen
  season and concentrations ≥ 100 pollen/m3 demarcate the peak pollen period (Pfaar et al.,
  2017). For grass and ragweed, ≥ 3 … season and ≥ 50 … peak (Pfaar et al., 2017, 2020)” —
  progi EAACI. To **granice sezonu i szczytu pylenia, nie klasy ryzyka objawów** — UI mówi:
  „poniżej progu sezonu / sezon pylenia / szczyt pylenia”, nie „niskie/wysokie”. Open-Meteo
  nie podaje własnych progów (sprawdzone na stronie docs). NIEZWERYFIKOWANE: że „pollen/m³”
  w źródle EEA = `grains/m³` Open-Meteo (przyjęte jako ta sama jednostka; progi stosowane
  wyłącznie przy jednostce dokładnie `grains/m³`, inaczej surowa wartość bez poziomu).
- **Poza zakresem:** `outdoor.evaluate` (ADR-016) bez pyłków — dodanie reguł wymaga ADR.
