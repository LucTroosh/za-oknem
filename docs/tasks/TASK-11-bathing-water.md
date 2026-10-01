# TASK 11.1 / 11.2 — Kąpieliska: research źródła i connector (ZABLOKOWANE)

Decyzja i wyniki researchu: `docs/architecture/ADR-021-bathing-water-source.md`.
Wpisy źródeł: `docs/data/source-registry.md` (`gis_bathing_sk`, `eea_bathing_water`).

## Goal

Dostarczyć użytkownikowi dane §7 Master Planu (status, przydatność, E. coli,
enterokoki, sinice, zamknięcie + powód, daty badań, sezon, lokalizacja) z
oficjalnego, dozwolonego źródła, bez zgadywania (rule #10, #15).

## Scope

- **11.1 (CZĘŚCIOWE/ZABLOKOWANE):** research źródeł, ADR-021 i wpisy w registry
  zrobione; Source Approval Gate NIEZALICZONY dla żadnego źródła (patrz AC).
- **11.2 (ZABLOKOWANE):** connector `app/connectors/<nazwa>/` (fetch/parse/
  validate/normalize), modele `BathingSite` + klasyfikacja/status (rule #7),
  migracja Alembic (nowy head po PR-ach w toku), scheduler z `source_status`
  (ADR-012), provenance `source_fetch_id` (ADR-014). Endpoint
  `GET /api/v1/water/latest` (freshness, nearest-site) należy do TASK-11.4.

## Acceptance Criteria

- [x] ADR-021 z opisem każdego rozważonego źródła i decyzją.
- [x] Registry zawiera wyłącznie fakty zweryfikowane; reszta oznaczona jawnie.
- [ ] Model `BathingSite` niesie współrzędne ORAZ `geo_area_id`/gmina (wymóg BACKLOG 11.2,
      potrzebny dla TASK-11.3); mapowanie do gminy przez TASK-6.2, bez własnego geo.
- [ ] Pełny Source Approval Gate (Master Plan §38, 12 punktów: dostępność API,
      stabilność, regulamin, licencja, `commercial_use`, redystrybucja, caching,
      limity, atrybucja, niezawodność, użycie mobilne, dane osobowe) zaliczony i
      zapisany w registry dla KAŻDEGO źródła wybranego do implementacji (nie dla
      kandydatów niewybranych), plus schemat/pola
      potwierdzone na prawdziwej próbce, a status registry =
      APPROVED (VERIFIED nie wystarcza). Samo istnienie zbioru (np. na dane.gov.pl) nie wystarcza.
- [ ] Parser testowany na fixture z POTWIERDZONYCH pól (oznaczony jako fixture).

## Blokada — co musi zrobić człowiek

Wystarczy jedna ścieżka; kroki 2–3 dotyczą tylko źródeł wybranych do użycia.

1. Jeśli wybrana ma być ścieżka GIS: napisać do GIS (właściciel `sk.gis.gov.pl`) z prośbą o: udokumentowany
   eksport/API, pisemną zgodę na automatyczne pobieranie, warunki licencji i
   `commercial_use`, atrybucję, limit żądań i współrzędne/TERYT kąpielisk.
2. Jeśli wybrane ma być EEA (tylko rejestr + klasyfikacja roczna): potwierdzić
   licencję wydania 2025, schemat xlsx, pola `BathingWater_Dyna_WM_2025`, filtr
   `countryName=Poland` i limit żądań EEA.
3. Opcjonalnie sprawdzić dane.gov.pl i WIOŚ/wojewódzkie jako dodatkowe kandydaty.
4. Dla wybranego źródła przeprowadzić pełny Gate §38 (AC wyżej), zatwierdzić je
   i wznowić zadanie jako osobny PR.

## Tests

Do zaprojektowania po odblokowaniu (parser, ingest, endpoint, scheduler,
freshness, provenance — wzorzec `imgw_hydro`).

## Non-goals

Mobile (11.5), agregat dashboard (11.6), alert zamknięć (11.3), własny geo-matching
(TASK-6.2), scraping HTML GIS bez zgody.

## Dependencies

TASK-11.3 (alert zamknięć), 11.4 (`/water/latest`; jego kryteria — `source`+`attribution`,
freshness, `source_status`, `UNAVAILABLE` zamiast „dopuszczone" przy braku statusu
bieżącego — zostają w BACKLOG/11.4, nie w tym dokumencie), 11.5, 11.6 zależą od 11.2, więc
są pośrednio ZABLOKOWANE do czasu zaliczenia Gate.

Zgoda/dane od GIS (EEA samo NIE odblokowuje 11.2 w pełnym zakresie: nie ma statusu
bieżącego, przyczyny zamknięcia ani pomiarów — może odblokować tylko rejestr
lokalizacji + klasyfikację roczną po potwierdzeniu licencji i limitu); ADR-009, ADR-012, ADR-014, TASK-6.2.

## Data Contract

Nie zdefiniowany — zależy od zatwierdzonego źródła. Kierunek: ADR-021 pkt 2–3.

## Security

Brak sekretów; publiczne źródła. LLM nie klasyfikuje statusu ani zamknięć.

## Architecture Impact

ADR-021 (Proposed). Bez zmian w kodzie i schemacie bazy w tym PR.
