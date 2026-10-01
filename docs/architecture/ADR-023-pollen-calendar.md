# ADR-023: Kalendarz pylenia jako statyczne dane referencyjne

- **Date:** 2026-10-01
- **Status:** Accepted

## Context

Decyzja właściciela: dodatkowy feature „kalendarz pylenia" — aplikacja pokazuje na podstawie
bieżącej daty, co w danym okresie potencjalnie uczula. ADR-020 daje prognozę modelową CAMS
(`pollen_snapshots`, 5 gatunków, tylko Europa/siatka 0,1°); jest to prognoza, nie pomiar
(rule #7). Rzeczywiste pomiary (OBAŚ) są kandydatem bez API i licencji (source-registry).
ADR-022: free-first, zero płatnych źródeł.

## Problem

1. Jak pokazać „typowy sezon" bez udawania pomiaru ani prognozy (rule #7)?
2. Skąd dane, żeby były wiarygodne i legalne (rule #15), bez kopiowania cudzych tabel?
3. Gdzie je trzymać (rule #14: API czyta tylko z naszych danych)?

## Options

1. **Wiersze w PostgreSQL (migracja Alembic).** Zbędne: dane są stałe, wersjonowane razem z
   kodem, nie mają provenance per fetch. Koszt: migracja, seed, drift.
2. **Pochodna z `pollen_snapshots` (historia CAMS).** Wymaga lat danych, których nie mamy,
   i myli prognozę z klimatologią.
3. **Statyczny plik JSON w repo + walidacja Pydantic (wybrane).** Zero zależności, zero sieci,
   przegląd zmian w PR, testy walidują plik.

## Decision

Opcja 3. `apps/api/app/data/pollen_calendar.json` (ładowany i walidowany przez
`app/pollen_calendar.py`), endpoint `GET /api/v1/pollen/calendar?date=YYYY-MM-DD`
(domyślnie dziś wg Europe/Warsaw; data spoza 2000–2100 lub zła → 422).

- **Nowy byt `SeasonalCalendar`** (referencyjny), osobny od Measurement/Forecast/Event/Alert/
  Notification (rule #7). Odpowiedź ma jawne `kind: "seasonal_calendar"`, `disclaimer`,
  `reviewed_at`, `attribution` i `sources`.
- **Granularność: dekady** (1 = dni 1–10, 2 = 11–20, 3 = 21–koniec miesiąca). Sezon nie
  przechodzi przez przełom roku (walidowane). Okno `peak` musi leżeć w sezonie. Faza:
  `start` (przed szczytem) / `peak` / `end` (po szczycie). `upcoming` = start sezonu w ciągu
  30 dni (z przeniesieniem na następny rok).
- **Zasady danych:** tylko fakty (zakresy dat) z wiarygodnych publikacji, własne zestawienie,
  bez kopiowania tabel/grafik/tekstów; przy rozbieżnościach — konserwatywna suma zakresów
  (opis w `note`); takson bez zweryfikowanego źródła NIE trafia do `taxa`, tylko do
  `not_covered` z powodem. Każdy takson ma ≥1 `source_ids` (walidacja w teście).
- **Klucze** spójne z `pollen_snapshots` tam, gdzie pokrycie istnieje (`alder`, `birch`,
  `mugwort`); `grass` i `ragweed` są w `not_covered` (UNVERIFIED), pozostałe taksony mają
  własne klucze (`hazel`, `ash`, `oak`, `cladosporium`).

## Consequences

- UI **musi** odróżniać trzy warstwy: kalendarz (typowy sezon, ten ADR), prognozę CAMS
  (`/pollen/latest`, `kind: model_forecast`) i — gdy powstanie — pomiary (OBAŚ, osobny
  `source_id` i blok, ADR-022 pkt 5). Kalendarz nigdy nie zasila pól pomiaru/prognozy ani
  odwrotnie; „brak taksonu w kalendarzu" ≠ „nie pyli".
- Zakres jest ogólnopolski i uśredniony; różnice regionalne i roczne rzędu 2–3 tygodni
  (więcej w skrajnych latach) wpisane w `disclaimer`. Brak personalizacji regionalnej.
- Dodanie/zmiana taksonu = zmiana pliku + źródło w `sources` + wpis w source-registry
  (rule #15); część źródeł ma licencję niekomercyjną (CC BY-NC) — używamy wyłącznie faktów,
  ale przed monetyzacją (ADR-003) trzeba je ponownie ocenić.
- Dopisanie traw i ambrozji wymaga zweryfikowania pełnych zakresów (source-registry
  `pollen_calendar`).
