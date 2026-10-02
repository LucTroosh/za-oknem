# ADR-030: Prognoza godzinowa na 48 h w tabeli `forecasts` (granularity), polityka retencji

**Status:** Accepted
**Data:** 2026-10-02

## Context

ADR-010 wprowadził `Forecast` wyłącznie jako prognozę **dzienną** (4 pola `daily`) i wprost
odłożył `hourly` (non-goal). Dziś jedyne wartości „co będzie za chwilę” to dzienne max/min.
Silnik „Na dwór” (ADR-016) ocenia tylko stan **teraz**; „najlepsze okno” na wysiłek (TASK-7.10)
wymaga godzinowej pogody na najbliższe 24–48 h. Open-Meteo zwraca `hourly` w tym samym
żądaniu co `current`/`daily`, a nasze żądanie już ma `hourly` (dew_point_2m, visibility,
uv_index — TASK-5.4, tylko dla godziny `current`).

## Problem

1. Gdzie i jak zapisać prognozę godzinową tak, by **nie mieszała się** z dzienną (reguła #7:
   Forecast ≠ Measurement; i prognoza godzinowa ≠ dzienna)? `weather_code` występuje w obu
   zestawach; wiersz dzienny i godzinowy dla 00:00 miałyby ten sam `(param, valid_from)` oraz —
   przy dotychczasowym wzorcu — ten sam `source_record_id` (unikalny klucz → godzinowy wiersz
   zostałby po cichu pominięty jako „już istnieje”).
2. Retencja: ADR-010 jest append-only (historia zmian prognozy). Godzinowo to ~9 parametrów ×
   48 h = ~430 wierszy na fetch (co 3 h), czyli ~3,5 tys. wierszy/dobę/obszar; przy aktywnych
   miejscowościach (ADR-029, do ~280 obszarów) ~1 mln wierszy/dobę — bez polityki tabela
   rośnie bez końca.
3. Budżet Open-Meteo (ADR-003/022): ile jednostek kosztuje rozszerzone żądanie?
4. Odporność (reguła #1): Open-Meteo bywa, że nie podaje części zmiennych (np.
   `precipitation_probability` jest często `null`), a pojedyncza godzina może mieć `null`.

## Options

- **Rozróżnienie granularności:** (a) kolumna `forecasts.granularity` (`daily`|`hourly`),
  migracja; (b) konwencja `param_code` (`weather_code_hourly`) bez migracji — nazwa jako
  ukryty dyskryminator, filtry po przedziale `valid_until − valid_from`; (c) osobna tabela
  `forecast_hours` — duplikacja modelu, drugi zestaw zapytań.
- **Retencja:** (a) append-only jak dzienna; (b) **tylko ostatni `forecast_reference_time`
  per obszar** + czyszczenie wierszy wygasłych; (c) TTL globalny po `fetched_at`.
- **Zakres czasowy w żądaniu:** (a) `forecast_hours=48`; (b) `forecast_days=7` jawnie + cięcie
  okna w parserze.

## Decision

1. **Kolumna `granularity` (migracja Alembic `0015`, NOT NULL, `server_default 'daily'`,
   indeks).** Istniejące wiersze są dzienne, więc default wypełnia je poprawnie. Kolumna zamiast
   konwencji nazw: dyskryminator jawny, w kluczu `DISTINCT ON` czytania i w usuwaniu; nie
   zakładamy nic o `param_code`. Migracja jest *konieczna* (punkt 1: kolizja
   `source_record_id`/`valid_from` dla `weather_code`).
2. **Żądanie (bez nowego round-tripu):** `hourly` = suma zbiorów (każda zmienna raz):
   dotychczasowe `dew_point_2m, visibility, uv_index` + `temperature_2m, apparent_temperature,
   precipitation, precipitation_probability, wind_speed_10m, wind_gusts_10m, weather_code`
   (`visibility` i `uv_index` są już w żądaniu, więc **widoczność wchodzi bez kosztu**; mgła
   i burza to wejścia silnika/okna). `daily` +`precipitation_probability_max`, `uv_index_max`.
   **`forecast_days=7` jawnie** (to dotychczasowa wartość domyślna Open-Meteo — dzienna
   prognoza zostaje 7-dniowa; sama zmiana niczego nie zmienia, ale przestaje być niejawna).
   **`forecast_hours` celowo NIE jest ustawione**: według dokumentacji liczy od bieżącej godziny
   (a nie od początku doby) — przy przesunięciu zegara serwera względem `current.time` mogłoby
   zgubić slot bieżącej godziny, którego szuka `normalize_hourly_current` (TASK-5.4: UV/widoczność).
   Okno 48 h tnie parser: od godziny `current` (`HOURLY_FORECAST_HOURS`); wcześniejsze godziny
   dzisiejszej doby odpadają (nie są prognozą). Koszt: większy surowy payload (7 dni × ~10
   serii) w `source_fetches` — mieści się w retencji ADR-014.
3. **Parser odporny (#1):** blok godzinowy jest czwartym, izolowanym blokiem ingestu (obok
   current / hourly-current / daily). Ścisła jest tylko *kształt* (`hourly`, `hourly_units`,
   `time` jako lista). Brak serii, brak jednostki, długość inna niż `time`, `null`/NaN/bool/tekst
   w godzinie, nieparsowalny czas → ginie **ta jedna wartość** (lub ten parametr), nigdy cała
   reszta; brak wartości = brak klucza w `params` godziny, nigdy 0. Zero użytecznych wartości w
   oknie → `OpenMeteoParseError` (pusty blok to porażka bloku w provenance/`source_status`, nie
   cichy sukces). Dziennie: 4 pola rdzeniowe ścisłe jak w ADR-010; nowe 2 **opcjonalne** (pomijane
   przy braku). `PARSER_VERSION` = 2.
4. **Model danych godziny:** wiersz `Forecast` z `granularity='hourly'`, `valid_from` = początek
   godziny (UTC), `valid_until` = +1 h, `model='auto'`, `forecast_reference_time` = fetch w koszu
   3 h (jak ADR-010). `source_record_id = hourly:{area}:{param}:{valid_from}:{ref}` — prefiks
   gwarantuje rozłączność z id dziennymi.
5. **Retencja godzinowa: tylko najnowszy przebieg per obszar, ale degradacja go nie niszczy.**
   Nowy przebieg zastępuje poprzedni (delete + insert + commit w jednej transakcji, jeden
   `try`, `IntegrityError` jest połykany i wycofywany — nie ucieka z `ingest_geo_area`, #1).
   Zasady: (a) **ten sam `forecast_reference_time` nadpisuje cały przebieg** (nie pomija znanych
   id — `fetched_at` i wartości muszą być świeże); (b) **przebieg zdegradowany** — pokrywa
   < połowy slotów poprzedniego (w oknie nowego) albo gubi któryś jego parametr — **nie kasuje
   poprzedniego**: zostaje stary (uczciwie starzeje się do STALE), log ostrzega; wyjątek: gdy
   poprzedni ma > 6 h (`HOURLY_BASELINE_MAX_AGE`), zastępujemy go nawet słabszym; (c)
   przebieg starszy niż zapisany nic nie zapisuje. Historia zmian prognozy godzinowej **nie
   jest** zachowywana (dzienna zostaje append-only, ADR-010) — nikt jej nie potrzebuje, a koszt
   jest ~100× większy. Dobowa konserwacja (`run_raw_retention`, kroki w osobnych `try`)
   usuwa wiersze godzinowe, których godzina skończyła się > 1 dobę temu (wygasłe miejscowości
   ADR-029 trzymałyby inaczej ostatni przebieg wiecznie). Schemat: `CHECK granularity IN
   ('daily','hourly')` i indeks `(granularity, valid_until)` pod to czyszczenie.
6. **API:** `dashboard_latest()` → `areas[].forecast.hours[]` (`valid_from`, `valid_until`,
   `params{value,unit}`), **osobna lista od `days`**, nigdy mieszana. Czytanie
   (`forecasts_by_area(hourly=True)`) bierze najświeższy przebieg per (obszar, granularity,
   okres, parametr), a `days`/`hours` grupuje rozłącznie po `granularity`. `/weather/forecast`
   zostaje dzienny (bez `hours`). Świeżość: `forecast.freshness`/`fetched_at` = **starsza** z
   (najnowszy fetch `days`, najnowszy fetch `hours`) — gdy jedna z części przestaje się
   odświeżać, blok nie wygląda na świeższy niż jego starsza część (reguła #8). Status źródła
   dla UI = `source_status.weather` (ADR-012), bez nowego pola. Puste `hours` = brak/zły parse
   bloku godzinowego, nie „brak prognozy”.
7. **Budżet jednostek (ADR-003/022): ZMIENIA SIĘ.** Estymata to dotychczasowy wzór
   `ceil(zmienne / 10)` liczony z unii żądanych zmiennych (zawyżony: zmienna w `current` i
   `hourly` liczy się dwa razy). Było 12 + 3 + 4 = 19 → **2 jednostki**; jest 12 + 10 + 6 = 28
   → **3 jednostki** (+50% na wywołanie). Konsekwencje liczbowe (limit 10 000/dobę, 8 fetchy/dobę
   na obszar): 7 obszarów seed = 168 jedn./dobę (było 112); **`max_active_areas()` (ADR-029)
   spada z floor(7000/17) = 411 do floor(7000/25) = 280** (8·3 + 1 pyłki). Wzór `8·units + 1`
   w kodzie i testach nie wymaga zmiany (czyta stałą). Alternatywy odrzucone: obcięcie
   istniejących zmiennych (TASK-5.4 ich potrzebuje), dwa osobne żądania (więcej round-tripów,
   te same jednostki). Reguła „>10 zmiennych = wiele wywołań” jest zweryfikowana (komentarz w
   `ingest.py`, cennik 2026-09-29); niezweryfikowane jest, czy zmienna obecna w `current` i
   `hourly` liczy się raz czy dwa razy oraz czy liczba dni (7 ≤ 14) coś waży — zostajemy przy
   zawyżonej estymacie (alert wcześniej, nie później — jak w ADR-003).

## Non-goals

- UI okna aktywności i **silnik okna** (warstwa nad `evaluate()`) — TASK-7.9/7.10.
- Godzinowa jakość powietrza (CAMS/Open-Meteo Air Quality) — TASK-7.11; do tego czasu okno
  nie może twierdzić „dobre powietrze o 17:00”.
- Strefa Europe/Warsaw (żądanie nadal `timezone=UTC`); `hours` są godzinami UTC.
- Mobile UI prognozy godzinowej (tylko typy kontraktu).
- Weryfikacja na żywo: dostępność `precipitation_probability` dla domyślnego modelu w Polsce
  niezweryfikowana (egress zablokowany) — dlatego parser jest tolerancyjny.

## Consequences

- `forecasts` dostaje kolumnę i indeks (migracja `0015`, szybka: `ADD COLUMN` z defaultem
  stałym); wierszy godzinowych jest na stałe ~430 na aktywny obszar.
- Kod czytający `Forecast` musi rozróżniać `granularity` (dziś: `forecasts_by_area`).
- Limit aktywnych miejscowości spada do 280 (ADR-029 zaktualizowany notą).
- **Wspólna świeżość `days`/`hours`:** blok `forecast` ma jedno `freshness`/`fetched_at` = starsza
  część. Konsekwencja: zablokowany/zdegradowany przebieg godzinowy (zachowany stary) albo
  nieodświeżany dzienny sprawia, że cały blok, także druga część, wygląda na starszy niż jest.
  To świadomie zachowawcze (#8); osobne pola per część dopiero gdy UI tego potrzebuje.
- Rozszerzenie okna (np. 72 h) = zmiana `HOURLY_FORECAST_HOURS` + test; retencja bez zmian.
