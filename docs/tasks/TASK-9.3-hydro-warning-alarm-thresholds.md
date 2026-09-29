# TASK 9.3 — Progi ostrzegawcze/alarmowe stanu wody

## Goal

Rozszerzyć connector `imgw_hydro` o oficjalnie publikowane przez IMGW progi
`stan_ostrzegawczy`/`stan_alarmowy` per stacja i wystawić deterministyczny
status `NORMAL`/`WARNING`/`ALARM`/`UNKNOWN` w `GET /api/v1/hydro/latest`.
To **nie jest** Alert Engine ani oficjalne ostrzeżenie IMGW (to już
`imgw_warningshydro`/ADR-009) — to prosta klasyfikacja liczbowa jednej
Measurement wobec dwóch innych, opublikowanych przez to samo źródło.

## Scope

- `imgw_hydro/parser.py`: `normalize()` zwraca teraz listę 1-3 rekordów
  Measurement (wzorzec jak w `open_meteo/parser.py`) — `water_level_cm` zawsze,
  plus `water_level_warning_cm`/`water_level_alarm_cm` gdy próg zdefiniowany
  (`stan_ostrzegawczy`/`stan_alarmowy` nie są `null`).
- `imgw_hydro/ingest.py`: `ingest_station()` zwraca liczbę zapisanych rekordów
  (0-3) zamiast `bool`, iteruje po liście z `normalize()`.
- `GET /api/v1/hydro/latest`: dodatkowe pola `warning_level_cm`,
  `alarm_level_cm`, `status`. `compute_status()` — czysta funkcja, porównanie
  liczbowe, brak LLM/zgadywania (rule #10).
- `docs/data/source-registry.md`: udokumentowane pola progów (zweryfikowane
  na żywo, w tym przypadek `null` dla stacji bez progu, np. jeziora).

## Acceptance Criteria

- [x] `normalize()` emituje osobny rekord per próg, gdy zdefiniowany (test:
      `test_normalize_includes_warning_and_alarm_thresholds_when_defined`).
- [x] `normalize()` pomija próg, gdy `null` — bez błędu (test:
      `test_normalize_omits_thresholds_when_null`).
- [x] `normalize()` rzuca `ImgwHydroParseError` na niepoprawną wartość progu
      (test: `test_normalize_raises_on_malformed_threshold`).
- [x] `source_record_id` unikalny per (stacja, param_code, obserwacja) — trzy
      rekordy z tego samego fetchu nie kolidują (test w
      `test_normalize_includes_warning_and_alarm_thresholds_when_defined`).
- [x] `ingest_station()` zapisuje 0-3 rekordy, zlicza poprawnie (testy:
      `test_ingest_station_stores_thresholds_too` i istniejące, zaktualizowane
      z `bool` na `int`).
- [x] `/hydro/latest` zwraca `status: UNKNOWN` dla stacji bez progów — nie
      `NORMAL` (test: `test_latest_hydro_shapes_response_from_rows`).
- [x] `/hydro/latest` liczy `NORMAL`/`WARNING`/`ALARM` poprawnie względem progu
      (testy: `test_compute_status_*`, `test_latest_hydro_includes_thresholds_and_status`).
- [x] Stacja z samymi progami (bez aktualnego `stan_wody`) nie pojawia się w
      odpowiedzi — zachowanie sprzed tej zmiany bez regresji (test:
      `test_latest_hydro_ignores_threshold_only_station`).

## Tests

`apps/api/tests/connectors/test_imgw_hydro_{parser,ingest}.py`,
`apps/api/tests/test_hydro.py`.

## Non-goals

- Alert Engine / powiadomienia na podstawie przekroczenia progu — to
  osobna decyzja (§47/§50 Master Planu), nie ta zmiana.
- Zmiana `imgw_warningshydro`/ADR-009 (oficjalne ostrzeżenia) — inny model,
  inny connector, bez zmian.
- Migracja bazy — reużywa istniejącej generycznej tabeli `measurements`.

## Dependencies

Brak nowej migracji, brak nowego ADR (reużycie istniejącego wzorca
multi-record `normalize()` z `open_meteo`, istniejący model `Measurement`).

## Data Contract

`GET /api/v1/hydro/latest` → stacja: `{..., water_level_cm, warning_level_cm,
alarm_level_cm, status: "NORMAL"|"WARNING"|"ALARM"|"UNKNOWN", ...}`.
`warning_level_cm`/`alarm_level_cm` mogą być `null` (brak progu dla stacji).

## Security

Brak zmian — te same dane z tego samego już-zaufanego publicznego endpointu.

## Architecture Impact

Brak — reużycie istniejącego wzorca (`normalize()` zwracające listę, jak w
`open_meteo`) i istniejącego modelu `Measurement`.
