# GIOŚ — pakiet implementacyjny dla Za Oknem v1

Data weryfikacji: 2026-10-03. Docelowe repo: LucTroosh/za-oknem.
Zakres: dokumentacja i plan rozwoju; ten pakiet NIE oznacza, że nowe funkcje są już zaimplementowane lub wdrożone.

## Kolejność czytania

1. [Wnioski, obszary i produkt](01-scope-and-product.md).
2. [Integracja, baza, kontrakty i geo](02-development-contract.md).
3. [Licencje i Source Approval Gate](03-licensing-and-source-gates.md).
4. [Zadania, testy i odbiór](04-work-breakdown.md).
5. [Gotowa instrukcja dla Claude](05-claude-prompt.md).
   Stan bramek per operacja i blokery: [07-operation-gates.md](07-operation-gates.md); decyzje: ADR-032; jak zamknąć
   B-6 na własnej maszynie: [08-operator-probe.md](08-operator-probe.md).
6. `api/*.md`: kompletny katalog operacji, parametrów, odpowiedzi, schematów i enumeracji.
7. `openapi/*`: oryginalne specyfikacje GIOŚ, zapisane bez zmian.
8. `evidence/*` oraz [raport weryfikacji](06-verification.md): rzeczywiste odpowiedzi HTTP wraz z adresami.

## Najważniejsze korekty względem wstępnego researchu

- API wód powierzchniowych ma jedną operację: programy monitoringu. Nie dostarcza w tym kontrakcie pomiarów pH, temperatury ani klasy stanu ekologicznego. Nie budować na nim karty „jakość wody”.
- PRTR i PA/SEVESO nie mają współrzędnych zakładów w opublikowanych schematach. Lokalizacja administracyjna jest dostępna, odległość od użytkownika wymaga dodatkowego wiarygodnego źródła geometrii.
- `liczbaRekordow` nie może być traktowane jako liczba wszystkich wyników: w próbach przy rozmiarze 1 zwracano 1. Semantykę paginacji trzeba potwierdzić, nie wnioskować z nazwy.
- HTTP 200 może zawierać `wynik.status=BLAD`. Taką odpowiedź traktować jako błąd źródła.
- Rzeczywiste typy różnią się od OpenAPI, m.in. współrzędne i flagi wód podziemnych. Katalog specyfikacji jest kontraktem deklarowanym, próbki są dowodem zachowania serwera.
- Siedem nowych grup OpenAPI plus istniejące API bieżącego powietrza to zakres pakietu. Komunikat o „8 nowych API” nie dowodzi istnienia ósmej nowej specyfikacji.
- Licencja CC BY 4.0 jest jawnie zapisana we wszystkich siedmiu nowych specyfikacjach. Nie przenosić jej automatycznie na inne portale, zdjęcia, mapy bazowe lub pliki osób trzecich.

## Źródła i wersjonowanie

Źródło specyfikacji: https://dane.gios.gov.pl/apispec/openapi-{nazwa}.yaml.
Źródło bieżącego powietrza: https://api.gios.gov.pl/pjp-api/v3/api-docs.
Źródło warunków: https://www.gov.pl/web/gios/ponowne-wykorzystywanie-danych.
Kontakt techniczny bieżącego powietrza: api@gios.gov.pl; nowy portal: https://dane.gios.gov.pl/kontakt.
`manifest.json` zawiera sumy SHA-256, adresy i wersje. Aktualizacja specyfikacji wymaga diffu i ponownych testów kontraktowych.
Oryginalne nowe specyfikacje: Źródło danych: GIOŚ, CC BY 4.0; kopie bez modyfikacji. Opisy i proponowana architektura Za Oknem są opracowaniem własnym.
