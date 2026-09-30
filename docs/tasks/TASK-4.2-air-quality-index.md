# TASK 4.2 — Indeks jakości powietrza: zablokowane na weryfikacji

## Goal

Indeks ogólny oraz indeksy cząstkowe per zanieczyszczenie w `/api/v1/air/latest`,
`dashboard_latest()` i na mobile (Home). Decyzja A/B: ADR-015.

## Scope (tego PR)

- ADR-015 (fakty zweryfikowane vs. niezweryfikowane, opcje, rekomendacja).
- **NIE zaimplementowane**: jakikolwiek kod indeksu, migracja, zmiany API/mobile.

## Acceptance Criteria (docelowe)

- [ ] Indeks ogólny = najgorszy z cząstkowych (zweryfikowane u GIOŚ).
- [ ] Indeks cząstkowy per parametr w `AirParam`; ogólny per stacja; oba w dashboard.
- [ ] Etykiety dosłownie: Bardzo dobry / Dobry / Umiarkowany / Dostateczny / Zły /
      Bardzo zły / Brak indeksu; badge z tekstem, nie tylko kolorem.
- [ ] Freshness/`observed_at` z danych wejściowych; „Brak indeksu” tylko gdy GIOŚ tak zwraca; brak wiersza/nieudany fetch → UNAVAILABLE (ADR-012).
- [ ] (B) progi dosłownie z oficjalnej tabeli + URL + data; testy na granicach
      (lewostronnie otwarte, prawostronnie domknięte). (A) parser v1 `getIndex`
      oparty na zaobserwowanym żywym JSON + testy.
- [ ] `aqi.ts` + `aqi.test.ts`; `index.tsx` tylko renderowanie.

## Tests

Do dodania po odblokowaniu: `apps/api/tests/test_air.py`, `test_dashboard.py`
(kolejność zapytań fake sessions), `apps/mobile/app/aqi.test.ts`.

## Non-goals

Zgadywanie progów lub kształtu odpowiedzi; LLM (rule #10). `ROADMAP.md` aktualizuje koordynator po merge: wiersz indeksu powietrza -> BLOCKED (warunek odblokowania: sekcja „Jak odblokować”).

## Dependencies

TASK-4.1 (DONE). ADR-015 → decyzja. Migracja 0010 tylko dla opcji A.

## Data Contract

Indeks ≠ Measurement (rule #7). Opcja A: snapshot z provenance (rule #6: `source_id`, endpoint, `source_record_id`
stabilny/unikalny np. `station_id:param:source_data_date`, `fetched_at`), `station_id`, klasą per
parametr ORAZ osobnym `source_data_date` per parametr (i dla indeksu ogólnego) +
`fetched_at` — parametry mogą pochodzić z różnych godzin, więc jeden timestamp
na stację pokazałby starszy składnik jako świeży; freshness liczona per parametr. Opcja B: pole wyliczane w odpowiedzi API.

## Security

Brak nowych sekretów; GIOŚ publiczne, limit 1500/min (opcja A).

## Architecture Impact

A: nowa tabela + connector call + wpis w source-registry. B: brak zmian schematu.

## Jak odblokować

Podać żywy JSON `aqindex/getIndex/<id>` (A) albo przepisać tabelę progów z
<https://powietrze.gios.gov.pl/pjp/content/health_informations> (B).
