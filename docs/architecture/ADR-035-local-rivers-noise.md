# ADR-035 — Lokalne rzeki i pomiary hałasu

Date: 2026-10-03
Status: Proposed (with implementation PR)

## Context

Właściciel produktu polecił dodać rzeki i hałas. Zmienia to wcześniejsze odłożenie tematów.
Istnieją adaptery IMGW hydro i GIOŚ noise oraz ekrany rivers/neighborhood.
Hałas GIOŚ jest pomiarem okresowym/historycznym; rzeki to obserwacje wodowskazowe.

## Problem

Lista rzek z całej Polski nie odpowiada misji „u Ciebie za oknem”. Wejście „Twoja okolica”
nie mówi wprost, że zawiera hałas. Nie można przedstawiać historii jako danych live ani
odległości od wodowskazu jako rozpoznania ryzyka powodziowego pod danym adresem.

## Options

1. Nowe connectory i osobna architektura: odrzucone, istnieją potrzebne moduły.
2. Rozbudowa istniejących API/ekranów: wybrane, bez zależności i nowych tabel.

## Decision

- `hydro/latest?geo_area_id=...` wybiera obserwacje w promieniu 50 km (domyślna decyzja produktu,
  nie deklaracja IMGW). Opcjonalny `max_distance_km`: >0 do 100 km. Bez area_id zachowana lista krajowa.
- Najnowszy rekord osobno dla stacji i parametru, tylko imgw_hydro; przyszłe pomiary >5 min wykluczone.
  Odległość Haversine przed zaokrągleniem służy do filtrowania; distance_km służy do prezentacji.
- Mobile pobiera hydro dla swojej lokalizacji. Start ma wejście „Rzeki w okolicy”, szczegóły mają
  dystans, czas, poziom w cm i progi. Nie dodajemy mapy, zlewni ani prognozy powodzi.
- Brak progu ostrzegawczego nie pozwala nazwać odczytu poniżej alarmowego NORMAL. Niepoprawne
  progi oznaczają UNKNOWN; failed refresh oznacza STALE. Stare odczyty nie uzasadniają uspokojenia.
- GIOŚ noise wykorzystuje istniejący import/kontrakt/neighborhood. Wejście „Hałas w okolicy”,
  pomiary drogowe, kolejowe, przemysłowe i lotnicze z datą, porą, dB i dystansem.
  Nie tworzymy oceny „cicho/głośno teraz”, agregacji dB ani nowych porad.
- Dotychczasowe flagi publikacji pozostają off do spełnienia warunków źródeł. To rozdzielenie
  realizacji funkcji od aktywacji, nie dalsze odłożenie zakresu produktu.

## Consequences

Kompatybilne opcjonalne pola kontraktu, bez migracji. Dane własnej DB, awarie izolowane.
Promień może zwrócić pustą listę i może obejmować inną zlewnię; nie gwarantuje kompletności rzek.
GIOŚ ma rzadką siatkę i opóźnione publikacje. Hydro legacy parser zakłada Europe/Warsaw;
potwierdzenie strefy i warunków jest wymagane przed publikacją. Nie zmieniamy arbitralnie
historycznych timestampów ani identyfikatorów już zapisanych rekordów.
