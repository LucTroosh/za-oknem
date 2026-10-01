# TASK-8.5 / 8.6 / 8.7 — Pyłki: źródło, model + ingest + scheduler, endpoint

Decyzja i research: [ADR-020](../architecture/ADR-020-pollen-source.md). Rejestr:
`docs/data/source-registry.md` → `open_meteo_pollen`. Mobile (TASK-8.8) i agregat
`dashboard_latest()` (TASK-8.9) to **osobne PR-y**.

## Goal

Backend pyłków dla 5 gatunków MVP (olcha, brzoza, trawy, bylica, ambrozja): źródło
zatwierdzone w Source Approval Gate, snapshot modelowy per gmina w PostgreSQL z pełnym
provenance, job w schedulerze raz na cykl modelu i `GET /api/v1/pollen/latest`.

## Scope

- TASK-8.5: wpis `open_meteo_pollen` w source-registry (licencja, commercial_use,
  rate_limit, attribution, status) + ADR-020. CAMS ADS zostaje alternatywą (klucz =
  blokada człowieka).
- TASK-8.6: model `PollenSnapshot` + migracja Alembic 0012 + connector
  `open_meteo_pollen` (client/parser/ingest) + retencja payloadu 7 dni + job
  schedulera (24 h) z `source_status` i licznikiem budżetu.
- TASK-8.7: `GET /api/v1/pollen/latest` (per geo_area, freshness, `source_status`,
  `source` + `attribution`).

## Acceptance Criteria

1. `PollenSnapshot` ma jawnie 5 gatunków (`alder`, `birch`, `grass`, `mugwort`,
   `ragweed`, grains/m³), `valid_at`, `forecast_reference_time`, `model`, `fetched_at`,
   `geo_area_id`, `source_fetch_id` (FK do `source_fetches`); model ⇔ migracja 0012
   (`alembic check` czysty).
2. Parser przyjmuje wyłącznie kształt z dokumentacji; zły kształt/wartość (tekst,
   bool, ujemna, NaN/inf, niejednakowe jednostki, offset ≠ 0, niezgodna długość
   tablic) → `OpenMeteoPollenParseError`, payload zostaje w `source_fetches` jako
   `invalid`.
3. Brak wartości z modelu → NULL w bazie i `null` w API; `0` pozostaje `0`; nigdzie
   brak nie jest zamieniany na 0.
4. Ingest: surowy payload zapisany przed parsowaniem (`pending`), potem `valid`/
   `invalid`; wiersze wskazują `source_fetch_id`; idempotentny w tej samej dobie;
   awaria jednej gminy nie zatrzymuje pozostałych; timeout + 1 retry (rule #5).
5. Każda REALNA próba HTTP liczy się w liczniku `open_meteo` (wspólny budżet,
   alert 70%).
6. Scheduler: job `open_meteo_pollen` co 24 h przez `_run_job_safely`; całkowita
   awaria (żadna gmina) → wyjątek → `source_status` failure; brak `geo_areas` → nic
   nie zapisuje; CLI zapisuje `source_status` tak samo.
7. `/api/v1/pollen/latest`: typowany `response_model`; `kind="model_forecast"`;
   `current` + `days`; freshness FRESH ≤ 32 h / RECENT ≤ 64 h / STALE; `source_status`
   (UNAVAILABLE bez udanego przebiegu); `source`/`attribution` zgodne z registry;
   czyta wyłącznie z bazy (rule #14).

## Tests

`tests/connectors/test_open_meteo_pollen_{client,parser,ingest}.py`,
`tests/test_pollen.py`, `tests/test_scheduler.py` (pollen), `tests/test_provenance.py`
(retencja). Fixture parsera jest zbudowany tylko z pól potwierdzonych w dokumentacji i
oznaczony jako fixture (nie nagrana odpowiedź).

## Non-goals

Karta mobile (8.8), agregat dashboardu (8.9), profil alergika (12.4), gatunek oliwka,
geo-matching do lokalizacji użytkownika (Geo Engine), retencja starych wierszy
`pollen_snapshots` (`# ponytail` w ADR-020), bezpośredni CAMS ADS (klucz).

## Dependencies

ADR-001 (snapshot per gmina), ADR-003 (licencja), ADR-004 (cykl), ADR-012
(`source_status`), ADR-014 (provenance), TASK-13.1a (licznik), TASK-6.1 (scheduler).
Migracja 0012: `down_revision = "0009"` (head main w chwili PR); PR #67 (0010) i #70
(0011) w toku — koordynator przepina po ich merge'u.

## Data Contract

Źródło: Open-Meteo Air Quality API, `hourly.time` (ISO 8601, UTC) + równoległe
tablice `alder_pollen` … `ragweed_pollen` (`float | null`), `hourly_units` (jedna
jednostka dla wszystkich), `utc_offset_seconds`. Szczegóły i lista
niezweryfikowanego w ADR-020.
API: `{areas[{geo_area_id, slug, name, latitude, longitude, kind, model, unit,
forecast_reference_time, fetched_at, freshness, valid_at, current{5×float|null},
days[{date, max{5×float|null}}]}], source, attribution, source_status}`.

## Security

Bez sekretów (brak klucza). Do zewnętrznego API idą wyłącznie współrzędne centroidu
gminy, nie użytkownika. Endpoint zapisany w provenance nie zawiera danych wrażliwych.
LLM nie uczestniczy (rule #10 — i tak nie są to dane bezpieczeństwa).

## Architecture Impact

Nowa tabela `pollen_snapshots`, nowy `source_id` `open_meteo_pollen`, nowy job
schedulera, wspólny licznik `open_meteo`. ADR-020 (+ dopisek w ADR-003: pyłki
podlegają niekomercyjnemu tierowi Open-Meteo).
