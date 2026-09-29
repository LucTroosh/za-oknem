# TASK 9.3 — Progi ostrzegawcze/alarmowe stanu wody

## Goal

Rozszerzyć connector `imgw_hydro` o oficjalnie publikowane przez IMGW progi
`stan_ostrzegawczy`/`stan_alarmowy` per stacja i wystawić deterministyczny
status `NORMAL`/`WARNING`/`ALARM`/`UNKNOWN` w `GET /api/v1/hydro/latest`.
To **nie jest** Alert Engine ani oficjalne ostrzeżenie IMGW (to już
`imgw_warningshydro`/ADR-009) — to prosta klasyfikacja liczbowa jednej
Measurement wobec dwóch innych, opublikowanych przez to samo źródło.

## Scope

- `imgw_hydro/parser.py`: `normalize()` zwraca teraz
  `{"level": <rekord append-only>, "thresholds": {param_code: <rekord upsert
  lub {"value": None} do usunięcia>}}` zamiast pojedynczego dicta. Woda
  (`stan_wody`) to prawdziwy szereg czasowy (nowy `observed_at` przy każdym
  realnym odczycie) — próg nie ma własnego znacznika czasu ze źródła i może się
  zmienić/zniknąć niezależnie od cyklu odczytu wodowskazu, więc progi mają
  stabilną tożsamość (`stacja:param_code`, bez timestampu) i własny zegar
  (nasz `fetched_at`, nie `stan_wody_data_pomiaru`).
- `imgw_hydro/ingest.py`: `_insert_if_new()` (bez zmian semantycznie —
  append-only dla wody) + nowy `_upsert_or_delete_threshold()` — każdy przebieg
  ingestu nadpisuje JEDEN wiersz per (stacja, param_code) aktualną wartością
  albo go usuwa, gdy próg wraca jako `null`.
- `GET /api/v1/hydro/latest`: dodatkowe pola `warning_level_cm`,
  `alarm_level_cm`, `status`. `compute_status()` — czysta funkcja, porównanie
  liczbowe, brak LLM/zgadywania (rule #10). Endpoint ufa temu, co jest w bazie
  — reconciliation dzieje się przy ingest, nie przy odczycie.
- `docs/data/source-registry.md`: udokumentowane pola progów (zweryfikowane
  na żywo, w tym przypadek `null` dla stacji bez progu, np. jeziora).

## Historia przeglądu (Codex, PR #42 — 3 rundy)

1. **P1:** `water_level_warning_cm` (22 znaki) przekraczał `VARCHAR(20)`
   kolumny `param_code` — PostgreSQL odrzuciłby każdy rekord progu ostrzegawczego
   (SQLite tego nie egzekwuje, testy by tego nie złapały). → zmieniono na
   `water_level_warn_cm` (19 znaków) + test wprost sprawdzający limit.
2. **P2:** pierwsza wersja pomijała próg przy `null` bez żadnego śladu — stary
   wiersz zostawałby "najnowszym" na zawsze. → dodano wymóg dopasowania do
   `observed_at` bieżącego odczytu wody.
3. **P2 (runda 3):** dopasowanie po `observed_at` samo było wadliwe — stacja,
   która przestaje raportować nowy `stan_wody` (ten sam `observed_at` w kółko),
   mogłaby mieć zmieniony/wycofany próg, a endpoint i tak pokazywałby stary,
   bo timestampy się zgadzały. **Root cause:** wiązanie ważności progu z
   cyklem odczytu wodowskazu było błędnym modelem od początku. → przeprojektowano
   na upsert/delete względem własnego cyklu ingestu (ten sam duch co
   `_expire_withdrawn()` w `imgw_warningshydro`/ADR-009), niezależnie od
   `stan_wody_data_pomiaru`.

## Acceptance Criteria

- [x] `normalize()` zwraca próg jako osobny rekord ze stabilnym
      `source_record_id` (`stacja:param_code`, bez timestampu) (test:
      `test_normalize_includes_thresholds_when_defined`).
- [x] Rekord progu używa `fetched_at`, nie `stan_wody_data_pomiaru`, jako
      `observed_at` (test:
      `test_normalize_thresholds_use_fetched_at_not_stan_wody_timestamp`).
- [x] `normalize()` zwraca `{"value": None}` dla progu `null` — sygnał do
      usunięcia, nie błąd (test: `test_normalize_marks_threshold_for_deletion_when_null`).
- [x] `normalize()` rzuca `ImgwHydroParseError` na niepoprawną wartość progu
      (test: `test_normalize_raises_on_malformed_threshold`).
- [x] Każdy `param_code` mieści się w `VARCHAR(20)` (test:
      `test_param_codes_fit_the_varchar20_column`).
- [x] Zmiana progu bez nowego odczytu wody aktualizuje wartość (test:
      `test_ingest_station_updates_threshold_even_without_a_new_water_reading`).
- [x] Wycofanie progu (→ `null`) usuwa zapisany wiersz (test:
      `test_ingest_station_deletes_threshold_when_withdrawn`).
- [x] `/hydro/latest` zwraca `status: UNKNOWN` dla stacji bez progów (test:
      `test_latest_hydro_shapes_response_from_rows`).
- [x] `/hydro/latest` liczy `NORMAL`/`WARNING`/`ALARM` poprawnie (testy:
      `test_compute_status_*`, `test_latest_hydro_includes_thresholds_and_status`).
- [x] Próg starszy niż odczyt wody (inny `observed_at`) nadal jest używany —
      to nie jest staleness, tylko inny zegar (test:
      `test_latest_hydro_uses_threshold_even_when_older_than_the_reading`).
- [x] Stacja z samymi progami (bez aktualnego `stan_wody`) nie pojawia się w
      odpowiedzi (test: `test_latest_hydro_ignores_threshold_only_station`).

## Tests

`apps/api/tests/connectors/test_imgw_hydro_{parser,ingest}.py`,
`apps/api/tests/test_hydro.py`.

## Non-goals

- Alert Engine / powiadomienia na podstawie przekroczenia progu — to
  osobna decyzja (§47/§50 Master Planu), nie ta zmiana.
- Zmiana `imgw_warningshydro`/ADR-009 (oficjalne ostrzeżenia) — inny model,
  inny connector, bez zmian.
- Migracja bazy — reużywa istniejącej generycznej tabeli `measurements`
  (usuwanie wierszy progów mieści się w istniejącym modelu, bez nowej kolumny).

## Dependencies

Brak nowej migracji, brak nowego ADR (reużycie istniejącego modelu
`Measurement` i wzorca reconciliation już sprawdzonego w `imgw_warningshydro`).

## Data Contract

`GET /api/v1/hydro/latest` → stacja: `{..., water_level_cm, warning_level_cm,
alarm_level_cm, status: "NORMAL"|"WARNING"|"ALARM"|"UNKNOWN", ...}`.
`warning_level_cm`/`alarm_level_cm` mogą być `null` (brak progu dla stacji).

## Security

Brak zmian — te same dane z tego samego już-zaufanego publicznego endpointu.

## Architecture Impact

Brak nowego ADR — reużycie istniejącego modelu `Measurement` i wzorca
reconciliation (upsert/delete względem własnego cyklu ingestu) już
ustanowionego i zrecenzowanego w ADR-009.
