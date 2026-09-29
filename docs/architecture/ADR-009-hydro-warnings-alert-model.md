# ADR-009: Pierwszy model Alert — ostrzeżenia hydrologiczne IMGW

**Status:** Accepted
**Data:** 2026-09-29

## Context

ADR-008 celowo odłożył ostrzeżenia (`warningshydro`/`warningsmeteo`) jako inny
koncept danych niż Measurement (rule #7). Master Plan §32 definiuje Alert bardzo
oszczędnie: "reprezentacja zdarzenia istotnego dla użytkownika", "Alert nie jest
tym samym co notification", "Alert może istnieć bez wysłania push" — bez
konkretnego schematu pól. Kształt `warningshydro` zweryfikowany na żywo w ADR-008:

```json
{
  "opublikowano": "2026-05-17 08:45:07",
  "stopień": "-1",
  "data_od": "2026-05-17 08:45:56",
  "data_do": "9999-12-31 23:59:59",
  "prawdopodobieństwo": "90",
  "numer": "31",
  "biuro": "Biuro Prognoz Hydrologicznych we Wrocławiu, ...",
  "zdarzenie": "Susza hydrologiczna",
  "przebieg": "...", "komentarz": "...",
  "obszary": [{"wojewodztwo": "wielkopolskie", "opis": "...", "kod_zlewni": [...]}]
}
```

## Problem

1. Jaki minimalny schemat `Alert` po naszej stronie ma sens, skoro Master Plan nie
   precyzuje pól, a jest tylko jedno źródło do zweryfikowania (IMGW)?
2. `stopień` dla suszy hydrologicznej to `"-1"` — inna skala niż typowe ostrzeżenia
   meteo (zwykle 1/2/3). Czy interpretować/normalizować ten numer?
3. Ostrzeżenia dotyczą województw/zlewni, nie punktów lat/lon jak nasze `geo_areas`
   — jak (i czy już teraz) je dopasować do lokalizacji użytkownika?
4. Zweryfikowano (WebFetch), że `warningsmeteo` przy braku ostrzeżeń zwraca obiekt
   `{"message": "..."}`, nie pustą listę — nie potwierdzono, że `warningshydro`
   zachowuje się identycznie w stanie pustym.

## Decision

- Nowa tabela `alerts` — pola wprost z payloadu IMGW, **bez reinterpretacji**
  `stopień` (rule #10: LLM/kod nigdy nie jest źródłem prawdy dla danych
  bezpieczeństwa — `severity_raw` trzymane jako string dokładnie tak, jak przyszło
  ze źródła, żadnej własnej skali 1-5 ani mapowania na kolory).
- `obszary` trzymane jako JSON (kolumna `areas`, `sqlalchemy.JSON`) — bez
  rozbijania na osobną tabelę: dopasowanie województwo↔`geo_area` to osobna,
  jeszcze nierozstrzygnięta decyzja (patrz Non-goals), więc normalizowanie
  struktury teraz byłoby zgadywaniem przyszłego kształtu zapytań (rule #10).
- Connector `imgw_warningshydro` (parser + client) **defensywnie** obsługuje oba
  znane kształty "pusto": lista `[]` ORAZ obiekt `{"message": ...}` — zamiast
  zgadywać które zachowanie ma `warningshydro`, kod działa poprawnie dla obu.
  Każdy inny kształt = głośny błąd (rule #10), nie cichy fallback.
- `source_record_id = f"{numer}:{opublikowano}"` — jeśli IMGW republikuje/aktualizuje
  ostrzeżenie z nowym `opublikowano`, dostajemy nowy wiersz (historia zachowana,
  §33 provenance), nie nadpisanie.
- `GET /api/v1/alerts/latest` — lista **aktualnie ważnych** ostrzeżeń
  (`data_do` w przyszłości), bez filtrowania po lokalizacji użytkownika.
- **Reconciliation** (dodane po code review PR #37): `data_do` bywa rokiem 9999
  (susza) — samo źródło nigdy nie mówi "to ostrzeżenie już nieaktywne", po
  prostu przestaje je zwracać. `ingest_batch()` po każdym KOMPLETNYM (bez
  błędów parsowania) fetchu zamyka (`valid_until` = czas fetcha) każdy aktywny
  wiersz tego źródła nieobecny w najnowszym snapshocie — inaczej fałszywy
  alert bezpieczeństwa mógłby wisieć w bazie praktycznie wiecznie (rule #10).
  Jeśli fetch jest CZĘŚCIOWO błędny (część rekordów nie sparsowała się),
  reconciliation jest pomijane w tej rundzie — niepełnemu snapshotowi nie
  ufamy na tyle, by na jego podstawie kasować ważne ostrzeżenia.
- **Upsert, nie tylko insert**: ostrzeżenie o tym samym `source_record_id` co
  już zapisane jest odświeżane (`valid_until`, `fetched_at` itd.), nie
  pomijane — inaczej ostrzeżenie zamknięte przez reconciliation, które IMGW
  potem znów zaczyna zwracać, zostałoby trwale "ukryte" pod starym,
  nieaktualnym `valid_until`.
- **Freshness na `fetched_at`, nie na `valid_until`** (rule #8): `/alerts/latest`
  zwraca `fetched_at` i pole `freshness` (FRESH/RECENT/STALE) liczone od czasu
  ostatniego potwierdzenia aktywności alertu, nie od jego własnego `valid_until`
  — inaczej przestój schedulera/IMGW byłby niewidoczny dla klienta aż do
  (ewentualnie bardzo odległego) końca ważności ostrzeżenia.

**Explicit non-goals:**
- `warningsmeteo` — kolejny connector, nie ten sam PR (jedno źródło na raz,
  ten sam wzorzec co GIOŚ→Open-Meteo→IMGW hydro).
- Dopasowanie województwo/zlewnia → `geo_area` użytkownika — wymaga własnej
  decyzji (czy trzymać statyczną mapę 7 seedowanych lokalizacji do województw,
  czy czekać na pełny Geo Engine z TERYT, Phase 6). Na razie `/alerts/latest`
  zwraca WSZYSTKIE aktywne ostrzeżenia w Polsce, klient/UI filtruje sam.
- Alert Engine (reguły, deduplikacja semantyczna, priorytetyzacja) — Master Plan
  §47, osobna, większa decyzja.
- Notification Engine / push — Alert może istnieć bez powiadomienia (§32 wprost).

## Consequences

- Pierwszy Alert w systemie, oddzielny od Measurement zgodnie z rule #7.
- `severity_raw` jako string oznacza, że UI/dalsza logika musi świadomie
  zdecydować jak interpretować różne skale (meteo vs hydro) — świadomy koszt,
  nie przeoczenie.
- Do czasu decyzji o geo-matching, mobile dostaje surową listę krajową — mniej
  użyteczne niż docelowo, ale prawdziwe dane, nie fabrykowane dopasowanie "na oko".
