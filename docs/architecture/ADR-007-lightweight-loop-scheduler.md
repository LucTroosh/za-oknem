# ADR-007: Loop-based scheduler zamiast pełnego SCHEDULER/JOB/QUEUE/WORKER

**Status:** Accepted
**Data:** 2026-09-29

## Context

Oba connectory (`gios`, `open_meteo`) mają gotowe, przetestowane `ingest_station`/
`ingest_geo_area` + CLI `main()` — ale uruchamiane wyłącznie ręcznie. Master Plan §46
opisuje docelowy mechanizm: SCHEDULER → JOB → QUEUE → WORKER → CONNECTOR, z tabelą
`jobs` (schedule, retry policy, last_run/last_success/last_failure, duration,
records fetched/processed, error count).

## Problem

Jak dziś (jeden VPS, dwa connectory, fetch co 1h/3h wg ADR-004) zacząć automatyczne
odświeżanie danych, bez budowania pełnej infrastruktury joba/kolejki/workera,
zanim jest ku temu realny powód (rule #10 — build for expansion, not overengineering)?

## Decision

Jeden dodatkowy proces (`app.scheduler`, w tym samym obrazie co API) z prostą pętlą:
budzi się co 60s, sprawdza czy minął interwał dla `open_meteo` (3h) albo `gios` (1h)
i jeśli tak — woła bezpośrednio `ingest_geo_area`/`ingest_station` (te same funkcje
co CLI, bez duplikacji logiki). Brak tabeli `jobs`, brak kolejki, brak osobnego
worker-procesu — jeden proces, jedna pętla, stdlib (`time.sleep`), stan w pamięci.

`open_meteo` uruchamia się dla wszystkich `geo_areas` (deterministyczne, już tak
działa domyślnie w CLI). `gios` wymaga listy `station_id` — ta lista **nie jest
zgadywana tutaj**: pochodzi z nowej zmiennej środowiskowej `GIOS_STATION_IDS`
(rule #9 — dopasowanie geo musi być deterministyczne i jawne, nie "na oko"; wybór
KTÓRE stacje monitorować to decyzja produktowa/Geo Engine, Phase 6 — nie temat tego
ADR). Pusta/brak zmiennej = scheduler pomija GIOŚ i loguje to jawnie, nie zgaduje.

**Explicit non-goals:**
- Tabela `jobs` z historią uruchomień (last_run/last_success/duration/error_count z
  §46) — dodać dopiero gdy faktycznie potrzebny będzie wgląd/alertowanie na
  nieudane runy, nie z góry.
- Kolejka (Redis/Celery/RQ) i osobny worker-proces — nie ma dziś więcej niż 2
  connectory i garstka lokalizacji; jeden proces w pętli w pełni wystarcza.
- Automatyczny dobór stacji GIOŚ per `geo_area` (nearest-station) — to Phase 6
  Geo Engine, nie scheduler.

## Consequences

- Dane odświeżają się same, bez ręcznego CLI — dashboard przestaje być
  "testowalny raz", staje się faktycznie żywy.
- Redis (`REDIS_URL`, już w stacku) zostaje nieużyty przez scheduler — jeśli
  kiedyś pojawi się druga replika API/schedulera, stan pętli (`last_run`) trzeba
  będzie przenieść do Redis, żeby uniknąć podwójnego fetchu. Świadomy,
  zaakceptowany koszt migracji, nie przeoczenie (tak jak ADR-005 dla `geo_areas`).
- `GIOS_STATION_IDS` pusty domyślnie — użytkownik musi świadomie skonfigurować,
  które stacje chce monitorować; brak wartości = brak automatycznego GIOŚ, nie cichy
  błąd.
