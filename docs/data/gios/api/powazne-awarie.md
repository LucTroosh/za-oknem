# PA API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-powazne-awarie.yaml. Pobrano 2026-10-03. SHA-256: `03506cbbf07df19b2b677a4823488f41e19d01097f70e4c9a782b9fb6d7b68c0`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/powazne-awarie

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/powazne-awarie`

Poważne Awarie

Usługa sieciowa udostępniająca dane dotyczące poważnych awarii objętych obowiązkiem zgłoszenia do GIOŚ

operationId: `getPowazneAwarieV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rok | query | False | integer | {"minimum":2017,"maximum":9999} | Rok (dane dostępne od 2017 roku) |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |
| powiat | query | False | string | {"maxLength":80} | Powiat, np. 'miński', 'kutnowski' |
| gmina | query | False | string | {"maxLength":80} | Gmina, np. 'Mińsk Mazowiecki', 'Kutno' |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PaPowazneAwarieOdpowiedz`

### GET `/v1/zaklady`

Zakłady stwarzające zagrożenie wystąpienia poważnej awarii przemysłowej

Usługa sieciowa udostępniająca dane o zakładach stwarzających zagrożenie wystąpienia poważnej awarii przemysłowej - zakładach o zwiększonym ryzyku (ZZR) i zakładach o dużym ryzyku (ZDR) wystąpienia poważnej awarii przemysłowej. Dane udostępniane według stanu na dzień dzisiejszy.

operationId: `getZakladyV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| klasyfikacjaZakladu | query | False | PaKlasyfikacjaZakladuEnum | {"enum":["ZZR","ZDR"]} | Klasyfikacja zakładu |
| regon | query | False | string | {"maxLength":9} | REGON |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PaZakladyOdpowiedz`

## Pełny słownik schematów

### `PaPowazneAwarieRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| data | string | False | {"maxLength":10} | Data |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| powiat | string | False | {"maxLength":80} | Powiat |
| gmina | string | False | {"maxLength":80} | Gmina |
| kodPocztowy | string | False | {"maxLength":6} | Kod pocztowy |
| miejscowosc | string | False | {"maxLength":80} | Miejscowość |
| miejsceZdarzenia | string | False | {"maxLength":32} | Miejsce zdarzenia |
| rodzajTransportu | string | False | {"maxLength":32} | Rodzaj transportu |
| klasyfikacjaZakladu | PaKlasyfikacjaZakladuEnum | False | {} | Klasyfikacja zakładu |
| rodzajZdarzenia | string | False | {} | Rodzaj zdarzenia |
| zrodloZdarzenia | string | False | {"maxLength":30} | Źródło zdarzenia |
| opisZdarzenia | string | False | {"maxLength":1000} | Opis zdarzenia |

### `PaPowazneAwarieOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PaPowazneAwarieRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PaZakladyRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| klasyfikacjaZakladu | PaKlasyfikacjaZakladuEnum | False | {} | Klasyfikacja zakładu |
| nazwaZakladu | string | False | {"maxLength":256} | Nazwa zakładu |
| regon | string | False | {"maxLength":9} | REGON |
| rodzajDzialalnosci | string | False | {"maxLength":255} | Rodzaj działalności |
| kodNace | string | False | {"maxLength":20} | Kod NACE |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| powiat | string | False | {"maxLength":80} | Powiat |
| gmina | string | False | {"maxLength":80} | Gmina |
| kodPocztowy | string | False | {"maxLength":6} | Kod pocztowy |
| miejscowosc | string | False | {"maxLength":80} | Miejscowość |
| ulica | string | False | {"maxLength":120} | Ulica |
| stronaWww | string | False | {"maxLength":254} | Adres strony internetowej zakładu |

### `PaZakladyOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PaZakladyRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PaKlasyfikacjaZakladuEnum`



```json
{
  "type": "string",
  "enum": [
    "ZZR",
    "ZDR"
  ]
}
```

### `WojewodztwoEnum`



```json
{
  "type": "string",
  "enum": [
    "dolnośląskie",
    "kujawsko-pomorskie",
    "lubelskie",
    "lubuskie",
    "łódzkie",
    "małopolskie",
    "mazowieckie",
    "opolskie",
    "podkarpackie",
    "podlaskie",
    "pomorskie",
    "śląskie",
    "świętokrzyskie",
    "warmińsko-mazurskie",
    "wielkopolskie",
    "zachodniopomorskie"
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
