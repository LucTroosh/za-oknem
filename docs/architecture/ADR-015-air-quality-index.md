# ADR-015: Indeks jakości powietrza (ogólny + cząstkowe)

- **Date:** 2026-09-30
- **Status:** Proposed (ZABLOKOWANE na weryfikacji — patrz Consequences)

## Context

Master Plan §4.1 wymienia w MVP „indeks jakości powietrza” i „indeksy cząstkowe”.
TASK-4.1 dostarczył pomiary 7 parametrów (Measurement). Indeks to pojęcie
pochodne — nie jest Measurement (rule #7), a rule #10 zabrania LLM i zgadywania
w danych bezpieczeństwa.

## Problem

Czy czytać gotowy indeks od GIOŚ (`/v1/rest/aqindex/getIndex/{stationId}`), czy
liczyć własną, deterministyczną funkcją wg opublikowanej metodologii?

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

## Decision (robocza)

Rekomendacja: **A**, bo eliminuje przepisywanie progów, których nie da się tu
zweryfikować, i rozstrzyga pkt 3. Decyzja finalna po dostarczeniu jednego z:
(i) surowy JSON z `GET /v1/rest/aqindex/getIndex/<id>` z żywego API (jak przy
weryfikacji z 2026-09-28), albo (ii) tabela progów przepisana z oficjalnej strony
z widocznego obrazka (wtedy B). Do tego czasu nie powstaje kod.

## Consequences

- Brak kodu i migracji w tym PR — tylko ADR i dokument zadania. Brak zgadywania.
- Niezależnie od opcji obowiązują: freshness indeksu = freshness danych wejściowych
  (rule #8), GIOŚ zwraca „Brak indeksu” dla stacji bez wyznaczonego indeksu; brak wiersza i brak udanego pobrania to osobny stan UNAVAILABLE (po nieudanym polu zostaje ostatni snapshot ze stanem wg `last_success_at`) (rule #8, ADR-012), nie „Brak indeksu” (nigdy 0 ani „Bardzo dobry”), etykiety
  dosłownie jak wyżej, dostępność (tekst, nie tylko kolor), logika mobilna w
  `apps/mobile/app/aqi.ts`.
- Migracja, jeśli A: `0010` (0009 zajęta przez PR provenance).
