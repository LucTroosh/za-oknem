# Macierz bramek per operacja (GIOS-00) — stan 2026-10-03

Dokument roboczy implementacji. Jedno źródło prawdy o tym, które operacje GIOŚ wolno wdrażać i co blokuje
resztę. Uzupełnia `03-licensing-and-source-gates.md` (gate z sześciu punktów) i `06-verification.md`
(dowody). Decyzje architektoniczne: `docs/architecture/ADR-032-neighborhood-module.md`.

## Jak to czytać i czego ten dokument NIE dowodzi

- Dowody = pliki w `evidence/` (rzeczywiste odpowiedzi HTTP z 2026-10-03, zapisane przez autora pakietu)
  oraz specyfikacje w `openapi/`. **Środowisko agenta nie ma dostępu do `dane.gios.gov.pl`** (blokada
  egress; analogicznie do `api.gios.gov.pl`), więc w tym PR **nie powtórzyłem żadnego żądania**. Nic poniżej
  nie jest „zweryfikowane na żywo przeze mnie”; to ocena dowodów z pakietu.
- Status operacji: `IMPLEMENTABLE` (dowody z pakietu pozwalają pisać kod i testy na fixture, ale **gate (03) NIE
  jest zaliczony** — brakujące punkty są wypisane w wierszu; `no_records` i włączenie flagi na produkcji dopiero po
  ich zamknięciu przez operatora, B-6/B-8), `PARTIAL` (część sekcji możliwa, część zablokowana), `BLOCKED` (z
  konkretnym brakiem). `UNVERIFIED` = brak jakiejkolwiek próbki operacji. Gate jest zaliczony dopiero przy statusie
  `APPROVED` w Source Registry.
- Gate (03): (1) kontrakt+licencja, (2) niepusty/pusty/błąd + parametry + paginacja + jednostki, (3) różnice
  spec/live obsłużone jawnie, (4) cykl publikacji albo wyjątek ADR, (5) geo i okres, (6) kwarantanna,
  retry, izolacja, testy, atrybucja, flaga. Punkty 4 i 6 wynikają z ADR-032 (import ręczny, flagi).

## Licencja (punkt 1) — wspólna dla wszystkich siedmiu

Każdy z siedmiu plików OpenAPI deklaruje `CC BY 4.0` (`https://creativecommons.org/licenses/by/4.0/`).
Warunki: atrybucja „Źródło danych: GIOŚ”, link do licencji, oznaczenie przetworzenia. Dotyczy zbiorów z tych
specyfikacji, nie innych portali, map bazowych ani grafik.

## Operacje

| Operacja (`/api/{usługa}/v1/…`) | Do czego | Dowód z pakietu | Co potwierdzone | Co NIE | Status |
|---|---|---|---|---|---|
| `halas/pomiar-halasu-w-srodowisku` | sekcja Hałas (GIOS-04) | niepusty (Żyglin, 64,5 dB, 2024), błąd walidacji przy 200, pusty brak | wymagane: `kategoria` (Droga/Lotnisko/Przemysł/Kolej), `wojewodztwo` (enum WIELKIMI literami, np. `ŚLĄSKIE`), `dataOd`, `dataDo` (ISO `yyyy-mm-dd`); jednostka dB (opis pola); WGS84: `coordWgs84X` = długość, `coordWgs84Y` = szerokość; `dataOd/dataDo` z offsetem mimo „date”; `pora` tekst („Dzień 16h”) | próbka pustego wyniku; semantyka `liczbaRekordow` i koniec paginacji (bez tego `no_records` jest niedozwolone); maks. zakres dat; cykl publikacji; czy cały kraj da się pobrać (64 kombinacje kategoria × województwo × okres) w rozsądnym czasie | **IMPLEMENTABLE** (import ręczny, flaga domyślnie off); gate niezaliczony: brak próbki pustego wyniku, paginacji i zakresu dat (B-6) |
| `halas/zasiegi-halasu` | polygon i ekspozycja (GIOS-05) | brak próbki; schemat ma przykład `Point` i płaską tablicę `coordinates` | tylko kontrakt | geometria rzeczywistego zasięgu, CRS, runda/wskaźnik/przedział | **BLOCKED** (próbka polygonu + CRS) |
| `halas/*` pozostałe (jednostki, działania, ludność, środki, powierzchnia, koszty, dopuszczalne poziomy) | kontekst | brak próbek | tylko kontrakt | wszystko | **UNVERIFIED** (poza zakresem PR-D) |
| `prtr/uwolnienia` | sekcja PRTR (GIOS-06) | niepusty (rok 2007, Woda, Zn) | `typUwolnienia`, `rokRaportu`, `zaklad`, `regon`, `wojewodztwo` (WIELKIE), `powiat` („Powiat turecki”), `miejscowosc`; `lacznaIlosc` jest liczbą mimo „string” w spec; brak współrzędnych | **jednostka `lacznaIlosc`** (brak w schemacie); bez filtra roku zwraca rekordy sprzed lat; paginacja; wymagane filtry | **PARTIAL**: lista zakładów w obszarze administracyjnym możliwa; **liczby emisji `unit_unknown`, bez agregacji i bez kg/t** |
| `prtr/transfery` | transfery odpadów | brak próbki | tylko kontrakt | wszystko, w tym jednostka masy | **UNVERIFIED** |
| `powazne-awarie/zaklady` | rejestr ZZR/ZDR (GIOS-07) | niepusty (ZZR, Wałbrzych) | `klasyfikacjaZakladu`, `nazwaZakladu`, `regon`, `kodNace` jako liczba JSON (`19.10` traci końcowe zero), administracja małymi literami (`dolnośląskie`, `wałbrzyski`, bez „Powiat”), adres, `stronaWww`; brak współrzędnych | paginacja; wymagane filtry; cykl | **PARTIAL**: rejestr informacyjny z dopasowaniem administracyjnym; bez odległości |
| `powazne-awarie/powazne-awarie` | historia zdarzeń | brak próbki | tylko kontrakt | pola zdarzenia, daty, powiązanie z zakładem | **UNVERIFIED** |
| `wody-powierzchniowe/programy-monitoringu` | plan monitoringu (GIOS-08) | pusty wynik (`Odra`, 2025) i błąd (`jcwpNazwa` wymagana, także dla pustego stringa); **brak niepustego rekordu** | `jcwpNazwa` jest wymagana w runtime | czy w ogóle zwraca rekordy; kształt rekordu; brak wartości pomiarów, klas, geometrii z definicji | **BLOCKED** dla UI (niepusty rekord) i **dla „jakości wody”** (plan ≠ wynik; wyniki i geometria JCWP z innego, jeszcze nieodnalezionego zbioru) |
| `wody-podziemne/punkty-pomiarowe-monitoringu` | punkty (GIOS-09) | niepusty (Odra, JCWPd PLGW60001) oraz błąd przy samych latach | wymagane: co najmniej `dorzeczeNazwa` albo `jcwpdKod` albo `jcwpdNumer` (nie w spec); współrzędne jako obiekt `{x, y}`; flagi `"TAK"` zamiast boolean | **CRS** (`x≈185897`, `y≈678641` to współrzędne projekcyjne, nie stopnie); polygony JCWPd | **BLOCKED** dla geo; dane punktów jako tabela możliwe, bez lokalnego dopasowania |
| `wody-podziemne/*` pozostałe (programy, metodyki, oceny, trendy, plik) | oceny JCWPd | brak próbek | tylko kontrakt | wszystko | **UNVERIFIED** |
| `nec/monitorowanie/stanowiska` | ekosystemy (GIOS-11) | niepusty (SPO MI Krucz, 2023) | `dlugoscGeograficzna` 16,417, `szerokoscGeograficzna` 52,813 (kolejność zgodna z nazwami i z położeniem w Polsce), `krajowyKodStacji` liczbą, nullable pola | formalne potwierdzenie CRS; `parametry` jest null | **IMPLEMENTABLE** dla stanowisk (gate niezaliczony: paginacja, rejestr pustych wyników); wyniki niżej |
| `nec/monitorowanie/wskazniki`, `…/wyniki` | wyniki | brak próbek | tylko kontrakt | jednostki, kwalifikatory, daty | **UNVERIFIED** |
| `powietrze/stanowisko-id` | metadane stanowisk historycznych | niepusty (stanowisko 2004–2005, zamknięte) | struktura rekordu | nie utożsamiać ze stanowiskiem aktywnym | **PARTIAL** (poza zakresem najbliższych PR) |
| `powietrze/*` pozostałe (oceny, PM2.5, chemizm opadów, raporty, plik) | historia (GIOS-10) | brak próbek | tylko kontrakt | wszystko | **UNVERIFIED** |

## Zależności i blokery (zapisane, nie zgadywane)

| Blocker | Co odblokuje | Kto / jak |
|---|---|---|
| B-1 Jednostka `lacznaIlosc` (PRTR) i masy odpadów | liczby emisji i transferów w UI | pytanie do GIOŚ (treść w `03`, pkt 1); do tego czasu `unit_unknown` |
| B-2 CRS punktów wód podziemnych i geometrii zasięgów hałasu | mapowanie punktu na JCWPd, ekspozycja hałasu | pytanie do GIOŚ + transformacja po stronie serwera i test znanych punktów; **nie zakładać EPSG:2180 z samych zakresów** |
| B-3 Polygony JCWP/JCWPd | wody powierzchniowe i podziemne „w okolicy” | osobny discovery zbioru geometrii z własnym gate |
| B-4 Wyniki jakości wód powierzchniowych | karta jakości wody | osobny discovery (portal/plik z wynikami, licencja); API `programy-monitoringu` ma tylko plan |
| B-5 Geometria zakładów PRTR i ZZR/ZDR | odległości, „w promieniu” | dodatkowy wiarygodny rejestr; do tego czasu tylko dopasowanie administracyjne |
| B-6 Semantyka `liczbaRekordow`, paginacja, maks. zakres dat, cykl publikacji, limity | cykliczny polling, pewność kompletności snapshotu | testy stron 0/1/ostatniej przez operatora (`--validate-only`) + pytanie do GIOŚ; do tego czasu import ręczny i ochrona przed pętlą |
| B-7 Strefa czasowa `wynik.data` (bez offsetu) | użycie `wynik.data` | nie używamy jej jako czasu pomiaru; własne `fetched_at` w UTC |
| B-8 Żywa weryfikacja z sieci | zmiana statusu `IMPLEMENTABLE` → `APPROVED` w Source Registry | operator: `python -m app.connectors.<źródło>.ingest --validate-only` na maszynie z dostępem; wynik do rejestru |

## Korekty pomysłu produktowego wynikające z kodu i źródeł

1. **Klucz API: `geo_area_id`, nie `place_id`.** Siedem miast z seedów nie ma `place_id`; mobile trzyma `geoAreaId`
   (ADR-032 pkt 4).
2. **Brak pola `freshness` w sekcjach historycznych.** Wystarczy `source_period` + `fetched_at` +
   `retrieval_status`; wskaźnik świeżości mógłby sugerować aktualność roczników (ADR-032 pkt 6).
3. **Hałas to rzadka siatka punktów.** Dla wielu lokalizacji będzie `no_coverage`; wejście na Start tylko przy
   włączonej fladze, sekcja bez danych jako jedna linia, próg odległości jawny i konfigurowalny.
4. **Wody powierzchniowe nie są kartą „jakość wody”.** To plan badań; do czasu wyników i geometrii sekcja
   nie powstaje (B-3, B-4).
5. **PRTR/ZZR/ZDR bez promienia.** Tylko „w miejscowości / w powiecie / w województwie”, zależnie od pewności
   dopasowania; nazewnictwo różni się między usługami (WIELKIE litery i „Powiat turecki” w PRTR, małe litery i
   bez „Powiat” w rejestrze ZZR/ZDR), więc potrzebna jest normalizacja hierarchii, nie dopasowanie po samej nazwie.
6. **Obecne `places` ma GeoNames-owe nazwy administracyjne** (województwo po angielsku, „Powiat xyz”),
   a województwo da się już mapować na kod (`places.alert_match_codes`, ADR-013). Dopasowanie PRTR/ZZR/ZDR
   korzysta z tego mapowania i ze słownika powiatów; zasięg „w miejscowości” tylko, gdy hierarchia zgadza się
   w całości.
7. **Import, nie scheduler** dla nowych źródeł (cykl UNKNOWN, dane roczne).
