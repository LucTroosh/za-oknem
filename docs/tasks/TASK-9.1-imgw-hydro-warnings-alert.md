# TASK 9.1 — IMGW ostrzeżenia hydrologiczne: model Alert

## Goal

Pierwsza Alert vertical slice: ostrzeżenia hydrologiczne IMGW, `GET
/api/v1/alerts/latest`. Świadomie oddzielona od `imgw_hydro`/Measurement
(ADR-008 non-goal, rule #7) — inny model danych, inny cykl życia.

## Scope

- ADR-009: nowy model `Alert` (nie Measurement), `severity_raw` bez
  reinterpretacji (rule #10), obsługa pustego kształtu `{"message": ...}`.
- Connector `imgw_warningshydro`: `client.py` (jedno wywołanie + retry),
  `parser.py` (`parse_warnings()` — defensywnie akceptuje listę lub
  message-dict; `normalize()` — mapowanie pól bez reinterpretacji), `ingest.py`.
- Nowa migracja `0005_alerts.py` — tabela `alerts`, unique
  `(source_id, source_record_id)`.
- `GET /api/v1/alerts/latest` — tylko aktualnie ważne ostrzeżenia
  (`valid_until >= now`), czyta wyłącznie z naszej bazy (rule #14).
- Wpięcie do `app/scheduler.py` (co 1h, bez gatingu — jedno wywołanie zwraca
  wszystkie aktywne ostrzeżenia, deterministyczne).

## Acceptance Criteria

- [x] `parse_warnings()` traktuje `{"message": ...}` jako zero ostrzeżeń, listę
      jako listę, cokolwiek innego jako błąd (`ImgwWarningsHydroParseError`).
- [x] `normalize()` NIE reinterpretuje `stopień` — `severity_raw` zostaje
      dokładnie takim stringiem, jaki podaje źródło (test:
      `test_maps_fields_without_reinterpreting_severity`, `-1` niezmienione).
- [x] `areas`/`obszary` przechowywane surowo (JSON), bez normalizacji do
      osobnej tabeli (ADR-009 — geo-matching to non-goal tego taska).
- [x] Jedno zepsute ostrzeżenie nie przerywa ingestu reszty (test:
      `test_one_bad_warning_does_not_abort_the_rest`) — rule #1.
- [x] Dedup po `(source_id, source_record_id)` — duplikat nie tworzy nowego
      wiersza (test: `test_ingest_warning_skips_duplicate`).
- [x] `/alerts/latest` zwraca tylko ostrzeżenia z `valid_until` w przyszłości.
- [x] `run_imgw_warningshydro()` w schedulerze nie wymaga żadnej konfiguracji.

## Tests

`apps/api/tests/connectors/test_imgw_warningshydro_{client,parser,ingest}.py`,
`apps/api/tests/test_alerts.py`, `apps/api/tests/test_scheduler.py`
(`TestRunImgwWarningsHydro`).

## Non-goals

- `warningsmeteo` (osobny endpoint, osobny task — Source Registry
  `imgw_warningsmeteo`, status DISCOVERY).
- Geo-matching `areas`/wojewodztwo do `geo_areas`/lokalizacji użytkownika.
- Alert Engine (Master Plan §47) i Notification Engine — ten task tylko
  przechowuje i udostępnia surowe ostrzeżenia źródła.
- Reinterpretacja `stopień` na własną skalę ważności (rule #10 — nigdy).

## Dependencies

Nowa migracja Alembic `0005_alerts.py` (rule #4 — wyłącznie migracja, tabela
`alerts` nie istnieje wcześniej).

## Data Contract

`GET /api/v1/alerts/latest` → `{"alerts": [{external_id, source, event_type,
severity_raw, probability_pct, issuing_office, description, comment, areas,
valid_from, valid_until, published_at}]}`.

## Security

Brak nowych sekretów. Brak klucza API (publiczny endpoint).

## Architecture Impact

ADR-009 (nowy model `Alert`, oddzielny od `Measurement` — rule #7).
