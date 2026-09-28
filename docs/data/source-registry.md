# Source Registry (starter)

Format wg §37 Master Planu. Status: DISCOVERY → VERIFIED → APPROVED → IMPLEMENTED →
PRODUCTION, alternatywnie BLOCKED. Uzupełniać przy każdym nowym connectorze
(Source Approval Gate, §38) — nie zaczynać implementacji connectora bez wpisu tutaj.

## open_meteo

- **owner:** OpenMeteo GmbH (Szwajcaria)
- **connector:** `open_meteo`
- **endpoint:** api.open-meteo.com (forecast + air-quality)
- **frequency:** wg ADR-001 (snapshot per aktywna gmina) + ADR-004 (częstotliwość =
  rzeczywisty cykl aktualizacji źródła). **Nie zweryfikowany jeszcze** dokładny cykl
  odświeżania modelu pogodowego Open-Meteo — do potwierdzenia przed implementacją w
  Phase 5 (sprawdzić dokumentację, nie zakładać "co godzinę" bez sprawdzenia).
- **coverage:** globalne, w tym Polska
- **license:** CC BY 4.0 (atrybucja wymagana)
- **commercial_use:** NIE na darmowym tierze — patrz ADR-003. Rewizja wymagana przed
  jakąkolwiek monetyzacją.
- **redistribution:** dozwolona pod CC BY 4.0 z atrybucją
- **caching:** wymagany snapshot w bazie (ADR-001), zero zapytań on-demand per użytkownik
- **rate_limit:** 600/min, 5000/h, 10000/dzień, 300000/miesiąc (darmowy tier)
- **attribution:** "Weather data by Open-Meteo.com (CC BY 4.0)" — wymagane w ekranie Źródła
- **status:** VERIFIED (licencja i limity sprawdzone 2026-09-28; nie zaimplementowany)
- **last_verified_at:** 2026-09-28

## cams_ads (Copernicus Atmosphere Data Store — pyłki, CAMS Air)

- **owner:** ECMWF / Copernicus (Unia Europejska)
- **connector:** `cams` (do zaprojektowania — inny kształt niż API pogodowe: pobranie
  pliku NetCDF/GRIB dla wycinka Polski, nie zapytanie per-punkt)
- **endpoint:** ads.atmosphere.copernicus.eu (wymaga rejestracji, klucz API)
- **frequency:** raz dziennie (prognoza pyłków aktualizowana raz/dzień, 4 dni naprzód) —
  zgodne z ADR-004, fetch nie częściej niż ten cykl
- **coverage:** Europa, w tym Polska (tylko powierzchnia, brak pionowego profilu)
- **license:** dane opisane przez Copernicus jako dostępne bez ograniczeń użycia,
  wymagana widoczna atrybucja programu Copernicus (Licence to Use Copernicus Products)
- **commercial_use:** TAK (bez ograniczeń wg dokumentacji Copernicus) — do potwierdzenia
  przy pełnym Source Approval Gate przed Phase 8
- **redistribution:** wymaga atrybucji Copernicus przy każdej publikacji danych
- **caching:** snapshot dzienny w bazie, tak jak weather (ADR-001)
- **rate_limit:** nieznany dokładnie — UNKNOWN, sprawdzić przy implementacji (Phase 8)
- **attribution:** "Contains modified Copernicus Atmosphere Monitoring Service
  information" — wymagane
- **status:** DISCOVERY (licencja wstępnie sprawdzona, techniczny kształt API nie
  zweryfikowany)
- **last_verified_at:** 2026-09-28

## gios (GIOŚ — jakość powietrza, stacje pomiarowe)

- **owner:** Główny Inspektorat Ochrony Środowiska (Polska, instytucja publiczna)
- **connector:** `gios`
- **endpoint:** `https://api.gios.gov.pl/pjp-api/v1/rest/` — `/station/findAll`,
  `/station/sensors/{stationId}`, `/data/getData/{sensorId}`, `/aqindex/getIndex/{stationId}`.
  Starsze endpointy bez `/v1/` wycofane 30.06.2025 — potwierdzone w dokumentacji GIOŚ
  (nie zgadywane).
- **frequency:** nie zweryfikowana co do rzeczywistego cyklu publikacji nowych pomiarów
  stacji (zgodnie z ADR-004 — do ustalenia przed produkcyjnym schedulerem, nie blokuje
  jednorazowego/manualnego ingestu na tym etapie)
- **coverage:** Polska (sieć stacji GIOŚ, liczba i lokalizacje zmienne)
- **license:** dane publiczne sektora publicznego — wymagane "jasne i wyraźne wskazanie
  źródła" przy republikacji (cytat z dokumentacji GIOŚ)
- **commercial_use:** brak jawnego zakazu w znalezionej dokumentacji — do potwierdzenia
  przy pełnym Source Approval Gate przed produkcją
- **redistribution:** dozwolona z atrybucją źródła
- **caching:** zgodnie z regułą #14 (CLAUDE.md) — mobile API czyta wyłącznie z naszej
  bazy, nigdy nie woła GIOŚ na żądanie użytkownika
- **rate_limit:** 2 zapytania/min (endpointy standardowe, np. listy stacji),
  1500 zapytań/min (dane bieżące i indeks jakości powietrza) — wg dokumentacji GIOŚ
- **attribution:** "Dane: Główny Inspektorat Ochrony Środowiska (GIOŚ)" — wymagane w
  ekranie Źródła
- **status:** VERIFIED (endpoint, limity i wymóg atrybucji potwierdzone w oficjalnej
  dokumentacji 2026-09-28). **Kształt JSON odpowiedzi NIE zweryfikowany na żywo** —
  sandbox, w którym pisany był connector, nie miał dostępu sieciowego do tego hosta.
  Parser oparty na udokumentowanym, stabilnym schemacie tego API — wymaga potwierdzenia
  jednym realnym wywołaniem przed oznaczeniem jako APPROVED.
- **last_verified_at:** 2026-09-28

## imgw

- **status:** DISCOVERY — do weryfikacji przy rozszerzaniu o hydrologię/ostrzeżenia
  (Phase 9/11). Nie blokuje pierwszego vertical slice (GIOŚ → PM2.5).
