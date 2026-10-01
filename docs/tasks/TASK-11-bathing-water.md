# TASK 11.1 / 11.2 — Kąpieliska: research źródła i connector (ZABLOKOWANE)

Decyzja i wyniki researchu: `docs/architecture/ADR-021-bathing-water-source.md`.
Wpisy źródeł: `docs/data/source-registry.md` (`gis_bathing_sk`, `eea_bathing_water`).

## Goal

Dostarczyć użytkownikowi dane §7 Master Planu (status, przydatność, E. coli,
enterokoki, sinice, zamknięcie + powód, daty badań, sezon, lokalizacja) z
oficjalnego, dozwolonego źródła, bez zgadywania (rule #10, #15).

## Scope

- **11.1 (zrobione):** research źródeł, ADR-021, wpisy w registry.
- **11.2 (ZABLOKOWANE):** connector `app/connectors/<nazwa>/` (fetch/parse/
  validate/normalize), modele `BathingSite` + klasyfikacja/status (rule #7),
  migracja Alembic (nowy head po PR-ach w toku), scheduler z `source_status`
  (ADR-012), provenance `source_fetch_id` (ADR-014), `GET /api/v1/water/latest`.

## Acceptance Criteria

- [x] ADR-021 z opisem każdego rozważonego źródła i decyzją.
- [x] Registry zawiera wyłącznie fakty zweryfikowane; reszta oznaczona jawnie.
- [ ] Source Approval Gate zaliczony dla wybranego źródła (licencja,
      `commercial_use`, atrybucja, cykl, schemat na prawdziwej próbce).
- [ ] Parser testowany na fixture z POTWIERDZONYCH pól (oznaczony jako fixture).
- [ ] `/water/latest`: `source` + `attribution` z registry, freshness,
      `source_status`; brak bieżącego statusu => `UNAVAILABLE`, nigdy „dopuszczone".

## Blokada — co musi zrobić człowiek

1. Napisać do GIS (właściciel `sk.gis.gov.pl`) z prośbą o: udokumentowany
   eksport/API, pisemną zgodę na automatyczne pobieranie, warunki licencji i
   `commercial_use`, atrybucję, limit żądań i współrzędne/TERYT kąpielisk.
2. W przeglądarce potwierdzić licencję wydania 2025 i schemat pliku EEA (Datahub, metadata factsheet), pola usługi `BathingWater_Dyna_WM_2025` i filtr `countryName=Poland`
3. Ręcznie sprawdzić portal dane.gov.pl pod kątem zbioru o kąpieliskach.
4. Po 1–3 — zatwierdzić źródło; wtedy zadanie można wznowić jako osobny PR.

## Tests

Do zaprojektowania po odblokowaniu (parser, ingest, endpoint, scheduler,
freshness, provenance — wzorzec `imgw_hydro`).

## Non-goals

Mobile (11.5), agregat dashboard (11.6), alert zamknięć (11.3), własny geo-matching
(TASK-6.2), scraping HTML GIS bez zgody.

## Dependencies

Zgoda/dane od GIS lub potwierdzona licencja EEA; ADR-009, ADR-012, ADR-014, TASK-6.2.

## Data Contract

Nie zdefiniowany — zależy od zatwierdzonego źródła. Kierunek: ADR-021 pkt 2–3.

## Security

Brak sekretów; publiczne źródła. LLM nie klasyfikuje statusu ani zamknięć.

## Architecture Impact

ADR-021 (Proposed). Bez zmian w kodzie i schemacie bazy w tym PR.
