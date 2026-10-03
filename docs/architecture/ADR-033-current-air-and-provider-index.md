# ADR-033: Bieżące powietrze i osobny indeks GIOŚ

Status: Proposed (do przyjęcia z PR). Data: 2026-10-03.

## Decyzja

Misja „Co dzieje się u Ciebie za oknem”: bieżące pomiary, prognoza i krótka historia.
Zbiory historyczne/rejestry z PR #134 pozostają on hold. Istniejący hałas zostaje w kodzie,
z wyłączoną domyślnie flagą; finalny UI powstaje po przekazaniu danych Design Leadowi.

- Zachowujemy 7 mierzonych parametrów i ich jednostki µg/m³ (także CO), czas każdego
  odczytu, brak = brak, nigdy zero. Nie wszystkie stacje mierzą wszystkie parametry.
- Jeden wybór stacji dla dashboardu, `/air/latest`, `/air/history` i `/air/provider-index`:
  najbliższa w promieniu ≤100 km z co najmniej jednym poprawnym, nie starszym niż 6 h
  pomiarem; gdy takich brak, najbliższa z wcześniejszymi danymi, jawnie STALE. Nadal
  obowiązują katalog/override z ADR-025, pasma z ADR-029 i wyłączenie regional z werdyktu.
- Nie mieszamy parametrów różnych stacji. Odczyt w przyszłości nie jest bieżącym pomiarem.
  Najnowszy odczyt per stacja/parametr wybiera SQL `row_number`; remis = najmniejsze id,
  tak samo jak historia. Historia pozostaje pomiarami, z lukami i bez interpolacji.
- Indeks dostawcy ma własną skalę `POLISH_AIR_QUALITY_INDEX`, kategorie 0–5, etykietę
  dokładnie ze źródła, indeksy cząstkowe SO2/NO2/PM10/PM2.5/O3 oraz flagę statusu.
  Nie jest Measurement ani liczonym u nas indeksem EEA; istniejący EAQI i Outdoor bez zmian.
- Migracja 0019: jeden snapshot indeksu per stacja plus stan ostatniej próby; raw fetch
  przez istniejące provenance. Błąd zachowuje snapshot i ustawia degraded, poprawny brak
  indeksu zastępuje poprzedni wynik. Brak klucza nie jest równoważny jawnemu null.
- Pobieranie w istniejącym godzinowym ingest: +1 request na stację; indeks nie zmienia
  sukcesu/porażki pobierania pomiarów. Flaga `GIOS_PROVIDER_INDEX_ENABLED=false` do
  rollout po migracji. API zawsze czyta bazę, nigdy nie odpytuje GIOŚ per użytkownik.
- Aktualność indeksu wynika z daty danych źródłowych, nie obliczenia/pobrania. Czasy
  lokalne Europe/Warsaw normalizujemy do UTC; nierozstrzygalna lub nieistniejąca godzina
  DST odrzucana. Przyszłość >5 min od pobrania odrzucana (tolerancja zegara, nie SLA).

## Dowód i ograniczenia

Rzeczywiste odpowiedzi stacji 52 i 11: `docs/data/gios/evidence/air-live/`.
Metadane odpowiedzi deklarują hourly, format lokalny; oficjalna strona API podaje
1500/min dla indeksu, endpoint `/v1/rest/aqindex/getIndex/{stationId}`. Nullable indeksy
cząstkowe potwierdzone dla stacji 11. Brak ogólnego indeksu i awarie sprawdzone na
syntetycznych fixture, nie udawanych próbach live. Nie przesądza to jakości pomiarów.

Brak nowej zależności, providera, pollingu rejestrów rocznych i nowej zakładki. Wybór
na podstawie jednego użytecznego parametru nie oznacza pełnego AQI — kompletność EAQI
nadal wyznacza ADR-015. API indeksu zwraca no_station, jeśli brak stacji z pomiarami,
nawet gdy sam rejestr indeksu ma rekord: spójna stacja ma pierwszeństwo.
