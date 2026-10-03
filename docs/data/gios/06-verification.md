# Raport weryfikacji 2026-10-03

## Co wykonano

Pobrano i sparsowano 7 oficjalnych YAML OpenAPI 3.1.1 / version 1.0.0 oraz JSON OpenAPI 3.0.1 JPOAT. Katalog api zawiera wszystkie opublikowane operacje i schematy. Wykonano po jednym żądaniu discovery do każdej nowej usługi, potem po jednym skorygowanym żądaniu dla hałasu i wód. To nie jest pełna certyfikacja wszystkich endpointów. Każda próbka ma URL, HTTP status, body, datę i stan sukcesu/błędu. Brak próbek z nieprzetestowanych operacji jest jawny.

## Wyniki rzeczywiste

| Usługa / operacja | Wynik | Znaczenie |
|---|---|---|
| PRTR /uwolnienia, size=1 | SUKCES, rekord z 2007 r. | bez roku filtr nie oznacza najnowszych danych; lacznaIlosc jest liczbą mimo string w spec; jednostka nieobecna |
| PA /zaklady, size=1 | SUKCES, ZZR w Wałbrzychu | kodNace jest liczbą mimo string w spec; brak coords |
| NEC /stanowiska, rok=2023 | SUKCES | kod stacji i lon/lat są liczbami mimo string; nullable parametry i kody |
| Powietrze /stanowisko-id | SUKCES | rekord stanowiska historycznego 2004–2005; nie utożsamiać z aktywnym sensorem |
| Hałas /pomiar, lowercase województwa | HTTP 200, BLAD 400 | województwo musi odpowiadać enum np. ŚLĄSKIE |
| Hałas /pomiar, ŚLĄSKIE i rok 2024 | SUKCES, 64.5 dB | WGS84 X jest longitude, Y latitude w tej próbce; date fields mają pełny datetime z offsetem mimo format=date |
| Wody podziemne /punkty, tylko lata | HTTP 200, BLAD 400 | dodatkowo wymagany co najmniej dorzeczeNazwa albo jcwpdKod albo jcwpdNumer; nie zapisano jako required w OpenAPI |
| Wody podziemne /punkty, dorzecze Odra | SUKCES | coords obiekt x/y w układzie projekcyjnym, nie string; flagi TAK zamiast boolean; CRS niepotwierdzony |
| Wody powierzchniowe /programy, Odra 2025 | SUKCES, liczbaRekordow=0, brak strona | brak wyniku dla tego query nie dowodzi pustego całego zbioru; niepusty rekord NIEZWERYFIKOWANY |
| Wody powierzchniowe /programy, pusta nazwa | HTTP 200, BLAD 400 | nazwa rzeczywiście wymagana; pusty string nie daje pełnego eksportu |

`wynik.data` w tych odpowiedziach nie ma timezone, mimo opisu UTC w schemacie. `liczbaRekordow=1` przy size=1 wskazuje, że nie wolno ufać mu jako globalnemu total; całkowita semantyka pozostaje do testów.

## Nierozstrzygnięte

Nie zweryfikowano kompletnej paginacji, cyklu publikacji i limitów nowych API, niepustych wyników programów wód powierzchniowych, jednostek PRTR, geometrii zasięgów hałasu, CRS wód podziemnych, pełnych danych ocen/trendów/NEC i dokumentów, geometrii JCWP/JCWPd/zakładów. Te elementy są blokadami odpowiednich funkcji, nie podstawą do zgadywania.

## Źródła pierwotne

- https://dane.gios.gov.pl/ — frontend wskazuje 7 plików /apispec/openapi-*.yaml; adresy w manifest.json.
- https://api.gios.gov.pl/pjp-api/v3/api-docs — pełny JPOAT.
- https://powietrze.gios.gov.pl/pjp/content/api — aktualne wersje, wycofanie starszych 30.06.2025, limity, JSON-LD, czas lokalny i opóźnienia danych manualnych.
- https://www.gov.pl/web/gios/ponowne-wykorzystywanie-danych — ponowne wykorzystanie, attribution, indywidualne opłaty.
- https://www.gov.pl/web/gios/jakosciowe-dane-o-srodowisku-na-wyciagniecie-reki-nowe-api-gios-juz-dostepne — opis programu; sam komunikat nie zastępuje specyfikacji.
- https://www.gov.pl/web/gios/monitoring-jakosci-gleby-i-ziemi — cykl 5 lat, 216 punktów, raport 2025 i XLSX 1995–2025.
- https://www.gov.pl/web/gios/monitoring-promieniowania-jonizujacego-oraz-jego-wyniki ; https://www.gov.pl/web/gios/monitoring-przyrody — dalsze obszary discovery.

Stan repo zweryfikowany przez README.md, CLAUDE.md, source-registry.md i connector gios/client.py na main; dokumentacja bazuje na head 2c00237ac3259098977df891ee5dca1ba56d4e08. Nie wykonano testów runtime aplikacji; zmiana jest dokumentacyjna.
