# TASK 9.2 — IMGW ostrzeżenia meteorologiczne: zablokowane na weryfikacji

> Aktualizacja 2026-10-03: blokada braku aktywnej fixture zamknięta. Rzeczywisty payload
> jest w `docs/data/imgw/evidence/warningsmeteo.json`. Parser/ingest/API/scheduler/exact
> county matching zaimplementowane pod flagą (ADR-034); strefa czasu/approval/rollout
> nadal pending. Poniższy opis zachowuje historyczny zakres TASK-9.2 z PR #38.


## Goal

Drugi connector Alert (obok `imgw_warningshydro`, ADR-009) — ostrzeżenia
meteorologiczne. Celowo NIE dokończony w tym tasku — patrz Non-goals.

## Scope

- `client.py`: fetch + retry, ten sam wzorzec co `imgw_warningshydro` (rule #5).
- `parser.py::parse_warnings()`: dispatch top-level kształtu (lista / pusty
  `{"message": ...}` / błąd) — zweryfikowany na żywo dla stanu pustego.
- **NIE zaimplementowane**: `normalize()`, `ingest.py`, rozszerzenie
  `GET /api/v1/alerts/latest`, wpięcie do schedulera.

## Acceptance Criteria

- [x] `client.fetch_warnings()` zwraca surowy payload, retry raz przy błędzie
      (test: `test_fetch_warnings_retries_once_then_succeeds`).
- [x] `parse_warnings()` poprawnie obsługuje zweryfikowany pusty kształt
      (test: `test_treats_message_dict_as_zero_warnings`).
- [x] `parse_warnings()` odrzuca nieznany kształt zamiast zgadywać (rule #10).
- [ ] `normalize()` — ZABLOKOWANE: brak żywego przykładu aktywnego ostrzeżenia
      meteo w chwili implementacji (API zwracało tylko stan pusty). Nieoficjalne
      źródła trzecie sugerują inny schemat pól niż `warningshydro` (`id`,
      `stopien` 1–3, `tresc`, `teryt[]`), ale to niezweryfikowane na żywo —
      rule #10 zabrania zgadywania kształtu danych bezpieczeństwa, rule #15
      wymaga realnej weryfikacji przed użyciem źródła. Decyzja użytkownika
      (2026-09-29): poczekać na realny przykład zamiast budować na domysłach.

## Tests

`apps/api/tests/connectors/test_imgw_warningsmeteo_{client,parser}.py`.

## Non-goals (tego taska)

- `normalize()`/`ingest.py`/endpoint/scheduler dla `imgw_warningsmeteo` —
  do dokończenia w kolejnym tasku, gdy pojawi się i zostanie zaobserwowane
  żywe, aktywne ostrzeżenie meteo (albo IMGW opublikuje oficjalny schemat).
  Sposób wznowienia: sprawdzić `https://danepubliczne.imgw.pl/api/data/warningsmeteo`
  podczas realnego ostrzeżenia (np. burze/upały latem, śnieg/mróz zimą),
  zapisać dokładny JSON, zaktualizować `parser.py::normalize()` analogicznie
  do `imgw_warningshydro`, dopisać `ingest.py`, rozszerzyć `/alerts/latest`.

## Dependencies

Brak nowej migracji — docelowo reużyje modelu `Alert` z ADR-009
(`source_id="imgw_warningsmeteo"`).

## Data Contract

Brak — `normalize()` nie istnieje. Docelowo analogiczny do `imgw_warningshydro`
po potwierdzeniu realnych nazw pól.

## Security

Brak nowych sekretów. Brak klucza API (publiczny endpoint).

## Architecture Impact

Brak nowej decyzji architektonicznej — kontynuacja wzorca z ADR-009
(defensywna obsługa pustego kształtu, `Alert` jako oddzielny model od
Measurement). Nie wymaga nowego ADR.
