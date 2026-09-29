# ADR-006: Nearest-station join dla /api/v1/dashboard/latest

**Status:** Accepted
**Data:** 2026-09-29

## Context

Po Phase 5 mamy dwa niezależne źródła w bazie: `measurements` (PM2.5 ze stacji GIOŚ,
punktowe współrzędne) i `weather_snapshots` (pogoda per `geo_area`, ADR-005's 7 ręcznie
wybranych lokalizacji). Mobile pokazuje je jako dwie osobne, niepowiązane listy — nie ma
jednego widoku "co się dzieje wokół mnie" per lokalizacja, mimo że produkt (CLAUDE.md,
jedno zdanie) właśnie to obiecuje.

Master Plan i CLAUDE.md rule #14 nazywają docelowy endpoint `/api/v1/dashboard` (i
pochodne). Pełne dopasowanie użytkownik → gmina (Phase 6 Geo Engine, TERYT,
point-in-polygon) to osobna, większa decyzja: wymaga wyboru źródła danych TERYT,
licencji, algorytmu — i jest świadomie odłożona (ADR-005's explicit non-goals), bo
wymaga też decyzji produktowej, nie tylko technicznej.

## Problem

Jak dać sensowny, jeden widok per lokalizacja BEZ czekania na pełny Geo Engine i bez
zgadywania dopasowania stacja↔gmina "na oko" (zakazane przez rule #9)?

## Decision

`GET /api/v1/dashboard/latest`: dla każdego `geo_area` (z istniejącego seeda, ADR-005)
znajdź NAJBLIŻSZĄ stację GIOŚ (haversine, `app/geo.py`) i jeśli mieści się w progu
`MAX_MATCH_DISTANCE_KM` (50 km — stała, udokumentowana, nie "na wszelki wypadek"),
dołącz jej najświeższy odczyt PM2.5. To jest metoda "nearest station" wprost dozwolona
przez ADR-001/rule #9 — deterministyczna i testowalna (znane współrzędne, znana
odległość, jeden wynik).

To NIE jest Phase 6 Geo Engine:
- Nie matchuje dowolnych współrzędnych użytkownika — tylko nasze własne, już zaszyte
  `geo_areas` (7 lokalizacji).
- Nie używa TERYT ani granic administracyjnych.
- Próg 50 km jest arbitralny (na tyle duży, by złapać jedyną obecnie zasiloną stację —
  Kłodzko — ale nie na tyle duży, by parować lokalizacje setki km od siebie).

Endpointy `/api/v1/air/latest` i `/api/v1/weather/latest` zostają bez zmian (rule #7:
measurement/forecast nie mieszamy) — `/dashboard/latest` to widok złożony z tych samych
danych, nie nowe źródło prawdy.

## Consequences

- Mobile dostaje jeden endpoint do jednego widoku per lokalizacja — bez zgadywania.
- Gdy przybędzie więcej stacji GIOŚ, dopasowanie samo się poprawi (więcej kandydatów do
  "nearest"), bez zmiany kodu.
- Gdy ruszy Phase 6 (pełny TERYT Geo Engine), ten endpoint albo zostanie zastąpiony,
  albo `MAX_MATCH_DISTANCE_KM`+haversine zostanie zamienione na realne dopasowanie do
  gminy — to świadomy, przewidziany koszt migracji, nie przeoczenie.
