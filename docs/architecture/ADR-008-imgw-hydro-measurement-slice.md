# ADR-008: IMGW hydro (stan wody) jako druga Measurement vertical slice; ostrzeżenia odłożone

**Status:** Accepted
**Data:** 2026-09-29

## Context

Master Plan §8 (Hydrologia) i §9 (Alerty) chcą obu: poziomu wody na stacjach i
ostrzeżeń hydrologicznych. IMGW-PIB (`danepubliczne.imgw.pl`) udostępnia oba jako
osobne, jednorazowo weryfikowane (2026-09-29, WebFetch na żywe endpointy) API:

- `GET /api/data/hydro/` — lista WSZYSTKICH stacji hydrologicznych w jednym
  wywołaniu (bez paginacji, bez per-stacja drugiego zapytania jak w GIOŚ), z
  `lat`/`lon` wprost w payloadzie: `id_stacji`, `stacja`, `rzeka`, `lat`, `lon`,
  `stan_wody`, `stan_wody_data_pomiaru`, `stan_alarmowy`, `stan_ostrzegawczy`
  (progi, mogą być `null`).
- `GET /api/data/warningshydro` — lista aktywnych ostrzeżeń: `stopień`, `data_od`,
  `data_do`, `prawdopodobieństwo`, `zdarzenie`, `obszary[].wojewodztwo` — gdy brak
  ostrzeżeń meteo, `warningsmeteo` zwraca **obiekt** `{"message": "Brak..."}**,
  nie pustą listę (zweryfikowany, nie zgadywany kształt "pustego" stanu — do
  potwierdzenia że `warningshydro` zachowuje się tak samo, zanim ktokolwiek to
  parsuje).

**Licencja** (regulamin `danepubliczne.imgw.pl/apiinfo`, zweryfikowany na żywo):
użytek niekomercyjny/prywatny bezpłatny; komercyjny wymaga płatnej umowy (poza
"danymi wysokiej wartości"). Wymagana atrybucja: *"Źródłem pochodzenia danych jest
Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy"* (+ dopisek
o przetworzeniu, jeśli dane są modyfikowane). Brak jawnego rate limitu w regulaminie.

## Problem

1. Stan wody (Measurement) i ostrzeżenia (Alert, rule #7 — nie mieszać pojęć) to
   dwie różne rzeczy w modelu danych. Robienie obu naraz podwaja zakres jednego
   PR-a i miesza dwie decyzje architektoniczne w jednym ADR.
2. Licencja jest analogiczna do Open-Meteo (ADR-003): darmowy tier tylko
   niekomercyjnie.
3. Częstotliwość odświeżania stacji hydro **nie jest udokumentowana** przez IMGW
   (sprawdzone: brak w regulaminie/apiinfo) — rule #16 wymaga zweryfikowanego
   cyklu, nie zgadywanego "na wszelki wypadek".

## Decision

**Ten ADR obejmuje wyłącznie stan wody (Measurement).** Ostrzeżenia hydrologiczne
(`warningshydro`) to osobny, przyszły task z własnym ADR — wymaga nowego modelu
`Alert` (nie ma go jeszcze w kodzie), którego Master Plan §32 nie precyzuje
wystarczająco, żeby projektować go "przy okazji".

- Connector `imgw_hydro`: jedno wywołanie `GET /api/data/hydro/` zwraca WSZYSTKIE
  stacje — brak potrzeby per-stacja fetchowania ani throttlingu jak w GIOŚ.
- Dane trafiają do **istniejącej** tabeli `measurements` (rule: nie tworzyć nowego
  modelu, gdy istniejący pasuje) — `param_code="water_level_cm"`, `unit="cm"`
  (standardowa jednostka `stanu wody` w polskiej hydrologii), `source_id="imgw_hydro"`.
  Nie koliduje z `/api/v1/air/latest` ani z dashboardem — oba filtrują jawnie po
  `param_code == "PM2.5"`.
- Analogicznie do ADR-003 (Open-Meteo): licencja niekomercyjna jest dziś zgodna z
  regułą "brak monetyzacji" (CLAUDE.md, ADR-003) — **rewizja wymagana przed**
  jakąkolwiek monetyzacją, dokładnie ten sam trigger co w ADR-003.
- Częstotliwość: **nieznana z dokumentacji**, przyjmujemy roboczo co 1h (jak GIOŚ,
  ta sama domena danych rządowych) — jawnie oznaczone jako założenie startowe do
  weryfikacji przy pierwszym realnym uruchomieniu (ten sam wzorzec co Open-Meteo w
  Source Registry), nie twarda, zweryfikowana wartość.
- Nowy `/api/v1/hydro/latest`, ten sam kształt co `/air/latest` (freshness,
  źródło, brak agregacji po stronie API — rule #14).

**Explicit non-goals:**
- `warningshydro`/`warningsmeteo` (Alert model) — osobny task.
- Geo-matching stacji hydro do `geo_areas` (dashboard) — nie dziś, ten sam powód
  co przy GIOŚ: jeden connector na raz, potem integracja.
- `stan_alarmowy`/`stan_ostrzegawczy` (progi alarmowe stacji) jako Alert — to
  metadane stacji, nie Alert; mogą zasilić przyszły Alert Engine, nie teraz.

## Consequences

- Druga, w pełni działająca Measurement vertical slice, zero nowej migracji.
- `imgw_hydro` musi zostać osobno zrewidowany w Source Registry przed rewizją
  monetyzacji (jak `open_meteo`).
- Częstotliwość fetchowania (1h) może się zmienić po pierwszej żywej weryfikacji —
  zaakceptowany koszt, nie przeoczenie (ten sam wzorzec co przy `open_meteo`).
- Ostrzeżenia hydrologiczne/meteo zostają w Source Registry jako DISCOVERY dla
  samego typu danych Alert, mimo że endpoint API jest już zweryfikowany — bo to co
  brakuje, to model danych po naszej stronie, nie dostęp do źródła.
