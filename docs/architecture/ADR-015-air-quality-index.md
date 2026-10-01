# ADR-015: Indeks jakości powietrza (ogólny + cząstkowe)

- **Date:** 2026-09-30 (decyzja EAQI: 2026-10-01)
- **Status:** Accepted — opcja C (Europejski Indeks Jakości Powietrza, EEA). Opcja A (gotowy indeks GIOŚ) = *Superseded option A*, odłożona; opcja B (własny indeks wg progów GIOŚ) odpada do czasu weryfikacji progów.

## Context

Master Plan §4.1 wymienia w MVP „indeks jakości powietrza” i „indeksy cząstkowe”.
TASK-4.1 dostarczył pomiary 7 parametrów (Measurement). Indeks to pojęcie
pochodne — nie jest Measurement (rule #7), a rule #10 zabrania LLM i zgadywania
w danych bezpieczeństwa.

## Problem

Czy czytać gotowy indeks od GIOŚ (`/v1/rest/aqindex/getIndex/{stationId}`), czy
liczyć własną, deterministyczną funkcją wg opublikowanej metodologii?

## Decision

**Opcja C: liczymy Europejski Indeks Jakości Powietrza (EAQI, EEA) własną, czystą funkcją
z naszych pomiarów GIOŚ** (`apps/api/app/air_index.py`). Powody: oficjalna, publiczna,
jawna metodologia z liczbowymi progami, zweryfikowana tekstowo (nie z obrazka); rule #10
(jawny algorytm, nie LLM), rule #14 (z naszej bazy, bez wołania zewnętrznego API).
Indeks *natywny* GIOŚ (opcja A, `aqindex/getIndex`) zostaje odłożoną opcją — odblokuje
ją żywy JSON albo tabela progów z oficjalnego obrazka; wtedy nowy ADR (historii nie kasujemy).

### Zweryfikowana metodologia EAQI (WebFetch, 2026-09-30)

Źródła pierwotne (zgodne co do liczb):
1. <https://airindex.eea.europa.eu/AQI/index.html> (strona EEA)
2. ETC HE Report 2024/17 „EEA's revision of the European air quality index bands”, v1,
   3.07.2025, DOI 10.5281/zenodo.15781195 (PDF na eionet.europa.eu).

- Kategorie (EN, EEA): Good, Fair, Moderate, Poor, Very poor, Extremely poor.
- Indeks **godzinowy** dla wszystkich pięciu zanieczyszczeń (także PM: „hourly based
  index”, nie 24 h), µg/m³. Pasma (powyżej ostatniego = Extremely poor):

| Zanieczyszczenie | Good | Fair | Moderate | Poor | Very poor | Extremely poor |
|---|---|---|---|---|---|---|
| PM2.5 | 0-5 | 6-15 | 16-50 | 51-90 | 91-140 | >140 |
| PM10 | 0-15 | 16-45 | 46-120 | 121-195 | 196-270 | >270 |
| NO2 | 0-10 | 11-25 | 26-60 | 61-100 | 101-150 | >150 |
| O3 | 0-60 | 61-100 | 101-120 | 121-160 | 161-180 | >180 |
| SO2 | 0-20 | 21-40 | 41-125 | 126-190 | 191-275 | >275 |

- Indeks ogólny: „The index corresponds to the poorest level for any of the five
  pollutants” (najgorszy z cząstkowych).
- Minimalny zestaw (EEA): stacje komunikacyjne — PM (2,5 lub 10) + NO2; tła/przemysłowe —
  PM + NO2 + O3; poniżej minimum mapa EEA pokazuje stację półprzezroczyście.
- CO i benzen: ani strona, ani raport ich nie wymieniają — **nie są w EAQI**; pokazujemy
  je wyłącznie jako wartości (bez indeksu cząstkowego).
- Progi wpisane w kod (`BANDS`) i, osobno, w test — literówka musi oblać test.

### Czego EEA NIE precyzuje — nasze decyzje (jawne, do rewizji)

1. **Granice pasm.** EEA podaje pasma całkowite („0-5, 6-15”), nasze wartości są
   ułamkowe. Przyjęto: pasmo = `wartość <= górny kraniec` (5,0 → Good, 5,01 → Fair),
   prawostronnie domknięte jak w GIOŚ; nigdy nie zaokrągla wartości do lepszego pasma.
   Zaokrąglenie do całkowitych dałoby 5,4 → Good; wybrano wariant ostrożniejszy.
2. **Typ stacji.** Nie mamy go w danych, więc wymagamy zestawu surowszego:
   (PM2.5 lub PM10) + NO2 + O3. Bez niego wynik Good/Fair = „brak indeksu” (brakujące
   zanieczyszczenie mogłoby być gorsze); wynik Moderate lub gorszy stoi jako **dolne
   ograniczenie** z `complete=false` (UI: „co najmniej …”). Stacja komunikacyjna bez O3
   dostaje więc „co najmniej” albo brak — świadomy koszt ostrożności.
3. **Nazwy polskie.** Oficjalnych polskich nazw 6 pasm po rewizji 2025 nie udało się
   zweryfikować (polska strona EEA opisuje starszy schemat 5-poziomowy). Kody w API są
   angielskie (EEA); etykiety PL w `aqi.ts` to **nasze tłumaczenie**: Dobra,
   Zadowalająca, Umiarkowana, Zła, Bardzo zła, Skrajnie zła. Celowo nie używamy nazw GIOŚ
   (Bardzo dobry…Bardzo zły): tamta skala ma inne progi — mylenie skal byłoby błędem.
4. **Jednostka.** GIOŚ zapisujemy jako `µg/m³` (`parser.PARAM_UNITS`). Wartość z inną
   jednostką jest pomijana (`missing: UNIT`), nie konwertowana. Ujemna/NaN/inf →
   `INVALID`, pomijana.

### Zachowanie (rule #8)

Wejście o freshness innym niż FRESH/RECENT (STALE/UNAVAILABLE) = brak, jak w
`outdoor.py`. Odpowiedź niesie `valid_until` (najwcześniejsze wygaśnięcie wejścia);
mobile po tym czasie przestaje twierdzić indeks, jak przy `outdoor`.

### Dlaczego bez migracji i bez tabeli

Indeks jest funkcją czystą bieżących, już zapisanych Measurement; druga kopia (snapshot)
to dwa źródła prawdy i osobny mechanizm świeżości. Liczymy przy odczycie z wierszy już
załadowanych przez `/air/latest` i `dashboard` (zero dodatkowych zapytań). Koszt: brak
historii indeksu — poza MVP. Migracja 0013 pozostaje wolna.

## Consequences

- Nowe: `app/air_index.py` (czysty), pole `index` w `GET /api/v1/air/latest` (per stacja,
  typowany `AirIndex`) i w bloku `air` z `dashboard/latest`; mobile `aqi.ts` +
  `components/AirIndexBadge.tsx`. Pola addytywne — starszy klient działa.
- Rule #15: EAQI to **metodologia, nie nowy feed** — brak nowego źródła i połączenia z
  EEA w runtime, więc Source Approval Gate jak dla connectora nie dotyczy; dane wejściowe
  to nadal GIOŚ (wpis `gios`). Licencja treści EEA: CC-BY 4.0, użycie komercyjne
  dozwolone, wymagane wskazanie EEA i niezniekształcanie sensu
  (<https://www.eea.europa.eu/en/legal-notice>, 2026-09-30). Adnotacja w
  `docs/data/source-registry.md`; atrybucja w UI: „Europejski Indeks Jakości Powietrza
  (EEA), liczony z pomiarów GIOŚ”. To nasze obliczenie wg metodologii EEA, nie oficjalny
  indeks EEA ani GIOŚ.
- Rule #12: ten ADR obejmuje zmianę (własne liczenie indeksu wg metodologii zewnętrznej,
  nowe pole kontraktu API).
- Rule #10: wynik POCHODNY, nie dane bezpieczeństwa; nie zastępuje komunikatów GIOŚ/IMGW.
- Dostępność: etykieta tekstowa, numer pasma (x/6) i ikona, nie tylko kolor.
- Ryzyko: rewizja pasm przez EEA (ostatnia: lipiec 2025) wymaga zmiany `BANDS` i testu.

---

# Historia (decyzja robocza sprzed 2026-10-01; zachowana, *Superseded option A*)

Poniższe sekcje opisują opcje A/B (GIOŚ) i powód pierwotnej blokady. Punkty o
freshness, „Brak indeksu” i dostępności z pierwotnych Consequences są realizowane przez
Decision powyżej.

## Fakty zweryfikowane (2026-09-30, WebFetch stron GIOŚ)

Źródła: <https://powietrze.gios.gov.pl/pjp/content/health_informations>,
<https://powietrze.gios.gov.pl/pjp/current>,
<https://powietrze.gios.gov.pl/pjp/content/show/1001197> (komunikat archiwalny).

- Kategorie (dosłownie): Bardzo dobry, Dobry, Umiarkowany, Dostateczny, Zły,
  Bardzo zły, oraz „Brak indeksu” (szary).
- Indeks ogólny „przyjmuje wartość najgorszego indeksu indywidualnego wśród
  zanieczyszczeń mierzonych na stacji” (albo wskaźnika dominującego dla regionu,
  albo nie jest wyznaczany).
- Progi są lewostronnie otwarte, prawostronnie domknięte (PM10 = 50,0 → Dobry;
  50,1 → Umiarkowany). Indeks dotyczy stężeń 1-godzinnych.
- Endpoint `aqindex/getIndex/{stationId}` istnieje, limit 1500 żądań/min
  (<https://powietrze.gios.gov.pl/pjp/content/api>).

## Fakty NIEzweryfikowane (powód blokady)

1. **Liczbowe progi per zanieczyszczenie** na stronach GIOŚ są wyłącznie obrazkiem
   (`content_image/1187`); WebFetch nie zwraca liczb, a `curl` do domeny GIOŚ jest
   blokowany przez proxy środowiska. Tabela z `armaag.gda.pl` (strona trzecia,
   bez daty, o rodowodzie „ATMOLUDEK”) NIE jest źródłem oficjalnym; GIOŚ ogłosił
   zmianę progów O3, więc jej przepisanie mogłoby dać błędne klasy. Jedyny punkt
   potwierdzony krzyżowo: granica PM10 50 µg/m³.
2. **Kształt odpowiedzi v1 `getIndex`.** Jedyny znaleziony przykład pochodzi ze
   starego API (`stIndexLevel.indexLevelName`, `pm10IndexLevel`, …). Rejestr
   źródeł odnotowuje, że żywe v1 zwraca JSON-LD z polskimi kluczami, więc kształt
   z przykładu nie może być założony (ta sama lekcja co przy parserze GIOŚ).
3. Czy CO i C6H6 wchodzą do indeksu ogólnego: strony GIOŚ są niespójne (jedna
   wymienia 7 zanieczyszczeń, inna pisze, że CO i C6H6 są mierzone, ale nie
   indeksowane).

## Options

- **A. Czytać gotowy indeks GIOŚ.** Zero własnych progów, zgodność z oficjalną
  stroną z definicji, rozstrzyga punkt 3 po stronie GIOŚ. Wymaga: nowego wywołania
  connectora, osobnego modelu (snapshot `AirIndex` — nie Measurement; migracja
  Alembic 0010), wpisu w source-registry. Koszt: zależność od kształtu v1 (pkt 2).
- **B. Liczyć samemu.** Czysta funkcja `(param, value) → klasa` + `max()`.
  Bez nowej tabeli i migracji, w pełni testowalna. Koszt: progi przepisane
  dosłownie z oficjalnej tabeli (pkt 1) i ryzyko rozjazdu po zmianie metodologii
  (jak O3).

## Decision robocza (zastąpiona opcją C)

Rekomendacja: **A**, bo eliminuje przepisywanie progów, których nie da się tu
zweryfikować, i rozstrzyga pkt 3. Decyzja finalna po dostarczeniu jednego z:
(i) surowy JSON z `GET /v1/rest/aqindex/getIndex/<id>` z żywego API (jak przy
weryfikacji z 2026-09-28), albo (ii) tabela progów przepisana z oficjalnej strony
z widocznego obrazka (wtedy B). Do tego czasu nie powstaje kod.

## Consequences robocze (pierwotne)

- Brak kodu i migracji w tym PR — tylko ADR i dokument zadania. Brak zgadywania.
- Niezależnie od opcji obowiązują: freshness indeksu = freshness danych wejściowych
  (rule #8), GIOŚ zwraca „Brak indeksu” dla stacji bez wyznaczonego indeksu; brak wiersza i brak udanego pobrania to osobny stan UNAVAILABLE (po nieudanym polu zostaje ostatni snapshot ze stanem liczonym z `source_data_date`, nie z czasu pollu) (rule #8, ADR-012), nie „Brak indeksu” (nigdy 0 ani „Bardzo dobry”), etykiety
  dosłownie jak wyżej, dostępność (tekst, nie tylko kolor), logika mobilna w
  `apps/mobile/app/aqi.ts`.
- Migracja, jeśli A: `0010` (0009 zajęta przez PR provenance).
