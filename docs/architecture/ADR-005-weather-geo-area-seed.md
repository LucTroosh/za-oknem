# ADR-005: Minimalny zestaw geo_areas jako seed przed pełnym Geo Engine

**Status:** Accepted
**Data:** 2026-09-28

## Context

ADR-001 (opcja C) ustala: pogoda/pyłki jako snapshot per gmina w bazie, mobile API
czyta wyłącznie z bazy, zasięg pobierania (aktywne obszary → cała Polska) jest
parametrem konfiguracyjnym schedulera, nie zmianą architektury. Master Plan sekwencjonuje
jednak Geo Engine (§27, dopasowanie nearest-station/point-in-polygon/TERYT) jako Phase 6,
PO Phase 5 (Weather). Żeby zaimplementować connector Open-Meteo teraz (Phase 5), potrzebna
jest jakaś tabela `geo_areas` — ale pełny, zweryfikowany zbiór wszystkich gmin z TERYT to
zakres Phase 6, nie Phase 5.

## Problem

Jak zacząć Phase 5 (Weather) bez czekania na Phase 6 (Geo Engine) i bez wymyślania
architektury sprzecznej z ADR-001?

## Decision

`geo_areas` to płaska tabela referencyjna (id, slug, name, latitude, longitude) —
**nie** pełny model TERYT/gmina z Master Planu §26/§27. Seed startowy: mały, ręcznie
wybrany zestaw kilku polskich miejscowości (w tym Kłodzko — ciągłość z już działającym
GIOŚ vertical slice, żeby dashboard mógł pokazać PM2.5 + pogodę dla tej samej lokalizacji).

To jest zgodne z ADR-001 opcją C ("aktywne obszary" mogą być małym, ręcznie zarządzanym
zbiorem na start) — nie jest nową decyzją architektoniczną, tylko jej pierwszą konkretną
instancją w najmniejszym możliwym kształcie.

**Explicit non-goals (Phase 6 territory, nie teraz):**
- Dopasowanie user lat/lon → najbliższa gmina (nearest-station/point-in-polygon).
- Pełna lista gmin z TERYT.
- Administrative Context (powiat/województwo) per §26.

Migracja z tego seeda do pełnego Geo Engine (Phase 6) to rozszerzenie tabeli
`geo_areas` o kolumnę TERYT + import pełnej listy gmin — nie zmiana schematu
`weather_snapshots` (klucz obcy `geo_area_id` zostaje ten sam).

## Consequences

- Phase 5 może ruszyć bez blokady na Phase 6.
- `geo_areas` będzie wymagało migracji rozszerzającej przy Phase 6 (dodanie TERYT,
  import pełnej listy) — to świadomy, zaakceptowany koszt, nie przeoczenie.
- Zasięg pogodowy na start = tylko te kilka zaszytych lokalizacji, nie cała Polska —
  zgodne z ADR-001 (rozszerzanie zasięgu to config, nie redeploy).
