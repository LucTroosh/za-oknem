# ADR-016: Outdoor Interpretation Engine (§52)

**Status:** Accepted
**Data:** 2026-09-30

## Context

Master Plan §52: "dobre warunki do biegania" to wartość DERIVED — temperatura,
opady, wiatr, jakość powietrza i UV przechodzą przez DETERMINISTIC RULES na
`GOOD / MODERATE / POOR` + `reasons[]`. §52/§53 oraz rule #10 zabraniają LLM
przy samej klasyfikacji. Wejścia już mamy: `WeatherSnapshot`
(`temperature_2m`, `apparent_temperature`, `precipitation`, `wind_speed_10m`,
`wind_gusts_10m`, `uv_index`, `visibility`; domyślne jednostki Open-Meteo:
°C, mm, km/h, m) oraz `Measurement` GIOŚ (`PM2.5`, `PM10`, µg/m³). Wpięcie w
`dashboard_latest()` to TASK-7.7, karta mobile to TASK-7.8.

## Problem

1. Gdzie ma żyć silnik i jak go zrobić testowalnym bez DB?
2. Skąd progi — bez udawania, że każdy jest "faktem naukowym"?
3. Co znaczy wynik, gdy brakuje wejść lub są nieświeże (rule #8), żeby brak
   danych nigdy nie dawał cichego `GOOD`?
4. Jaka reguła agregacji czynników?

## Options

- **Lokalizacja:** (a) `app/outdoor.py` — jeden płaski moduł, tak jak
  `app/geo.py`, `app/rate_budget.py`, `app/source_status.py`; (b)
  `app/engines/outdoor.py` — nowy pakiet na jeden plik (YAGNI).
- **Brak danych:** (a) liczyć z tego, co jest, brak ignorować (ciche `GOOD`);
  (b) cały wynik `UNKNOWN`, gdy cokolwiek brakuje (jeden brakujący UV kasuje
  użyteczną ocenę — łamie rule #1 w duchu); (c) **ocena z dostępnych czynników
  + jawne `missing[]`, z podziałem na czynniki rdzeniowe i opcjonalne**.
- **Agregacja:** (a) najgorszy czynnik; (b) suma punktów/wagi (nieprzejrzyste,
  trudne do uzasadnienia, niemonotoniczne przy błędnych wagach).

## Decision

1. **`apps/api/app/outdoor.py`**, czysta funkcja `evaluate(inputs, rules=RULES)`;
   tylko stdlib (dataclass/Enum), zero sqlalchemy/fastapi, zero I/O i zegara.
2. **Najgorszy czynnik wyznacza wynik** (max po wszystkich regułach). Brak
   sumowania: dwa czynniki MODERATE dają MODERATE, nie POOR.
3. **Semantyka braków.** Wejście to `Reading(value, freshness)` lub `None`.
   Użyteczne tylko `FRESH`/`RECENT`; `None`, `STALE`, `UNAVAILABLE`, dowolny inny
   status i wartości nieskończone/NaN (NaN w porównaniach po cichu daje
   `False` → fałszywe GOOD) są traktowane jako brak i trafiają do `missing[]`
   (status `MISSING`/`STALE`/`INVALID`). Nieświeża wartość NIGDY nie wpływa na
   ocenę (rule #8 — nie ma "pewnej oceny" ze starych danych).
   Czynniki rdzeniowe (grupy): `thermal` (apparent lub temperature), `wind`,
   `precipitation`, `air` (PM2.5 lub PM10 — wystarczy jedno). Opcjonalne:
   porywy, UV, widoczność.
   - najgorszy dostępny wynik MODERATE/POOR → ten wynik (zła wiadomość nie jest
     unieważniana brakiem innych danych; `missing[]` mówi, czego brakuje);
   - dostępne czynniki dają GOOD, ale brakuje grupy rdzeniowej → **`UNKNOWN`**;
   - brakuje tylko opcjonalnych → `GOOD` + `missing[]` (UV nocą i tak ≈ 0;
     widoczność/porywy nie są warunkiem bezpieczeństwa sensu stricto);
   - brak wszystkiego → `UNKNOWN`.
   Porządek "dla monotoniczności": `GOOD < UNKNOWN < MODERATE < POOR`
   (`SEVERITY`) — pogorszenie wartości nigdy nie poprawia wyniku; UNKNOWN znaczy
   "nie potwierdzono GOOD".
4. **`reasons[]`**: `{code, param, value, threshold, comparison, unit, level}`
   tylko dla reguł na poziomie MODERATE/POOR; kolejność: POOR przed MODERATE,
   potem kolejność tabeli `RULES` (deterministyczna, niezależna od kolejności
   wejść). `threshold` to przekroczona krawędź, `comparison`
   (`gt|gte|lt|lte`) mówi, jak ją czytać — UI nie zgaduje.
5. **Progi w jednym miejscu** — tabela `RULES` na poziomie modułu, każda reguła
   z polem `basis`. Test pilnuje, że reguła bez "PRODUCT DECISION" ma w `basis`
   datę weryfikacji.
   Zweryfikowane źródła (2026-09-30, WebFetch):
   - PM2.5 >15 → MODERATE, >50 → POOR; PM10 >45 / >120: granice
     European AQI (godzinowe) EEA — Good+Fair / Moderate / Poor+:
     <https://airindex.eea.europa.eu/AQI/index.html> (PM2.5: Fair 6-15,
     Moderate 16-50, Poor 51-90; PM10: Fair 16-45, Moderate 46-120,
     Poor 121-195). Progi EEA są faktem; **przypisanie ich do GOOD/MODERATE/POOR
     dla ćwiczeń na zewnątrz to decyzja produktowa**. Uwaga: 15/45 µg/m³
     pokrywa się z 24h AQG WHO 2021 — potwierdzone tylko wtórnie
     (<https://www.iqair.com/newsroom/2021-who-air-quality-guidelines>);
     strony WHO podają wartości wyłącznie w obrazku, a ekstrakcja jednej z nich
     dała niespójne liczby, więc **nie powołujemy się na WHO jako źródło
     pierwotne**. Wartości godzinowe GIOŚ nie są średnią 24h — przybliżenie.
   - UV ≥6 → MODERATE, ≥8 → POOR: krawędzie kategorii High (6-7) / Very high
     (8-10) globalnego UV Index WHO/WMO/UNEP/ICNIRP:
     <https://www.icnirp.org/en/applications/uv-index/index.html>. Mapowanie
     kategorii na ocenę = decyzja produktowa; nie zaokrąglamy do całkowitych jak
     oficjalny indeks.
   - Wiatr średni ≥29 km/h → MODERATE, ≥39 → POOR: dolne granice Beaufort 5
     ("fresh breeze" 29-38) i 6 ("strong breeze" 39-49):
     <https://en.wikipedia.org/wiki/Beaufort_scale>. Porywy ≥50 / ≥62 km/h
     (dolne granice Beaufort 7 / 8) — skala opisuje wiatr uśredniony, więc dla
     porywów to tylko orientacja.
   - **Decyzje produktowe "do kalibracji" (brak zweryfikowanego źródła, nie
     udajemy faktu):** temperatura odczuwalna i 2 m — upał ≥27 / ≥32 °C, zimno
     ≤0 / ≤−10 °C (te same progi dla obu parametrów, liczone niezależnie, worst
     wins); opady ≥0,1 mm → MODERATE, ≥2,5 mm → POOR (okno sumowania
     `precipitation` w `current` Open-Meteo nie zostało tu zweryfikowane —
     progi dotyczą wartości tak, jak jest zapisana); widoczność <5000 m →
     MODERATE, <1000 m → POOR (intuicja "mgła ≈ 1 km", niezweryfikowana).
     Nie sprawdziliśmy też progów ostrzeżeń IMGW (wiatr/upał) — świadomie nie
     powielamy ich z pamięci.
6. **Punkt wpięcia pod TASK-12.4:** opcjonalny parametr `rules` (można podać
   zmodyfikowaną tabelę). Wrażliwość/profil NIE jest zaimplementowany.

## Consequences

- Silnik testowalny zwykłym `python3`; ten sam kod wywoła TASK-7.7 z danych
  DB (freshness przekazuje wołający z istniejących `freshness()`).
- Wołający odpowiada za jednostki (°C, mm, km/h, m, µg/m³) — silnik ich nie
  konwertuje; TASK-7.7 musi zmapować `param_code` GIOŚ `PM2.5`/`PM10` na pola
  `pm25`/`pm10` i sprawdzić `unit`.
- Kalibracja produktowa = edycja jednej tabeli + aktualizacja testów granic
  (testy liczą się z tabeli `RULES`, więc same brzegi przesuną się razem).
- Brak zmian w modelach, migracjach, `dashboard.py` i mobile.
- Rozszerzenie (np. śnieg, pyłki, NO2/O3) = nowe pola `OutdoorInputs` + reguły.
