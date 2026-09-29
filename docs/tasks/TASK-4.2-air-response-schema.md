# TASK 4.2 — Typed response model dla `/api/v1/air/latest`

## Goal

`GET /api/v1/air/latest` dziś zwraca `-> dict` bez `response_model` — FastAPI
generuje dla niego pusty/nieprecyzyjny schemat OpenAPI (`{}`), więc endpoint
nie ma żadnej udokumentowanej, wymuszanej struktury odpowiedzi mimo że jest to
flagowy endpoint Vertical Slice (GIOŚ → ... → PM2.5 na ekranie). Dodać
Pydantic `response_model`, żeby kształt był udokumentowany i żeby FastAPI
walidowało odpowiedź przy każdej zmianie kodu (regresja kształtu wywali 500,
nie cichą literówkę w kluczu).

## Scope

- `api/v1/air.py`: nowe modele Pydantic (`AirParam`, `AirStation`,
  `AirLatestResponse`) odzwierciedlające dokładnie dzisiejszy kształt dict
  (żadnej zmiany API na zewnątrz - to czysto wewnętrzne wzmocnienie typów).
  `response_model=AirLatestResponse` na dekoratorze; funkcja nadal zwraca
  zwykły dict (FastAPI waliduje/filtruje przez response_model niezależnie od
  tego, czy zwracasz dict czy instancję modelu).
- Żadnych zmian w `dashboard.py`/mobile — ten task dotyczy wyłącznie
  `/air/latest`, inne endpointy to osobne taski (mniejszy, przeglądalny PR).

## Non-goals

- `/weather/latest`, `/weather/forecast`, `/hydro/latest`, `/alerts/latest`,
  `/dashboard/latest` — ten sam wzorzec, ale osobne taski/PR-y (każdy mały i
  niezależny, zgodnie z workflow).
- `/health`, `/health/ready` — dwuklawiszowy `{"status": "ok"}`, brak realnej
  wartości z formalnego modelu (YAGNI).

## Acceptance Criteria

- [x] `response_model=AirLatestResponse` na `GET /air/latest`.
- [x] Puste `stations: []` nadal poprawnie serializuje się przez model (brak
      wyjątku walidacji na pustej liście - test: `test_empty_stations_valid`).
- [x] Model odrzuca (422 przy realnym FastAPI request, `ValidationError` w
      testach jednostkowych) odpowiedź z brakującym wymaganym polem - dowód,
      że response_model faktycznie coś wymusza, a nie jest kosmetyką.
- [x] Istniejące testy `test_air.py` przechodzą bez zmian w oczekiwanym JSON
      (ten task nie zmienia kształtu odpowiedzi, tylko go typuje).
- [x] `ruff check`/`ruff format --check` czyste.

## Dependencies

Brak (niezależne od PR #45/#47/#49/#50 — inny plik).

## Data Contract

Bez zmian — `response_model` opisuje istniejący, już ustalony kształt
`{"stations": [...]}`.

## Security

Brak nowej powierzchni.

## Architecture Impact

Brak — czysto wewnętrzne typowanie jednego endpointu.
