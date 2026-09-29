# TASK 9.6 — Typed response model dla `/api/v1/alerts/latest`

## Goal

Ten sam wzorzec co TASK-4.2/5.5/9.5, zastosowany do ostatniego z prostych
GET-ów: `GET /api/v1/alerts/latest`. Domyka response_model dla wszystkich
czterech endpointów danych (§10 checklist REST API).

## Scope

- `api/v1/alerts.py`: `AlertOut`, `AlertsLatestResponse` (Pydantic).
  `source` zostaje `str` (nie `Literal`) - w przeciwieństwie do air/weather,
  alerty już dziś pochodzą z więcej niż jednego `source_id` (ADR-009:
  `imgw_warningshydro`, docelowo `imgw_warningsmeteo`). `areas` zostaje
  `list[dict[str, Any]]` - to celowo nieznormalizowany surowy JSON źródła
  (ADR-009: tabela byłaby przedwczesna przed decyzją o geo-matchingu).

## Acceptance Criteria

- [x] `response_model=AlertsLatestResponse` na `GET /alerts/latest`.
- [x] `comment`/`probability_pct` (realnie nullable w modelu DB) nadal
      przechodzą jako `None`, nie stają się wymagane.
- [x] Istniejące testy `test_alerts.py` przechodzą bez zmian.
- [x] Nowe testy: model przyjmuje realny kształt, odrzuca brakujące pole i
      nieznaną wartość `freshness`.
- [x] `ruff check`/`ruff format --check` czyste.

## Dependencies

Brak (niezależne od PR #45/#47/#49/#50/#51/#52/#53 — inny plik).

## Data Contract

Bez zmian.

## Security

Brak nowej powierzchni.

## Architecture Impact

Brak.
