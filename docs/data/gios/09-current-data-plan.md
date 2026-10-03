# Bieżące dane GIOŚ — zakres po decyzji właściciela 2026-10-03

Ten dokument doprecyzowuje PR #134 / 04-work-breakdown. Misja: „Co dzieje się u Ciebie
za oknem”. Implementacja danych → brief Design Leada → finalny UI → build/testy na
urządzeniu. Testy automatyczne i niezależny code review wykonujemy podczas developmentu.

| Task | Wynik / odbiór | Stan |
|---|---|---|
| CURRENT-01 | Utrwalić zakres i on hold; ADR-033 | W tym PR, do review |
| CURRENT-02 | 7 parametrów, pełna paginacja sensorów, brak fikcyjnych zer i jednostek | Implementacja do review; test paginacji i uszkodzonego przejścia |
| CURRENT-03 | Jedna stacja dla dashboard/latest/history/index; bieżąca przed archiwalną; stabilny remis sensorów | Implementacja do review; test SQL i zgodności endpointów |
| CURRENT-04 | Indeks GIOŚ: fetch/parser/snapshot/provenance/DB-only API, izolacja awarii, źródłowe czasy i skala | Implementacja do review; migracja 0019; flaga domyślnie off |
| CURRENT-05 | Historia 24/48 h, brak interpolacji, niejednoznaczne godziny DST rozróżnione offsetem | PR #146/#147 + poprawka review w tym PR; QA urządzenia po UI |
| CURRENT-06 | Osobny agent CR, poprawki, Ruff/mypy/pytest/kontrakty i mobile lint/types/tests | Weryfikacja w tym PR; PostGIS w CI |
| CURRENT-07 | Brief prawdziwych danych, stanów i ograniczeń dla Design Leada | `docs/ui/gios-current-data-design-brief.md` |
| CURRENT-08 | Implementacja zatwierdzonego UI, build, testy urządzenia i realnego backendu | Po pracach Design Leada; nie wykonywać builda wcześniej |

## On hold

GIOS-04/05: historyczny hałas i zasięgi. GIOS-06/07: PRTR, ZZR/ZDR i historia awarii.
GIOS-08/09: plany i okresowe oceny wód. GIOS-10: roczne oceny powietrza/skład PM2.5/
chemizm opadów. GIOS-11/12: NEC, gleby, PEM, promieniowanie, przyroda, morze, CLC,
monitoring zintegrowany. GIOS-13: UI historycznego modułu Twoja okolica.
Dokumentacja i istniejący kod zostają. Brak aktualnych pomiarów = brak nowego kafelka.

## Dalsze bieżące operacje — discovery przed implementacją

W katalogu JPOAT są także `aggregate/getAggregatePm10Data` (agregaty ostatnich 3 dób)
i `levels/getInformationAboutExceeding` (aktywne informacje o przekroczeniach).
Nie zostały zaimplementowane w tym PR i nie są metrykami gotowymi dla Design Leada.
Potrzebują niepustej/pustej/błędnej próbki, jednostek, okresu i lokalnego przypisania.
Informacji o przekroczeniu nie tworzymy sami z chwilowego stężenia. To kolejne zadania
CURRENT-09/10, oparte na własnym gate; nie mylić ich z odłożonymi rocznymi rejestrami.

## Uruchomienie indeksu i rollback

1. Merge zależności #146/#147 i tego PR, migracje `uv run alembic upgrade head`.
2. Ustawić `GIOS_PROVIDER_INDEX_ENABLED=true` w konfiguracji backendu/schedulera.
3. Kontrolowany `python -m app.connectors.gios.ingest --station-id 52`; następnie
   `GET /api/v1/air/provider-index?geo_area_id=<aktywna lokalizacja>` dla własnego obszaru.
   Stacja odpowiedzi musi zgadzać się z `/air/latest` i `/air/history`.
4. Sprawdzić źródłowe daty, freshness, attribution i degradację przy błędzie.
5. Rollback: flaga false, bez usuwania danych; pomiary i EAQI nadal działają.

Włączenie flagi/backendu i rollout nie zostały wykonane przez agenta. Lokalny import
próbki/testy nie są dowodem wdrożenia na produkcji ani testem aplikacji na urządzeniu.
