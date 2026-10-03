# WODY-POWIERZCHNIOWE API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-wody-powierzchniowe.yaml. Pobrano 2026-10-03. SHA-256: `cb353fef329debf30ee430b6d3c0b245614ac446661c6281cc96c0f10de0e4c5`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/wody-powierzchniowe

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/programy-monitoringu`

Programy monitoringu jednolitych części wód powierzchniowych

Usługa sieciowa udostępniająca zaplanowane programy monitoringu jednolitych części wód powierzchniowych (dane dostępne od 2022 roku)

operationId: `getProgramyMonitoringuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| jcwpKod | query | False | string | {"maxLength":30} | Kod jednolitej części wód powierzchniowych (jcwp). Kody jcwp znajdują się na Portalu Jakości Wód Powierzchniowych [https://wody.gios.gov.pl/pjwp/maps/](https://wody.gios.gov.pl/pjwp/maps/) |
| jcwpNazwa | query | True | string | {"maxLength":200} | Nazwa jednolitej części wód powierzchniowych (jcwp). Nazwy jcwp znajdują się na Portalu Jakości Wód Powierzchniowych [https://wody.gios.gov.pl/pjwp/maps/](https://wody.gios.gov.pl/pjwp/maps/) |
| ppkKod | query | False | string | {"maxLength":50} | Kod punktu pomiarowo-kontrolnego (ppk). Kody ppk znajdują się na Portalu Jakości Wód Powierzchniowych [https://wody.gios.gov.pl/pjwp/maps/](https://wody.gios.gov.pl/pjwp/maps/) |
| ppkNazwa | query | False | string | {"maximum":150} | Nazwa punktu pomiarowo-kontrolnego (ppk). Nazwy ppk znajdują się na Portalu Jakości Wód Powierzchniowych [https://wody.gios.gov.pl/pjwp/maps/](https://wody.gios.gov.pl/pjwp/maps/) |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| wskaznik | query | False | string | {"maxLength":200} | Nazwa wskaźnika. Wykaz wskaźników zamieszczony jest w zał. 3 rozporządzeniu  Ministra Infrastruktury z dnia 13 lipca 2021 r. w sprawie form i sposobu prowadzenia monitoringu jednolitych części wód powierzchniowych i jednolitych części wód podziemnych [https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20210001576](https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20210001576) |
| rok | query | True | integer | {"minimum":2022,"maximum":9999} | Rok badania (dane dostępne od 2022 roku) |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `JwodaProgramyMonitoringuOdpowiedz`

## Pełny słownik schematów

### `JwodaProgramyMonitoringuRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| jcwpKod | string | True | {"maxLength":30} | Kod jednolitej części wód powierzchniowych (jcwp) |
| jcwpNazwa | string | True | {"maxLength":200} | Nazwa jednolitej części wód powierzchniowych (jcwp) |
| ppkKod | string | False | {"maxLength":50} | Kod punktu pomiarowo-kontrolnego (ppk) |
| ppkNazwa | string | False | {"maxLength":150} | Nazwa punktu pomiarowo-kontrolnego (ppk) |
| wojewodztwo | WojewodztwoEnum | True | {} | Województwo |
| wskaznik | string | False | {"maxLength":200} | Nazwa wskaźnika |
| rok | string | True | {} | Rok badania |

### `JwodaProgramyMonitoringuOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of JwodaProgramyMonitoringuRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `WojewodztwoEnum`



```json
{
  "type": "string",
  "enum": [
    "DOLNOŚLĄSKIE",
    "KUJAWSKO-POMORSKIE",
    "LUBELSKIE",
    "LUBUSKIE",
    "ŁÓDZKIE",
    "MAŁOPOLSKIE",
    "MAZOWIECKIE",
    "OPOLSKIE",
    "PODKARPACKIE",
    "PODLASKIE",
    "POMORSKIE",
    "ŚLĄSKIE",
    "ŚWIĘTOKRZYSKIE",
    "WARMIŃSKO-MAZURSKIE",
    "WIELKOPOLSKIE",
    "ZACHODNIOPOMORSKIE"
  ]
}
```

### `WynikTyp`

Wynik wykonania operacji

| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| idZdarzenia | string / uuid | True | {"examples":["e1933560-9691-4ff5-9335-6096911ff5fa"]} | Unikalny identyfikator zdarzenia (UUID) |
| status | string | True | {"enum":["SUKCES","BLAD"]} | Status wykonania operacji |
| data | string / date-time | True | {} | Data i czas wykonania operacji (ISO 8601, UTC) |
| blad | BladTyp | False | {} |  |

### `BladTyp`

Szczegóły błędu występującego podczas przetwarzania

| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| kod | string | True | {} | Kod błędu zgodny z katalogiem błędów systemu |
| opis | string | True | {} | Szczegółowy opis błędu |
