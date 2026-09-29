# TASK 9.5 — Typed response model dla `/api/v1/hydro/latest`

## Goal

Ten sam wzorzec co TASK-4.2/5.5, zastosowany do `GET /api/v1/hydro/latest`.

## Scope

- `api/v1/hydro.py`: `HydroStation`, `HydroLatestResponse` (Pydantic),
  odzwierciedlające dokładnie dzisiejszy kształt dict. `status` i `freshness`
  jako zamknięte `Literal` - zamiast `str` - żeby przyszła literówka/nowa
  wartość w `compute_status()`/`freshness()` wywaliła się głośno na testach,
  nie przeszła cicho do klienta.

## Acceptance Criteria

- [x] `response_model=HydroLatestResponse` na `GET /hydro/latest`.
- [x] Istniejące testy `test_hydro.py` przechodzą bez zmian oczekiwanego JSON-a.
- [x] Nowe testy: model odrzuca brakujące pole i nieznaną wartość `status`.
- [x] `ruff check`/`ruff format --check` czyste.

## Dependencies

Brak (niezależne od PR #45/#47/#49/#50/#51/#52 — inny plik).

## Data Contract

Bez zmian.

## Security

Brak nowej powierzchni.

## Architecture Impact

Brak.
