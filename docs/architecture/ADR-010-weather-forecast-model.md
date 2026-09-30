# ADR-010: Model Forecast — prognoza pogody Open-Meteo (§30)

**Status:** Accepted
**Data:** 2026-09-29

## Context

Master Plan §30 wymaga osobnego modelu `Forecast`, wyraźnie odróżnionego od
`Measurement` (rule #7): "Measurement i Forecast nie mogą być mylone". Do tej
pory connector `open_meteo` pobierał wyłącznie `current` (ADR-001,
`WeatherSnapshot`) — ROADMAP.md §2.2 miał to jako TODO ("prognoza, nie tylko
current").

Open-Meteo API pozwala dołączyć `daily=...` do TEGO SAMEGO zapytania co
`current=...` — jedno wywołanie HTTP zwraca oba bloki (`current`+`current_units`
oraz `daily`+`daily_units`). Kształt `daily` jest inny niż `current`: nie
pojedynczy odczyt, tylko równoległe tablice (`time: [...]`, `temperature_2m_max:
[...]`, ...) — jeden wpis per dzień. Potwierdzone przez dokumentację
(open-meteo.com/en/docs — API bezpośrednio zablokowane przez robots.txt w tym
środowisku, ten sam ograniczenie co przy pierwszej implementacji `current`,
udokumentowane w `client.py`/source-registry.md; weather nie jest danymi
bezpieczeństwa, więc weryfikacja z oficjalnej dokumentacji tekstowej jest
przyjętym precedensem, inaczej niż przy IMGW alertach).

## Problem

1. Open-Meteo nie zwraca w odpowiedzi API znacznika czasu "kiedy uruchomiono
   ten model" (`forecast_reference_time` z §30) — nie ma czegoś takiego w
   udokumentowanym kształcie odpowiedzi.
2. Bez stabilnego, pochodzącego ze źródła znacznika czasu dla "run" modelu,
   naiwne użycie `datetime.now()` jako `forecast_reference_time` łamie
   idempotencję (rule #40): dwa uruchomienia ingestu w tym samym cyklu 3h
   (ADR-004) dostałyby różne `forecast_reference_time` → różne
   `source_record_id` → duplikaty.
3. Czy prognoza powinna być append-only (zachowywać historię tego, jak
   prognoza się zmieniała w miarę zbliżania się terminu) czy upsert/delete
   (jak progi ostrzegawcze w TASK-9.3)?

## Decision

- Nowa tabela `forecasts`, osobna od `weather_snapshots` (rule #7). Pola:
  `geo_area_id`, `param_code`, `value`, `unit` (jak `WeatherSnapshot`) plus
  `model`, `forecast_reference_time`, `valid_from`, `valid_until` (§30).
- **`forecast_reference_time` = nasz własny `fetched_at` zaokrąglony w dół do
  3-godzinnego okna (ten sam cykl co ADR-004/scheduler)**, nie surowy znacznik
  fetchu. To uczciwie udokumentowane przybliżenie (nie zgadywanie — źródło
  faktycznie nie publikuje własnego znacznika "run modelu"), a zaokrąglenie do
  realnego cyklu fetchowania rozwiązuje punkt 2: dwa fetche w tym samym oknie
  3h dostają identyczny `forecast_reference_time`, więc identyczny
  `source_record_id` → naturalny dedup, bez dodatkowej logiki.
- **`model = "auto"`** — dokładna, udokumentowana wartość domyślna Open-Meteo,
  gdy parametr `models` nie jest podany (nie wymyślona nazwa).
- **Append-only** (jak `Measurement`/`WeatherSnapshot`), NIE upsert/delete jak
  progi w TASK-9.3. Różnica: próg wodowskazu to referencyjna wartość bez
  wartości w historii ("jaki jest próg TERAZ"); prognoza ma wartość w historii
  ("jak prognoza na czwartek zmieniała się w miarę zbliżania się czwartku") —
  to jest dokładnie dana, którą §33 (raw provenance) każe zachowywać, nie
  nadpisywać. Endpoint odczytu bierze NAJNOWSZY `forecast_reference_time` per
  (geo_area, dzień, param) — najświeższa dostępna prognoza na dany dzień.
- `source_record_id = f"{geo_area_id}:{param_code}:{valid_from.isoformat()}:
  {forecast_reference_time.isoformat()}"`.
- Jedno zapytanie HTTP (`current`+`daily` razem) — nie dwa osobne connectory
  ani dwa wywołania API per geo_area (rule #5 nie wymaga, a marnowałoby to
  rate limit bez potrzeby). `client.fetch_current()` przemianowany na
  `client.fetch_weather()` — stara nazwa byłaby myląca po tej zmianie.
- Zakres dzienny (`daily`) ograniczony do MVP: `temperature_2m_max`,
  `temperature_2m_min`, `precipitation_sum`, `weather_code` — nie pełen zestaw
  dostępnych w Open-Meteo pól dziennych (YAGNI, rozszerzyć gdy realnie
  potrzebne, ten sam wzorzec co `CURRENT_PARAMS`).
- Izolacja awarii (rule #1, wzorzec z TASK-9.3): parsowanie `current` i
  `daily` są niezależne (osobne `try/except`) — błąd w jednym bloku odpowiedzi
  nie blokuje zapisania drugiego, jeśli ten jest poprawny.

## Non-goals

- Godzinowa (`hourly`) prognoza — tylko dzienna na start (§30 nie precyzuje
  granularności, dzienna wystarcza dla MVP dashboardu).
- Wykorzystanie historii prognoz (jak prognoza się zmieniała) w UI — dane są
  zachowywane (append-only), ale na razie nic ich nie czyta poza "najświeższa
  prognoza".
- Zmiana cyklu fetchowania (`OPEN_METEO_INTERVAL_SECONDS`, ADR-004) — bez
  zmian, forecast korzysta z tego samego uruchomienia co current.

## Consequences

- `forecasts` rośnie szybciej niż `weather_snapshots` per geo_area (4 pola ×
  7 dni × liczba fetchy dziennie, nie 1 dzień) — akceptowalne przy obecnej
  skali (7 zaseedowanych lokalizacji), do rewizji gdy realnie urośnie liczba
  lokalizacji (podobna logika co decyzja o braku Redis/workerów).
- `GET /api/v1/weather/forecast` musi jawnie wybrać "najnowszy
  `forecast_reference_time` per dzień" — nie może po prostu wziąć "wszystkich
  wierszy", bo zwróciłby duplikaty z różnych przebiegów ingestu.
