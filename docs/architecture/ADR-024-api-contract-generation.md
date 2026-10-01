# ADR-024: Kontrakt API — `response_model` dla dashboardu + typy TS generowane z OpenAPI

- **Date:** 2026-10-01
- **Status:** Accepted

## Context

`/dashboard/latest` zwracał goły `dict` — jego schemat OpenAPI był generycznym obiektem, a
mobile utrzymywał ręczne typy (`index.tsx`, `alerts.ts`, `pollen.ts`, ...), które rozjeżdżały się
z backendem po każdym nowym bloku (pollen, outdoor, air.index). Pozostałe endpointy mają już
`response_model` (PR #51–#54).

## Problem

Jak mieć jedno źródło prawdy o kształcie odpowiedzi, wykrywać rozjazd backend↔mobile w CI i nie
dokładać zależności (CLAUDE.md: bez nowych zależności bez uzasadnienia)?

## Options

1. Ręcznie utrzymywane typy TS + test porównujący klucze — zero kodu generującego, ale rozjazd
   wykrywa tylko to, co ktoś dopisał do testu.
2. `openapi-typescript` (npm) — standard, ale nowa zależność dev i nowy etap `npm install` poza `apps/mobile`.
3. Własny generator ~60 linii (Node ≥ 22, bez zależności) dla podzbioru JSON Schema, który emituje
   pydantic — `openapi.json` → `schema.ts`, zatwierdzone w repo; CI sprawdza aktualność.

## Decision

Opcja 3. Przepływ: `DashboardResponse` (Pydantic, `app/api/v1/dashboard.py`) →
`apps/api/scripts/export_openapi.py` (deterministyczny `packages/api-contract/openapi.json`) →
`packages/api-contract/generate.mjs` (`schema.ts`, same typy). Dwa kroki CI z `--check`
(backend: `openapi.json`; mobile: `schema.ts`) — rozjazd = czerwone CI. Mobile importuje typy
wyłącznie przez `import type` (brak wpływu na bundler Metro). Widokowe typy UI (`PollenBlock`,
`OutdoorBlock`, ...) zostają tam, gdzie tolerują starszy backend, ale `contract.test.ts` wymusza
w `tsc`, że każdy blok kontraktu jest przez nie akceptowany.

Model odzwierciedla dokładnie dotychczasowy JSON: wszystkie pola wymagane, „brak danych" = `null`
(nigdy brak klucza), timestampy jako stringi ISO (blok `pollen` przechodzi przez
`jsonable_encoder`, by nie zmienić `+00:00` na `Z`). Awaria źródła (reguła #1) jest wyrażona
w kształcie (`freshness: UNAVAILABLE`, puste `items`), więc nigdy nie unieważnia modelu.

## Consequences

- Nowe pole w dashboardzie = zmiana modelu + `export_openapi.py` + `generate.mjs` (CI wskaże, czego brakuje).
- Pydantic odrzuca nieznane klucze przy serializacji — test kontraktowy porównuje body z surowym
  dictem endpointu, więc zapomniane pole nie przejdzie niezauważone.
- Bez `uv.lock` (znana luka repo) wydanie FastAPI/Pydantic zmieniające serializację OpenAPI może
  zaczerwienić `--check` na niezmienionym PR; komunikat podaje wersje, naprawa = regeneracja
  (jedna komenda). Docelowo: commit `uv.lock` + `uv sync --locked`.
- Generator obsługuje tylko konstrukcje, które emituje FastAPI/pydantic (`$ref`, `anyOf`, `enum`,
  `const`, `array`, `object`/`additionalProperties`); nieznany typ → `unknown`. Przy bardziej
  złożonych schematach rozważyć `openapi-typescript` (osobny ADR).
- Pozostałe ręczne typy w `index.tsx`/`alerts.ts`/`hydro.ts`/`outdoor.ts`/`aqi.ts` można migrować
  do `schema.ts` stopniowo (zmiany w UI poza zakresem tego ADR).

## Related

ADR-001 (Mobile API czyta tylko z bazy), ADR-012 (source_status), CLAUDE.md reguły #1, #7, #8.
