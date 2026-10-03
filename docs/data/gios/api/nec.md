# NEC API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-nec.yaml. Pobrano 2026-10-03. SHA-256: `1f2ae40926ad348eb4ae1c26187c348a80cb16fac892ab929e175cfbf02e4c88`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/nec

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/monitorowanie/stanowiska`

Wykaz lokalizacji stacji do monitorowania negatywnego wpływu zanieczyszczenia powietrza na te ekosystemy

Usługa sieciowa udostępniająca listę stacji/stanowisk do monitorowania negatywnego wpływu zanieczyszczeń powietrza na ekosystemy na potrzeby dyrektywy NEC

operationId: `getMonitorowanieStanowiskaV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rokRaportowania | query | True | integer | {"minimum":2019,"maximum":9999} | Rok raportowania. Oznacza rok przekazania danych do Komisji Europejskiej w ramach dyrektywy NEC. Raporty dostępne od roku 2019 i kolejno co 4 lata. Przykładowo, dane dla 2019 roku dotyczą wykazu stacji wybranych w 2018 r. dla których w 2019 r. zestawiono wyniki monitoringu. |
| regionBiogeograficzny | query | False | NecRegionBiogeograficznyEnum | {"enum":["kontynentalny","alpejski"]} | Region biogeograficzny |
| typEkosystemuMAES | query | False | NecTypEkosystemuMAESEnum | {"enum":["ekosystem miejski","lasy i inne tereny zadrzewione","uprawy, łąki i tereny trawiaste","wrzosowiska i zarośla","tereny skąpo porośnięte roślinnością","tereny podmokłe","rzeki i jeziora","inne"]} | Typ ekosystemu wg klasyfikacji MAES |
| statusObszaru | query | False | NecStatusObszaruEnum | {"enum":["objęty ochroną","nieobjęty ochroną"]} | Status obszaru |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `NecMonitorowanieStanowiskaOdpowiedz`

### GET `/v1/monitorowanie/wskazniki`

Wykaz wskaźników używanych do monitorowania negatywnego wpływu zanieczyszczenia powietrza na ekosystemy

Usługa sieciowa udostępniająca informacje o wskaźnikach używanych do monitorowania negatywnego wpływu zanieczyszczenia powietrza na ekosystemy na potrzeby dyrektywy NEC

operationId: `getMonitorowanieParametryV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rodzajEkosystemu | query | False | NecRodzajEkosystemuEnum | {"enum":["lądowy","wodny"]} | Rodzaj ekosystemu |
| rokRaportowania | query | False | integer | {"minimum":2019,"maximum":9999} | Rok raportowania. Oznacza rok przekazania danych do Komisji Europejskiej w ramach dyrektywy NEC. Raporty dostępne od roku 2019 i kolejno co 4 lata. Przykładowo, dane dla 2019 roku dotyczą wykazu stacji wybranych w 2018 r. dla których w 2019 r. zestawiono wyniki monitoringu. |
| krajowyKodStacji | query | False | string | {"maxLength":1000} | Krajowy kod stacji |
| nazwaStacji | query | False | string | {"maxLength":1000} | Nazwa stacji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `NecMonitorowanieWskaznikiOdpowiedz`

### GET `/v1/monitorowanie/wyniki`

Dane uzyskane w wyniku monitorowania negatywnego wpływu zanieczyszczenia powietrza na ekosystemy

Usługa sieciowa udostępniająca wyniki monitorowania wpływu zanieczyszczeń powietrza na ekosystemy na potrzeby dyrektywy NEC

operationId: `getMonitorowanieWynikiV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rokRaportowania | query | True | integer | {"minimum":2019,"maximum":9999} | Rok raportowania. Oznacza rok przekazania danych do Komisji Europejskiej w ramach dyrektywy NEC. Raporty dostępne od roku 2019 i kolejno co 4 lata. Przykładowo, dane dla 2019 roku dotyczą wykazu stacji wybranych w 2018 r. dla których w 2019 r. zestawiono wyniki monitoringu. |
| rokWykonaniaPomiaru | query | False | integer | {"minimum":1990,"maximum":9999} | Rok wykonania pomiaru |
| regionBiogeograficzny | query | False | NecRegionBiogeograficznyEnum | {"enum":["kontynentalny","alpejski"]} | Region biogeograficzny |
| typEkosystemuMAES | query | False | NecTypEkosystemuMAESEnum | {"enum":["ekosystem miejski","lasy i inne tereny zadrzewione","uprawy, łąki i tereny trawiaste","wrzosowiska i zarośla","tereny skąpo porośnięte roślinnością","tereny podmokłe","rzeki i jeziora","inne"]} | Typ ekosystemu wg klasyfikacji MAES |
| statusObszaru | query | False | NecStatusObszaruEnum | {"enum":["objęty ochroną","nieobjęty ochroną"]} | Status obszaru |
| krajowyKodStacji | query | False | string | {"maxLength":1000} | Krajowy kod stacji |
| nazwaStacji | query | False | string | {"maxLength":1000} | Nazwa stacji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `NecMonitorowanieWynikiOdpowiedz`

## Pełny słownik schematów

### `NecMonitorowanieStanowiskaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rokRaportowania | integer | False | {} | Rok raportowania |
| kodKraju | string | False | {} | Kod kraju |
| krajowyKodStacji | string | False | {} | Krajowy kod stacji |
| nazwaStacji | string | False | {} | Nazwa stacji |
| kodEuropejski | string | False | {} | Kod Europejski |
| kodStacjiMonitoringowejRDW | string | False | {} | Kod stacji monitoringowej RDW |
| kodJCWP | string | False | {} | Kod JCWP |
| nazwaSieciMonitoringu | string | False | {} | Nazwa sieci monitoringu |
| dlugoscGeograficzna | string | False | {} | Lokalizacja stacji - długość geograficzna |
| szerokoscGeograficzna | string | False | {} | Lokalizacja stacji - szerokość geograficzna |
| typEkosystemuMAES | NecTypEkosystemuMAESEnum | False | {} | Typ ekosystemu wg klasyfikacji MAES (ekosystem miejski, lasy i inne tereny zadrzewione, uprawy, łąki i tereny trawiaste, wrzosowiska i zarośla, tereny skąpo porośnięte roślinnością, tereny podmokłe, rzeki i jeziora i inne) |
| typEkosystemuEUNIS | string | False | {} | Typ ekosystemu wg klasyfikacji EUNIS |
| statusObszaru | NecStatusObszaruEnum | False | {} | Status obszaru (objęty ochroną, nieobjęty ochroną, nieznany) |
| regionBiogeograficzny | NecRegionBiogeograficznyEnum | False | {} | Region biogeograficzny (ALP, CON) |
| parametry | array of ParametrStacji | False | {} | Lista parametrów stacji |

### `ParametrStacji`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| nazwa | string | False | {} |  |
| wartosc | string | False | {} |  |

### `NecMonitorowanieStanowiskaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of NecMonitorowanieStanowiskaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `NecMonitorowanieWskaznik`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rodzajEkosystemu | NecRodzajEkosystemuEnum | False | {} | Rodzaj ekosystemu |
| klasa | string | False | {} | Klasa wskaźnika |
| nazwa | string | False | {} | Nazwa wskaźnika |
| jednostka | string | False | {} | Jednostka miary |

### `NecMonitorowanieWskaznikiRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rokRaportowania | integer | False | {} | Rok raportowania |
| krajowyKodStacji | string | False | {} | Krajowy kod stacji |
| nazwaStacji | string | False | {} | Nazwa stacji |
| wskazniki | array of NecMonitorowanieWskaznik | False | {} |  |

### `NecMonitorowanieWskaznikiOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of NecMonitorowanieWskaznikiRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `NecMonitorowanieWynik`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| wskaznik | NecMonitorowanieWskaznik | False | {} |  |
| wartosc | string | False | {} | Wartość |

### `NecMonitorowanieWynikiRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| krajowyKodStacji | string | False | {} | Krajowy kod stacji |
| nazwaStacji | string | False | {} | Nazwa stacji |
| rokRaportowania | integer | False | {} | Rok raportowania |
| rokWykonaniaPomiaru | integer | False | {} | Rok wykonania pomiaru |
| miesiacWykonaniaPomiaru | integer | False | {} | Miesiąc wykonania pomiaru |
| dzienWykonaniaPomiaru | integer | False | {} | Dzień wykonania pomiaru |
| regionBiogeograficzny | NecRegionBiogeograficznyEnum | False | {} | Region biogeograficzny (ALP, CON) |
| typEkosystemuMAES | NecTypEkosystemuMAESEnum | False | {} | Typ ekosystemu wg klasyfikacji MAES (ekosystem miejski, lasy i inne tereny zadrzewione, uprawy, łąki i tereny trawiaste, wrzosowiska i zarośla, tereny skąpo porośnięte roślinnością, tereny podmokłe, rzeki i jeziora i inne) |
| statusObszaru | NecStatusObszaruEnum | False | {} | Status obszaru (objęty ochroną, nieobjęty ochroną, nieznany) |
| wyniki | array of NecMonitorowanieWynik | False | {} |  |

### `NecMonitorowanieWynikiOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of NecMonitorowanieWynikiRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `NecRegionBiogeograficznyEnum`



```json
{
  "type": "string",
  "enum": [
    "kontynentalny",
    "alpejski"
  ]
}
```

### `NecRodzajEkosystemuEnum`



```json
{
  "type": "string",
  "enum": [
    "lądowy",
    "wodny"
  ]
}
```

### `NecStatusObszaruEnum`



```json
{
  "type": "string",
  "enum": [
    "objęty ochroną",
    "nieobjęty ochroną"
  ]
}
```

### `NecTypEkosystemuMAESEnum`



```json
{
  "type": "string",
  "enum": [
    "ekosystem miejski",
    "lasy i inne tereny zadrzewione",
    "uprawy, łąki i tereny trawiaste",
    "wrzosowiska i zarośla",
    "tereny skąpo porośnięte roślinnością",
    "tereny podmokłe",
    "rzeki i jeziora",
    "inne"
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
