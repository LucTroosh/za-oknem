# TASK 6.1 — Loop-based scheduler dla obu connectorów

## Goal

Dane mają się odświeżać same (bez ręcznego CLI), bez budowania pełnego
SCHEDULER/JOB/QUEUE/WORKER z Master Planu §46, zanim jest ku temu realny powód
(rule #10).

## Scope

- ADR-007: decyzja o zakresie (jeden proces, pętla, stdlib — nie kolejka/worker).
- `app/scheduler.py`: `run_open_meteo()` (wszystkie `geo_areas`, co 3h),
  `run_gios()` (stacje z `GIOS_STATION_IDS`, co 1h), `main()` z pętlą `while`.
- `docker-compose.yml`: nowy, opcjonalny serwis `scheduler` (ten sam obraz co `api`).
- `.env.example`: `GIOS_STATION_IDS` (puste domyślnie).

## Acceptance Criteria

- [x] `run_open_meteo` woła `ingest_geo_area` dla każdego `geo_area` (test:
      `test_ingests_every_geo_area`).
- [x] `run_gios` bez `GIOS_STATION_IDS` nic nie robi i nie zgaduje stacji (test:
      `test_skips_when_no_station_ids_configured`) — rule #9.
- [x] `run_gios` z ustawioną zmienną ingestuje dokładnie te stacje (test:
      `test_ingests_configured_stations`).
- [x] `main()` respektuje interwały per-job niezależnie (test:
      `test_third_iteration_reruns_gios_after_its_interval`).
- [x] Scheduler i CLI używają tych samych `ingest_station`/`ingest_geo_area` —
      zero duplikacji logiki ingestu.

## Tests

`apps/api/tests/test_scheduler.py`.

## Non-goals

- Tabela `jobs` / historia uruchomień / retry policy z Master Planu §46.
- Kolejka (Redis/Celery/RQ) i osobny worker-proces.
- Automatyczny dobór stacji GIOŚ per `geo_area` (nearest-station) — Phase 6 Geo
  Engine, nie scheduler.

## Dependencies

TASK-5.1, TASK-5.2 — używa istniejących connectorów i modeli.

## Data Contract

Brak nowego API — scheduler tylko woła istniejące funkcje ingestu.

## Security

Brak nowych sekretów. `GIOS_STATION_IDS` to konfiguracja, nie sekret.

## Architecture Impact

ADR-007 (nowa, jawnie ograniczona w zakresie decyzja — nie pełny §46).
