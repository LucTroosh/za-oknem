# TASK 3.1 — Raw ingestion / provenance (ADR-014)

## Goal

Odpowiedzieć na pytanie audytowe Master Planu §33 „co dokładnie zwróciło
źródło, gdy zapisaliśmy tę wartość?”: surowy payload + wersja parsera + status
walidacji, jednoznacznie powiązane z każdym rekordem znormalizowanym, z ograniczoną
retencją (rule #6, rule #10).

## Scope

- ADR-014 (`docs/architecture/ADR-014-raw-ingestion-provenance.md`).
- Model `SourceFetch` (`source_fetches`: source_id, endpoint, fetched_at,
  parser_version, validation_status, payload JSONB) + nullable FK
  `source_fetch_id` na `Measurement`, `Alert`, `WeatherSnapshot`, `Forecast`;
  migracja `0009_source_fetches.py`.
- `app/provenance.py`: `record_fetch()` (best-effort), `set_validation_status()`,
  `batch_status()`, `purge_expired_payloads()`, `RETENTION_DAYS`.
- `PARSER_VERSION` w `parser.py` każdego connectora; integracja: `gios` (fetch
  per `getData`), `open_meteo` (fetch per geo_area), `imgw_hydro`
  (`ingest_snapshot`), `imgw_warningshydro` (`ingest_raw`) — scheduler i CLI
  wołają te same funkcje.
- Scheduler: job `run_raw_retention` raz na dobę, izolowany (rule #1), bez
  wpisu w `source_status`.

## Non-goals

- `imgw_warningsmeteo` — brak ingestu (TASK-9.2 BLOCKED); podłączy się tym samym
  kontraktem.
- Backfill rekordów sprzed 0009 (payloadów już nie ma).
- Wystawianie provenance w mobile API / endpoint audytowy.
- Zapis list stacji/sensorów GIOŚ (tylko metadane).
- Deduplikacja identycznych payloadów, kasowanie wierszy metadanych.

## Acceptance Criteria

- [ ] Każdy działający connector zapisuje `source_fetches` i ustawia
      `source_fetch_id` na rekordach z tego pobrania (testy per connector).
- [ ] Payload nieparsowalny jest zapisany ze statusem `invalid`; częściowo
      odrzucony wsad = `partial`; poprawny = `valid`.
- [ ] Nieudany zapis provenance nie blokuje zapisu rekordów (FK NULL) — także
      dla `Alert`; odświeżenie rekordu przy nieudanym zapisie zeruje link.
- [ ] Retencja zeruje tylko payloady starsze niż okno źródła (7/7/14/30 dni),
      źródło spoza listy 7 dni; wiersze i FK zostają; payload = SQL NULL.
- [ ] Job retencji wpięty w scheduler, jego awaria nie zatrzymuje pozostałych
      jobów i nie tworzy wpisu w `source_status`.
- [ ] Migracja Alembic 0009 (rule #4) — `alembic upgrade head` i
      `alembic check` przechodzą; `ruff check`, mypy, pytest w CI.

## Tests

`tests/test_provenance.py` (model, record/status, best-effort, retencja),
`TestProvenance` w `tests/connectors/test_{gios,open_meteo,imgw_hydro,
imgw_warningshydro}_ingest.py`, `tests/test_scheduler.py` (hydro/ostrzeżenia
przez nowe punkty wejścia, `run_raw_retention`, `track_status=False`).

## Dependencies

ADR-004 (cykle fetchowania), ADR-007 (scheduler), ADR-012 (`source_status`).
Kolejne źródła (CAMS, `Event` z TASK-9.4, kąpieliska) korzystają z tego
kontraktu.

## Data Contract

Nowa tabela `source_fetches`; nowa nullable kolumna `source_fetch_id` (indeks,
FK) w czterech tabelach. Brak zmian w API.

## Security

Payload to publiczne dane źródeł (licencje w `source-registry.md`); brak
sekretów — żądania nie niosą kluczy (Open-Meteo/GIOŚ/IMGW bez kluczy). Źródło
z kluczem API w URL (CAMS) musi zapisywać `endpoint` bez klucza. Brak ekspozycji
w API. LLM nie uczestniczy (rule #10).

## Architecture Impact

ADR-014 (Accepted): nowy typ danych (provenance), rule #12.
