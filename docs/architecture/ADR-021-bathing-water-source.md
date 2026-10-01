# ADR-021: Źródło danych o kąpieliskach (Phase 11)

- **Date:** 2026-10-01
- **Status:** Proposed (implementacja ZABLOKOWANA na Source Approval Gate — patrz Decision)

## Context

Master Plan §7 (Woda) wymaga w MVP: status kąpieliska, przydatność do kąpieli,
E. coli, enterokoki, sinice, zamknięcie + powód, daty ostatniego/następnego
badania, sezon, lokalizację. To dane bezpieczeństwa (CLAUDE.md #10, #15):
nie zgadujemy kształtu danych, nie scrapujemy bez zgody, LLM nie jest źródłem prawdy.

## Problem

Czy istnieje oficjalne, stabilne, legalnie użyteczne źródło pobieralne
programowo? Wynik researchu 2026-10-01 (WebFetch/WebSearch; `curl` z tego
środowiska nie ma egressu — nie obchodzono proxy). Streszczenia stron robił
model pomocniczy — traktować jako wskazówki do potwierdzenia, nie cytaty.

### (a) Serwis Kąpieliskowy GIS — `sk.gis.gov.pl`
- **Korekta opisu blokady z BACKLOG:** `/kapieliska` jest renderowane po stronie
  serwera (HTML, lista ok. 718 kąpielisk: nazwa, adres, powiat/województwo, daty
  sezonu, „woda przydatna do kąpieli", data ostatniego badania, klasyfikacja
  2025–2026). Nie jest to czysta aplikacja JS.
- Strona kąpieliska (`/index.php/kapielisko/{id}`) pokazuje: datę oceny, status
  wody, E. coli i enterokoki (jtk/100 ml), datę kolejnego badania, próg
  (E. coli 1000, enterokoki 400), akwen, sezon, klasyfikację. W pobranej treści
  nie widać współrzędnych ani TERYT.
- **Brak** udokumentowanego API, eksportu CSV/XML, linku do otwartych danych ani
  regulaminu/licencji (stopka: deklaracja dostępności, klauzula informacyjna,
  cookies; `/informacje` — bez warunków ponownego wykorzystania).
- Częstotliwość: wg gov.pl min. 3 badania w sezonie, odstęp maks. miesiąc,
  pierwsze nie wcześniej niż 10 dni przed otwarciem. Dane z sezonu, nie strumień.
- Wniosek: jedyne źródło **bieżącego** statusu, ale wyłącznie jako HTML bez
  warunków użycia. Scraping = niestabilny kontrakt + brak zgody (rule #15).

### (b) dane.gov.pl
- Nie zweryfikowano: `api.dane.gov.pl` / wyszukiwarka zwróciły błąd uprawnień
  narzędzia. Wyszukiwanie WWW nie wskazało zbioru GIS o kąpieliskach. gov.pl
  (strona GIS o jakości wody) nie wspomina o otwartych danych/API.
  **Status: NIEZWERYFIKOWANE** — do sprawdzenia ręcznie.

### (c) EEA — Bathing Water Directive, status of bathing water
- Zbiór roczny (publikacja 2026-06-02, pokrycie 1990–2025), pobranie jako
  Excel (.xls/.xlsx) z EEA Datahub; klasyfikacja sezonowa, NIE status bieżący.
- Usługa ArcGIS `marine.discomap.eea.europa.eu/arcgis/rest/services/BathingWater/BathingWater_Dyna_WM_2018/MapServer`:
  warstwa 0 (punkty) ma pola `monitoringSiteIdentifier`, `bathingWaterName`,
  `countryName`, `bwWaterCategory`, `latitude`, `longitude`,
  `monitoringCalendarStatus`, `managementStatus`, `qualityStatus`,
  `qualityStatus_minus1..10`, `bwProfileLink`; formaty JSON/geoJSON/PBF,
  `maxRecordCount` 1000. Copyright usługi: „EEA, Bathing waters data and
  coordinates: Member states authorities". Wg wyników wyszukiwania istnieje też
  nowsza usługa `..._2024` — nie sprawdzono, która jest aktualna.
- **Niezweryfikowane:** licencja aktualnego zbioru/usługi (strona datahubu jej
  nie podała; rekord z 2011 ma CC BY 4.0, ale to inny rekord), schemat pliku
  xlsx, czy filtr po kraju działa, stabilność URL usługi, rate limit.
- Wniosek: wiarygodny rejestr lokalizacji (id, nazwa, WGS84) + roczna
  klasyfikacja; nie daje przydatności, przyczyny zamknięcia, E. coli,
  enterokoków, sinic ani dat badań.

### (d) Wojewódzkie serwisy / WIOŚ
Nie badano — brak czasu sesji (limit narzędzi). Nie ma podstaw, by zakładać, że
cokolwiek z tego jest programowo dostępne.

## Options

1. Scraping HTML `sk.gis.gov.pl` — odrzucone (brak zgody i warunków, rule #15).
2. EEA jako rejestr + klasyfikacja roczna — kandydat, ale Gate niezaliczony
   (licencja i schemat niezweryfikowane) — nie implementujemy na domysłach.
3. dane.gov.pl — niezweryfikowane.
4. Zgoda/kontakt z GIS na eksport lub API — jedyna droga do statusu bieżącego.

## Decision

1. **Nie implementujemy connectora w tym PR.** Żadne źródło nie przeszło Source
   Approval Gate; wpisy w registry mają status DISCOVERY/BLOCKED.
2. Kierunek modelu (do potwierdzenia przy implementacji, rule #7):
   `BathingSite` (obiekt: id źródła, nazwa, WGS84, kategoria wody) oddzielony od
   `BathingWaterClassification` (per sezon — ocena roczna) oraz, po zgodzie GIS,
   `BathingWaterStatus` (pomiar/ocena z datą) ≠ Alert zamknięcia (TASK-11.3,
   ADR-009).
3. **Brak bieżącego statusu ≠ „dopuszczone".** API/mobile pokażą
   `current_status: UNAVAILABLE` („brak danych o bieżącym statusie"); roczna
   klasyfikacja nigdy nie jest prezentowana jako przydatność do kąpieli dziś (rule #8).
4. Po odblokowaniu: freshness przez `source_status` (ADR-012), provenance
   ADR-014, fetch wg realnego cyklu (rule #16).

## Consequences

- TASK-11.2–11.6 pozostają zablokowane; żaden kod, migracja ani endpoint nie
  powstaje na zgadywaniu. Numer migracji 0013 zostaje wolny.
- Rozstrzygnięcie wymaga człowieka (lista w `docs/tasks/TASK-11-bathing-water.md`).
- Jeśli GIS zgodzi się na eksport, ten ADR zostanie zaktualizowany
  (Status → Accepted), bez zmiany zasad z pkt 3.
