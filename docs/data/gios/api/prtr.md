# PRTR API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-prtr.yaml. Pobrano 2026-10-03. SHA-256: `1f9d74b14af08215421e685a1afd3effaefb7934393155fa532b07fca75bb2dc`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/prtr

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/uwolnienia`

Uwolnienia i transfery zanieczyszczeń

Usługa sieciowa udostępniająca informacje o typie i ilości uwolnień zanieczyszczeń do środowiska oraz transferów zanieczyszczeń

operationId: `getUwolnieniaITransferyZanieczyszczenV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| typUwolnienia | query | False | PrtrTypUwolnieniaEnum | {"enum":["Powietrze","Woda","Gleba","Ścieki"]} | Typ uwolnienia (powietrze, woda, gleba, ścieki) |
| rokRaportu | query | False | integer | {"minimum":2007,"maximum":9999} | Rok raportu (dane dostępne od 2007 roku) |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| miejscowosc | query | False | string | {"maximum":256} | Miejscowość |
| zaklad | query | False | string | {"maxLength":1024} | Nazwa zakładu |
| kodZanieczyszczenia | query | False | integer | {"minimum":1,"maximum":9999} | Opis kodów zanieczyszczenia znajduje się pod adresem: [https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:32006R0166#page=12](https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:32006R0166#page=12), Kod zanieczyszczenia pochodzi z kolumny Nr. Przykład: 2 |
| kodDzialalnosciGlownej | query | False | string | {"maxLength":20} | Opis kodów działalności głównej znajduje się pod adresem: [https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:32006R0166#page=8](https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:32006R0166#page=8), Przykład: 1.(c) |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PrtrZanieczyszczeniaOdpowiedz`

### GET `/v1/transfery`

Transfer odpadów poza miejsce powstawania

Usługa sieciowa udostępniająca informacje o ilości odpadów transferowanych poza miejsce powstawania

operationId: `getTransferOdpadowPozaMiejscePowstawaniaV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| typTransferu | query | False | PrtrTypTransferuEnum | {"enum":["Transfer odpadów niebezpiecznych w granicach kraju","Transfer odpadów niebezpiecznych do innych krajów","Transfer odpadów innych niż niebezpieczne"]} | Typ transferu |
| rokRaportu | query | False | integer | {"minimum":2007,"maximum":9999} | Rok raportu (dane dostępne od 2007 roku) |
| procesZagospodarowaniaOdpadow | query | False | PrtrProcesZagospodarowaniaOdpadowEnum | {"enum":["R","D"]} | Proces zagospodarowania odpadów, R - odzysk, D - unieszkodliwianie |
| kodDzialalnosciGlownej | query | False | string | {"maxLength":20} | Opis kodów działalności głównej znajduje się pod adresem: [https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:32006R0166#page=8](https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:32006R0166#page=8), Przykład: 1.(c) |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PrtrTransportOdpadowOdpowiedz`

## Pełny słownik schematów

### `PrtrZanieczyszczeniaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| typUwolnienia | PrtrTypUwolnieniaEnum | True | {} | Typ uwolnienia |
| lacznaIlosc | string | False | {} | Łączna ilość |
| zanieczyszczenie | string | True | {"maxLength":255} | Zanieczyszczenie |
| kodZanieczyszczenia | integer | False | {} | Kod zanieczyszczenia |
| dzialalnoscGlowna | string | True | {"maxLength":1000} | Działalność główna |
| kodDzialalnosciGlownej | string | False | {"maxLength":20} | Kod działalności głównej |
| rokRaportu | integer | True | {"examples":[2021]} | Rok raportu |
| zaklad | string | False | {"maxLength":1024} | Zakład |
| regon | string | False | {"maxLength":20} | Regon |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| powiat | string | False | {"maxLength":240} | Powiat |
| miejscowosc | string | True | {"maxLength":256} | Miejscowość |

### `PrtrZanieczyszczeniaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PrtrZanieczyszczeniaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PrtrTransportOdpadowRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| masaOdpadow | string | False | {} | Masa odpadów |
| procesZagospodatrowaniaOdpadow | PrtrProcesZagospodarowaniaOdpadowEnum | False | {} | Proces zagospodarowania odpadów |
| typTransferu | PrtrTypTransferuEnum | False | {} | Typ transferu |
| dzialalnoscGlowna | string | False | {"maxLength":1000} | Działalność główna |
| kodDzialalnosciGlownej | string | False | {"maxLength":20} | Kod działalności głównej |
| rokRaportu | integer | False | {} | Rok raportu |
| zaklad | string | False | {"maxLength":1024} | Zakład |
| regon | string | False | {"maxLength":20} | Regon |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| powiat | string | False | {"maxLength":240} | Powiat |
| miejscowosc | string | False | {"maxLength":256} | Miejscowość |

### `PrtrTransportOdpadowOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PrtrTransportOdpadowRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PrtrTypUwolnieniaEnum`



```json
{
  "type": "string",
  "enum": [
    "Powietrze",
    "Woda",
    "Gleba",
    "Ścieki"
  ]
}
```

### `PrtrProcesZagospodarowaniaOdpadowEnum`

Proces zagospodarowania odpadów, R - odzysk, D - unieszkodliwianie

```json
{
  "type": "string",
  "description": "Proces zagospodarowania odpadów, R - odzysk, D - unieszkodliwianie",
  "enum": [
    "R",
    "D"
  ]
}
```

### `PrtrRodzajOdpadowEnum`



```json
{
  "type": "string",
  "enum": [
    "Niebezpieczne",
    "Inne niż niebezpieczne"
  ]
}
```

### `PrtrTypTransferuEnum`



```json
{
  "type": "string",
  "enum": [
    "Transfer odpadów niebezpiecznych w granicach kraju",
    "Transfer odpadów niebezpiecznych do innych krajów",
    "Transfer odpadów innych niż niebezpieczne"
  ]
}
```

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
