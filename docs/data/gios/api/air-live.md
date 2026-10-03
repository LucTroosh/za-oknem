# OpenAPI definition — katalog development

Źródło: https://api.gios.gov.pl/pjp-api/v3/api-docs. Pobrano 2026-10-03. SHA-256: `72424ad45519e48001de16bfac6148c03aa7de6158fa4062e4d8e1dcb363db54`.

OpenAPI: 3.0.1; wersja: v0.

Base URL: https://api.gios.gov.pl/pjp-api

Licencja deklarowana: {}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

Uwaga wdrożeniowa: spec zawiera także starsze `/rest/...` i operacje portalowe. Dla czterech podstawowych usług stosować wyłącznie `/v1/rest/...` zgodnie z oficjalną informacją o wycofaniu starszych wersji 30.06.2025. Pozostałe pozycje są inwentaryzacją schematu; nie integrować ich bez osobnego gate.

## Operacje

### GET `/version`



Usługa sieciowa udostępniająca aktualną wersję API

operationId: `getVersion`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; application/json → `VersionDTO`

### GET `/rest/statistics/getStatisticsForPollutants`



Usługa sieciowa udostępniająca statystyki roczne od roku 2000 dla SO2, NO2, NOx, CO, O3, C6H6, PM10, PM2,5, Pb(PM10), As(PM10), Cd(PM10), Ni(PM10), BaP(PM10), WWA(PM10), Jony(PM2,5), Hg(TGM), formaldehyd, depozycja, wraz z ich parametrami

https://api.gios.gov.pl/pjp-api/v1/rest/statistics/getStatisticsForPollutants.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/statistics/getStatisticsForPollutants?indicator=O3

operationId: `getStatistics`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Województwo. <br /> Dostępne atrybuty:    <br /> Województwo - parametr dla nazwy województwa<br />  |
| indicator | query | True | string | {} | SO2, NO2, NOx, CO, O3, C6H6, PM10, PM2,5, Pb(PM10), As(PM10), Cd(PM10), Ni(PM10), BaP(PM10), WWA(PM10), Jony(PM2,5), Hg(TGM), Formaldehyd, Depozycja |
| filter[wojewodztwo] | query | False | string | {} | Województwo np. śląskie, kujawsko-pomorskie. Wartości parametrów należy oddzielać przecinkiem. |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `StatisticsLdDTO`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/statistics/getStatisticsForPollutants`



Usługa sieciowa udostępniająca statystyki roczne od roku 2000 dla SO2, NO2, NOx, CO, O3, C6H6, PM10, PM2,5, Pb(PM10), As(PM10), Cd(PM10), Ni(PM10), BaP(PM10), WWA(PM10), Jony(PM2,5), Hg(TGM), formaldehyd, depozycja, wraz z ich parametrami

https://api.gios.gov.pl/pjp-api/v1/rest/statistics/getStatisticsForPollutants.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/statistics/getStatisticsForPollutants?indicator=O3

operationId: `getStatistics_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Województwo. <br /> Dostępne atrybuty:    <br /> Województwo - parametr dla nazwy województwa<br />  |
| indicator | query | True | string | {} | SO2, NO2, NOx, CO, O3, C6H6, PM10, PM2,5, Pb(PM10), As(PM10), Cd(PM10), Ni(PM10), BaP(PM10), WWA(PM10), Jony(PM2,5), Hg(TGM), Formaldehyd, Depozycja |
| filter[wojewodztwo] | query | False | string | {} | Województwo np. śląskie, kujawsko-pomorskie. Wartości parametrów należy oddzielać przecinkiem. |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `StatisticsLdDTO`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/station/sensors/{stationId}`

Pobierz listę czujników stacji pomiarowej

Usługa sieciowa udostępniająca listę stanowisk pomiarowych dostępnych na wybranej stacji pomiarowej.

https://api.gios.gov.pl/pjp-api/v1/rest/station/sensors/{stationId}.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/station/sensors/52

operationId: `getAutomaticAndManualSensors`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwy atrybutu. Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny. Domyślne sortowanie odbywa się rosnąco po atrybucie Identyfikator stanowiska. Dostępne atrybuty: Id - parametr dla identyfikatora stanowiska |
| stationId | path | True | integer / int64 | {} | Identyfikator stacji pomiarowej np. 52. Lista stacji i stanowisk pomiarowych wraz z ich id udostępniana jest poprzez usługi API 'Stacje pomiarowe i stanowiska pomiarowe' |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/json → `DataException`

- HTTP 404: Nie znaleziono; application/json → `DataException`

- HTTP 200: OK; application/ld+json → `SensorLd`

- HTTP 201: Utworzono nowy zasób; application/json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/json → `DataException`

- HTTP 204: Brak zawartości; application/json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/json → `DataException`

- HTTP 400: Błędne żądanie; application/json → `DataException`

- HTTP 401: Brak autoryzacji; application/json → `DataException`

- HTTP 403: Dostęp zabroniony; application/json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/json → `DataException`

- HTTP 409: Konflikt; application/json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/json → `DataException`

### GET `/v1/rest/station/findAll`

Pobierz listę stacji pomiarowych

Usługa sieciowa udostępniająca listę stacji pomiarowych

https://api.gios.gov.pl/pjp-api/v1/rest/station/findAll.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/station/findAll

operationId: `getAutomaticAndManualStation`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Identyfikator stacji<br /> Dostępne atrybuty:    <br /> Id - parametr dla identyfikatora stacji,<br />  |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/json → `DataException`

- HTTP 404: Nie znaleziono; application/json → `DataException`

- HTTP 200: OK; application/ld+json → `StationLd`

- HTTP 201: Utworzono nowy zasób; application/json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/json → `DataException`

- HTTP 204: Brak zawartości; application/json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/json → `DataException`

- HTTP 400: Błędne żądanie; application/json → `DataException`

- HTTP 401: Brak autoryzacji; application/json → `DataException`

- HTTP 403: Dostęp zabroniony; application/json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/json → `DataException`

- HTTP 409: Konflikt; application/json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/json → `DataException`

### GET `/v1/rest/metadata/stations`



Usługa sieciowa udostępniająca metadane stacji pomiarowych: kod stacji, międzynarodowy kod stacji, nazwa stacji, stary kod stacji, data uruchomienia, data zamknięcia, typ stacji, typ obszaru, rodzaj stacji, województwo, miejscowość, ulica, współrzędne geograficzne (WGS84 φ N, WGS84 λ E)

https://api.gios.gov.pl/pjp-api/v1/rest/metadata/stations.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/metadata/stations

operationId: `getStationMetadata`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Kod stacji <br /> Dostępne atrybuty:    <br /> Kod - parametr dla Kodu stacji |
| filter[miejscowosc] | query | False | string | {} | Miejscowość np. Białka,Bielawa,Bogatynia,Brzeg Głogowski,Czarna Góra,Duszniki-Zdrój,Dzierżoniów . W przypadku wyboru dwóch należy oddzielić je znakiem przecinka (,) |
| filter[kod-stacji] | query | False | string | {} | Kod stacji np. DsBialka, DsBielGrot, DsBogChop, DsBoleslaMOB. W przypadku wyboru kilku kodów stacji należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `StationMetaDataLdDTO`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/metadata/stations`



Usługa sieciowa udostępniająca metadane stacji pomiarowych: kod stacji, międzynarodowy kod stacji, nazwa stacji, stary kod stacji, data uruchomienia, data zamknięcia, typ stacji, typ obszaru, rodzaj stacji, województwo, miejscowość, ulica, współrzędne geograficzne (WGS84 φ N, WGS84 λ E)

https://api.gios.gov.pl/pjp-api/v1/rest/metadata/stations.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/metadata/stations

operationId: `getStationMetadata_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Kod stacji <br /> Dostępne atrybuty:    <br /> Kod - parametr dla Kodu stacji |
| filter[miejscowosc] | query | False | string | {} | Miejscowość np. Białka,Bielawa,Bogatynia,Brzeg Głogowski,Czarna Góra,Duszniki-Zdrój,Dzierżoniów . W przypadku wyboru dwóch należy oddzielić je znakiem przecinka (,) |
| filter[kod-stacji] | query | False | string | {} | Kod stacji np. DsBialka, DsBielGrot, DsBogChop, DsBoleslaMOB. W przypadku wyboru kilku kodów stacji należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `StationMetaDataLdDTO`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/metadata/sensors`



Usługa sieciowa udostępniająca metadane stanowisk pomiarowych: kod stanowiska, kod stacji, nazwa stacji, stary kod stacji, wskaźnik – kod, wskaźnik, czas uśredniania, typ pomiaru, data uruchomienia, data zamknięcia, województwo, nazwa strefy

https://api.gios.gov.pl/pjp-api/v1/rest/metadata/sensors.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/metadata/sensors

operationId: `getSensorsMetadata`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Kod stacji <br /> Dostępne atrybuty:    <br /> Kod - parametr dla Kodu stacji |
| filter[typ-pomiaru] | query | False | string | {} | Typ pomiaru: automatyczny lub manualny. W przypadku wyboru dwóch należy oddzielić je znakiem przecinka (,) |
| filter[kod-stacji] | query | False | string | {} | Kod stacji np. DsBialka, DsBielGrot, DsBogChop, DsBoleslaMOB. W przypadku wyboru kilku kodów stacji należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `SensorMetaDataLdDTO`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/metadata/sensors`



Usługa sieciowa udostępniająca metadane stanowisk pomiarowych: kod stanowiska, kod stacji, nazwa stacji, stary kod stacji, wskaźnik – kod, wskaźnik, czas uśredniania, typ pomiaru, data uruchomienia, data zamknięcia, województwo, nazwa strefy

https://api.gios.gov.pl/pjp-api/v1/rest/metadata/sensors.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/metadata/sensors

operationId: `getSensorsMetadata_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny.  <br /> Domyślne sortowanie odbywa się rosnąco po atrybucie Kod stacji <br /> Dostępne atrybuty:    <br /> Kod - parametr dla Kodu stacji |
| filter[typ-pomiaru] | query | False | string | {} | Typ pomiaru: automatyczny lub manualny. W przypadku wyboru dwóch należy oddzielić je znakiem przecinka (,) |
| filter[kod-stacji] | query | False | string | {} | Kod stacji np. DsBialka, DsBielGrot, DsBogChop, DsBoleslaMOB. W przypadku wyboru kilku kodów stacji należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `SensorMetaDataLdDTO`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/levels/getWarnings`





operationId: `getWarnings`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of AlarmLevelDTO`

### GET `/rest/levels/getWarnings`





operationId: `getWarnings_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of AlarmLevelDTO`

### GET `/rest/levels/getPermissible`





operationId: `getPermissible`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of AlarmLevelDTO`

### GET `/v1/rest/levels/getPermissible`





operationId: `getPermissible_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of AlarmLevelDTO`

### GET `/v1/rest/levels/getInformationAboutExceeding`

Pobierz informacje o przekroczeniach

Usługa sieciowa udostępniająca aktywne informacje o przekroczeniu poziomu informowania, alarmowego, dopuszczalnego i docelowego zanieczyszczeń 

https://api.gios.gov.pl/pjp-api/v1/rest/levels/getInformationAboutExceeding.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/levels/getInformationAboutExceeding

operationId: `getInformationAboutExceeding`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny. Domyśle sortowanie odbywa się malejąco po  parametrze Data i godzina.<br /> Dostępne atrybuty:    <br /> Województwo - parametr dla nazwy województwa.<br />Data - parametr dla Data i godzina |
| filter[wojewodztwo] | query | False | string | {} | Województwo np. ŚLĄSKIE, WARMIŃSKO-MAZURSKIE, KUJAWSKO-POMORSKIE, MAŁOPOLSKIE. W przypadku wyboru kilku województw należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ExceedingLdDTO`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/levels/getInformationAboutExceeding`

Pobierz informacje o przekroczeniach

Usługa sieciowa udostępniająca aktywne informacje o przekroczeniu poziomu informowania, alarmowego, dopuszczalnego i docelowego zanieczyszczeń 

https://api.gios.gov.pl/pjp-api/v1/rest/levels/getInformationAboutExceeding.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/levels/getInformationAboutExceeding

operationId: `getInformationAboutExceeding_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny. Domyśle sortowanie odbywa się malejąco po  parametrze Data i godzina.<br /> Dostępne atrybuty:    <br /> Województwo - parametr dla nazwy województwa.<br />Data - parametr dla Data i godzina |
| filter[wojewodztwo] | query | False | string | {} | Województwo np. ŚLĄSKIE, WARMIŃSKO-MAZURSKIE, KUJAWSKO-POMORSKIE, MAŁOPOLSKIE. W przypadku wyboru kilku województw należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ExceedingLdDTO`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/data/getData/{idSensor}`

Usługa sieciowa udostępniająca dane pomiarowe w formacie JSON-LD.

Usługa sieciowa udostępniająca dane pomiarowe na podstawie podanego identyfikatora stanowiska pomiarowego typu automatycznego. Dla stanowiska typu manualnego wyniki pomiarów nie są dostępne na bieżąco, są one udostępniane po 4-8 tygodniach od poboru próby przez usługę API „Archiwalne dane pomiarowe”

https://api.gios.gov.pl/pjp-api/v1/rest/data/getData/{idSensor}.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/data/getData/52

operationId: `getData`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu. Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny.<br>Domyślne sortowanie odbywa się malejąco po atrybucie Data.<br>Dostępne atrybuty:<br>Data - parametr dla daty, |
| idSensor | path | True | integer / int64 | {} | Identyfikator stanowiska np. 52<br>Lista stacji i stanowisk pomiarowych wraz z ich id udostępniana jest poprzez usługi API "Stacje pomiarowe i stanowiska pomiarowe” |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `CurrentDataDTO`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

### GET `/v1/rest/concentration/getDistributionsOfConcentrationsMap`



Usługa sieciowa udostępniająca dane prezentowane na mapach rozkładów stężeń z wybranego roku kalendarzowego, dla wybranego zanieczyszczenia, w podziale na kryterium ochrony zdrowia i ochrony roślin.

https://api.gios.gov.pl/pjp-api/v1/rest/concentration/getDistributionsOfConcentrationsMap.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca plik do pobrania, zawierający dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/concentration/getDistributionsOfConcentrationsMap?year=2020&indicatorType=OZ&indicator=PM10_sr_roczna

operationId: `getDistributionsOfConcentrationsMap`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| year | query | True | integer / int32 | {} | Rok - dostępne są dane od 2019 roku |
| indicatorType | query | True | string | {} | Typ wskaźnika: OZ - Ochrona zdrowia, OR - Ochrona roślin |
| indicator | query | True | string | {} | Wskaźnik ochrona zdrowia (OZ): PM10_sr_roczna, PM25_sr_roczna, NO2_sr_roczna, O3_3letnia, BaP_sr_roczna, SO2_25h_max, PM10_36_max, NO2_19h_max, SO2_4_max </br>Wskaźnik ochrona roślin (OR): SO2_sr_roczna, NOx_sr_roczna, O3_5letnia |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ConcentrationDistributionsDTO`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/concentration/getDistributionsOfConcentrationsMap`



Usługa sieciowa udostępniająca dane prezentowane na mapach rozkładów stężeń z wybranego roku kalendarzowego, dla wybranego zanieczyszczenia, w podziale na kryterium ochrony zdrowia i ochrony roślin.

https://api.gios.gov.pl/pjp-api/v1/rest/concentration/getDistributionsOfConcentrationsMap.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca plik do pobrania, zawierający dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/concentration/getDistributionsOfConcentrationsMap?year=2020&indicatorType=OZ&indicator=PM10_sr_roczna

operationId: `getDistributionsOfConcentrationsMap_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| year | query | True | integer / int32 | {} | Rok - dostępne są dane od 2019 roku |
| indicatorType | query | True | string | {} | Typ wskaźnika: OZ - Ochrona zdrowia, OR - Ochrona roślin |
| indicator | query | True | string | {} | Wskaźnik ochrona zdrowia (OZ): PM10_sr_roczna, PM25_sr_roczna, NO2_sr_roczna, O3_3letnia, BaP_sr_roczna, SO2_25h_max, PM10_36_max, NO2_19h_max, SO2_4_max </br>Wskaźnik ochrona roślin (OR): SO2_sr_roczna, NOx_sr_roczna, O3_5letnia |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ConcentrationDistributionsDTO`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/archivalData/getDataForAllStationsByYearAndVoivodeship`



Usługa sieciowa udostępniająca archiwalne wyniki pomiarów automatycznych i manualnych z wybranego roku kalendarzowego (również trwającego), dla wybranego zanieczyszczenia lub wszystkich łącznie, ze wszystkich stacji w wybranym województwie

https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStationsByYearAndVoivodeship.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStationsByYearAndVoivodeship?year=2021&voivodeship=ŚLĄSKIE

operationId: `getDataForAllStationsByYearAndVoivodeship`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się rosnąco po atrybutach Kod stanowiska oraz Data. <br /> Dostępne atrybuty:    <br /> Data - parametr dla daty, <br />Kod - parametr dla kodu stanowiska  |
| year | query | True | string | {} | Rok, np. 2020. |
| voivodeship | query | True | string | {} | Województwo, np. ŚLĄSKIE, WARMIŃSKO-MAZURSKIE, KUJAWSKO-POMORSKIE, MAŁOPOLSKIE. |
| pollution | query | False | string | {} | Dostępne zanieczyszczenia: 123trimetylobenzen, 124trimetylobenzen, 135trimetylobenzen, 13butadien, 1buten, 1penten, 2penten, As(PM10), As(cdepoz), BaA(PM10), BaA(cdepoz), BaP(PM10), BaP(cdepoz), BbF(PM10), BbF(cdepoz), BjF(PM10), BjF(cdepoz), BkF(PM10),<br>BkF(cdepoz), C6H6, CO, Ca2+(PM2.5), Cd(PM10), Cd(cdepoz), Cl_(PM2.5), Cr(PM10), Cu(PM10), DBahA(PM10), DBahA(cdepoz), EC(PM2.5), HCl,<br>Hg(TGM), Hg(cdepoz), IP(PM10), IP(cdepoz), K+(PM2.5), Mg2+(PM2.5), NH3, NH4+(PM2.5), NO, NO2, NO3_(PM2.5), NOx,Na+(PM2.5), Ni(PM10),<br>Ni(cdepoz), O3,OC(PM2.5), PM10, PM2.5, Pb(PM10), SO2, SO42_(PM2.5), acetylen, cis2buten, etan, etylen, etylobenzen, formaldehyd, ibutan, iheksan, ioktan, ipentan, izopren, ksylen, mpksylen, nbutan, nheksan, nheptan, noktan, npentan, oksylen, propan, propen, toluen, trans2buten |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ArchivalDataDto`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/archivalData/getDataForAllStationsByYearAndVoivodeship`



Usługa sieciowa udostępniająca archiwalne wyniki pomiarów automatycznych i manualnych z wybranego roku kalendarzowego (również trwającego), dla wybranego zanieczyszczenia lub wszystkich łącznie, ze wszystkich stacji w wybranym województwie

https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStationsByYearAndVoivodeship.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStationsByYearAndVoivodeship?year=2021&voivodeship=ŚLĄSKIE

operationId: `getDataForAllStationsByYearAndVoivodeship_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się rosnąco po atrybutach Kod stanowiska oraz Data. <br /> Dostępne atrybuty:    <br /> Data - parametr dla daty, <br />Kod - parametr dla kodu stanowiska  |
| year | query | True | string | {} | Rok, np. 2020. |
| voivodeship | query | True | string | {} | Województwo, np. ŚLĄSKIE, WARMIŃSKO-MAZURSKIE, KUJAWSKO-POMORSKIE, MAŁOPOLSKIE. |
| pollution | query | False | string | {} | Dostępne zanieczyszczenia: 123trimetylobenzen, 124trimetylobenzen, 135trimetylobenzen, 13butadien, 1buten, 1penten, 2penten, As(PM10), As(cdepoz), BaA(PM10), BaA(cdepoz), BaP(PM10), BaP(cdepoz), BbF(PM10), BbF(cdepoz), BjF(PM10), BjF(cdepoz), BkF(PM10),<br>BkF(cdepoz), C6H6, CO, Ca2+(PM2.5), Cd(PM10), Cd(cdepoz), Cl_(PM2.5), Cr(PM10), Cu(PM10), DBahA(PM10), DBahA(cdepoz), EC(PM2.5), HCl,<br>Hg(TGM), Hg(cdepoz), IP(PM10), IP(cdepoz), K+(PM2.5), Mg2+(PM2.5), NH3, NH4+(PM2.5), NO, NO2, NO3_(PM2.5), NOx,Na+(PM2.5), Ni(PM10),<br>Ni(cdepoz), O3,OC(PM2.5), PM10, PM2.5, Pb(PM10), SO2, SO42_(PM2.5), acetylen, cis2buten, etan, etylen, etylobenzen, formaldehyd, ibutan, iheksan, ioktan, ipentan, izopren, ksylen, mpksylen, nbutan, nheksan, nheptan, noktan, npentan, oksylen, propan, propen, toluen, trans2buten |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ArchivalDataDto`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/archivalData/getDataForAllStations`



Usługa sieciowa udostępniająca archiwalne wyniki pomiarów automatycznych i manualnych ze wszystkich stacji w kraju dla dowolnego wybranego okresu czasu (max. 31 dni). Należy wybrać zakres czasu: Data od i Data do lub Liczba dni wstecz od 

https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStations.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStations?dayNumber=2

operationId: `getArchivalDataForAllStations`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się rosnąco po atrybutach Kod stanowiska oraz Data. <br /> Dostępne atrybuty:    <br /> Data - parametr dla daty, <br />Kod - parametr dla kodu stanowiska  |
| dateFrom | query | False | string | {} | Data od:<br>należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-23 15:00 |
| dateTo | query | False | string | {} | Data do:<br>należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-25 11:00 |
| dayNumber | query | False | string | {} | Liczba dni wstecz od dnia dzisiejszego np. 5 (dzień rozumiany jako 24 godziny wstecz od wywołania usługi) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ArchivalDataDto`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/archivalData/getDataForAllStations`



Usługa sieciowa udostępniająca archiwalne wyniki pomiarów automatycznych i manualnych ze wszystkich stacji w kraju dla dowolnego wybranego okresu czasu (max. 31 dni). Należy wybrać zakres czasu: Data od i Data do lub Liczba dni wstecz od 

https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStations.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataForAllStations?dayNumber=2

operationId: `getArchivalDataForAllStations_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się rosnąco po atrybutach Kod stanowiska oraz Data. <br /> Dostępne atrybuty:    <br /> Data - parametr dla daty, <br />Kod - parametr dla kodu stanowiska  |
| dateFrom | query | False | string | {} | Data od:<br>należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-23 15:00 |
| dateTo | query | False | string | {} | Data do:<br>należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-25 11:00 |
| dayNumber | query | False | string | {} | Liczba dni wstecz od dnia dzisiejszego np. 5 (dzień rozumiany jako 24 godziny wstecz od wywołania usługi) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ArchivalDataDto`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/rest/archivalData/getDataBySensor/{idSensor}`



Usługa sieciowa udostępniająca archiwalne wyniki pomiarów automatycznych i manualnych na podstawie podanego identyfikatora stanowiska pomiarowego dla dowolnego wybranego okresu czasu (max. 366 dni). Należy podać identyfikator stanowiska oraz wybrać zakres czasu: Data od i Data do lub Liczba dni wstecz od 

https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataBySensor/{idSensor}.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https:///api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataBySensor/52?dayNumber=3

operationId: `getArchivalDataBySensor`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się malejąco po atrybucie Data. <br /> Dostępne atrybuty:    <br /> Data - parametr dla daty <br />  |
| idSensor | path | True | integer / int64 | {} | Identyfikator stanowiska np. 52                <br/> Lista stacji i stanowisk pomiarowych wraz z ich id udostępniana jest poprzez usługi API "Stacje pomiarowe i stanowiska pomiarowe”  |
| dateFrom | query | False | string | {} | Data od:                                             <br />- dla stanowisk automatycznych (wyniki jednogodzinne ) należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-23 15:00  <br /> - dla stanowisk manualnych (wyniki średniodobowe) należy określić datę uwzględniając dni zgodnie z przykładem: 2022-02-23 00:00  |
| dateTo | query | False | string | {} | Data do:                                                                   <br />- dla stanowisk automatycznych (wyniki jednogodzinne ) należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-25 11:00  <br />- dla stanowisk manualnych (wyniki średniodobowe) należy określić datę uwzględniając dni zgodnie z przykładem: 2022-02-25 00:00 |
| dayNumber | query | False | string | {} | Liczba dni wstecz od dnia dzisiejszego np. 5 (dzień rozumiany jako 24 godziny wstecz od wywołania usługi) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ArchivalDataDto`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/archivalData/getDataBySensor/{idSensor}`



Usługa sieciowa udostępniająca archiwalne wyniki pomiarów automatycznych i manualnych na podstawie podanego identyfikatora stanowiska pomiarowego dla dowolnego wybranego okresu czasu (max. 366 dni). Należy podać identyfikator stanowiska oraz wybrać zakres czasu: Data od i Data do lub Liczba dni wstecz od 

https://api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataBySensor/{idSensor}.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https:///api.gios.gov.pl/pjp-api/v1/rest/archivalData/getDataBySensor/52?dayNumber=3

operationId: `getArchivalDataBySensor_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się malejąco po atrybucie Data. <br /> Dostępne atrybuty:    <br /> Data - parametr dla daty <br />  |
| idSensor | path | True | integer / int64 | {} | Identyfikator stanowiska np. 52                <br/> Lista stacji i stanowisk pomiarowych wraz z ich id udostępniana jest poprzez usługi API "Stacje pomiarowe i stanowiska pomiarowe”  |
| dateFrom | query | False | string | {} | Data od:                                             <br />- dla stanowisk automatycznych (wyniki jednogodzinne ) należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-23 15:00  <br /> - dla stanowisk manualnych (wyniki średniodobowe) należy określić datę uwzględniając dni zgodnie z przykładem: 2022-02-23 00:00  |
| dateTo | query | False | string | {} | Data do:                                                                   <br />- dla stanowisk automatycznych (wyniki jednogodzinne ) należy określić datę uwzględniając dni i godziny zgodnie z przykładem: 2022-02-25 11:00  <br />- dla stanowisk manualnych (wyniki średniodobowe) należy określić datę uwzględniając dni zgodnie z przykładem: 2022-02-25 00:00 |
| dayNumber | query | False | string | {} | Liczba dni wstecz od dnia dzisiejszego np. 5 (dzień rozumiany jako 24 godziny wstecz od wywołania usługi) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `ArchivalDataDto`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/aqindex/getIndex/{stationId}`



Usługa sieciowa udostępniająca indeks jakości powietrza na podstawie podanego identyfikatora stacji pomiarowej.
https://api.gios.gov.pl/pjp-api/v1/rest/aqindex/getIndex/{stationId}

Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/aqindex/getIndex/52

operationId: `getIndex`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu. Aby posortować w odwrotnej kolejności należy poprzedzić nazwę parametru znakiem minus. Parametr jest opcjonalny. |
| stationId | path | True | integer / int32 | {} | Identyfikator stacji pomiarowej np. 52 <br/> Lista stacji i stanowisk pomiarowych wraz z ich id udostępniana jest poprzez usługi API "Stacje pomiarowe i stanowiska pomiarowe” |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/ld+json → `DataException`

- HTTP 404: Nie znaleziono; application/ld+json → `DataException`

- HTTP 200: OK; application/ld+json → `AqIndexMetaDTO`

- HTTP 503: Usługa czasowo niedostępna.; application/ld+json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/ld+json → `DataException`

- HTTP 204: Brak zawartości; application/ld+json → `DataException`

- HTTP 401: Brak autoryzacji; application/ld+json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/ld+json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/ld+json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/ld+json → `DataException`

- HTTP 400: Błędne żądanie; application/ld+json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/ld+json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/ld+json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/ld+json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/ld+json → `DataException`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/ld+json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/ld+json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/ld+json → `DataException`

- HTTP 403: Dostęp zabroniony; application/ld+json → `DataException`

- HTTP 409: Konflikt; application/ld+json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/ld+json → `DataException`

### GET `/v1/rest/aggregate/getAggregatePm10Data`



Usługa sieciowa udostępniająca agregaty ze stanowisk automatycznych za 3 ostatnie doby w podziale na województwa i powiaty:
1. Agregat Maksimum ze średnich 8-godzinnych z 1-godzinnych wyników pomiarów pyłu zawieszonego PM10;
2. Agregat Średnia 24-godzinna z 1-godzinnych wyników pomiarów pyłu zawieszonego PM10

https://api.gios.gov.pl/pjp-api/v1/rest/aggregate/getAggregatePm10Data.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/aggregate/getAggregatePm10Data

operationId: `getAggregatePm10Data`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się rosnąco po atrybutach Kod stanowiska oraz Data. <br /> Dostępne atrybuty:    <br /> Województwo - parametr dla nazwy województwa, <br /> Powiat - parametr dla nazwy powiatu  |
| filter[powiat] | query | False | string | {} | Powiat np. Katowice, Zabrze, Bielsko-Biała,  Warszawa, limanowski, ostrołęcki, olkuski. W przypadku wyboru kilku powiatów należy oddzielić je znakiem przecinka (,) |
| filter[wojewodztwo] | query | False | string | {} | Województwo np. ŚLĄSKIE, WARMIŃSKO-MAZURSKIE, KUJAWSKO-POMORSKIE, MAŁOPOLSKIE. W przypadku wyboru kilku województw należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/json → `DataException`

- HTTP 404: Nie znaleziono; application/json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/json → `DataException`

- HTTP 200: OK; application/ld+json → `AggregatePM10DataDTO`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/json → `DataException`

- HTTP 403: Dostęp zabroniony; application/json → `DataException`

- HTTP 409: Konflikt; application/json → `DataException`

- HTTP 400: Błędne żądanie; application/json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/json → `DataException`

- HTTP 204: Brak zawartości; application/json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/json → `DataException`

- HTTP 401: Brak autoryzacji; application/json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/json → `DataException`

### GET `/rest/aggregate/getAggregatePm10Data`



Usługa sieciowa udostępniająca agregaty ze stanowisk automatycznych za 3 ostatnie doby w podziale na województwa i powiaty:
1. Agregat Maksimum ze średnich 8-godzinnych z 1-godzinnych wyników pomiarów pyłu zawieszonego PM10;
2. Agregat Średnia 24-godzinna z 1-godzinnych wyników pomiarów pyłu zawieszonego PM10

https://api.gios.gov.pl/pjp-api/v1/rest/aggregate/getAggregatePm10Data.
Usługa sieciowa typu REST wykorzystująca zapytanie HTTP GET. Udostępniająca dane w formacie JSON-LD.

Przykład zapytania: https://api.gios.gov.pl/pjp-api/v1/rest/aggregate/getAggregatePm10Data

operationId: `getAggregatePm10Data_1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| page | query | False | integer / int32 | {"minimum":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0. |
| size | query | False | integer / int32 | {"minimum":1} | Parametr mechanizmu stronicowania określający ilość wyników na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 20, Maksymalna wartość → 500. |
| sort | query | False | string | {} | Parametr mechanizmu sortowania. Jako wartość przyjmuje nazwę atrybutu.                  Aby posortować w odwrotnej kolejności należy poprzedzić nazwę atrybutu znakiem minus. Parametr jest opcjonalny. <br />Domyślne sortowanie odbywa się rosnąco po atrybutach Kod stanowiska oraz Data. <br /> Dostępne atrybuty:    <br /> Województwo - parametr dla nazwy województwa, <br /> Powiat - parametr dla nazwy powiatu  |
| filter[powiat] | query | False | string | {} | Powiat np. Katowice, Zabrze, Bielsko-Biała,  Warszawa, limanowski, ostrołęcki, olkuski. W przypadku wyboru kilku powiatów należy oddzielić je znakiem przecinka (,) |
| filter[wojewodztwo] | query | False | string | {} | Województwo np. ŚLĄSKIE, WARMIŃSKO-MAZURSKIE, KUJAWSKO-POMORSKIE, MAŁOPOLSKIE. W przypadku wyboru kilku województw należy oddzielić je znakiem przecinka (,) |

Odpowiedzi:

- HTTP 429: Zbyt wiele zapytań w jednostce czasu; application/json → `DataException`

- HTTP 404: Nie znaleziono; application/json → `DataException`

- HTTP 202: Zaakceptowano zapytanie, odpowiedź jeszcze nie jest gotowa; application/json → `DataException`

- HTTP 200: OK; application/ld+json → `AggregatePM10DataDTO`

- HTTP 502: Błąd bramki – serwer otrzymał niepoprawną odpowiedź od serwera nadrzędnego.; application/json → `DataException`

- HTTP 406: Nieakceptowalne – treść nie może zostać przygotowana w sposób zasygnalizowany nagłówkami; application/json → `DataException`

- HTTP 303: Zobacz inne: odpowiedź na zapytanie dostępna pod innym adresem; application/json → `DataException`

- HTTP 405: Nieodpowiednia metoda; application/json → `DataException`

- HTTP 410: Zasób usunięty i już nigdy nie będzie dostępny pod tym adresem; application/json → `DataException`

- HTTP 422: Zapytanie niepoprawne semantycznie; application/json → `DataException`

- HTTP 500: Wewnętrzny błąd serwera; application/json → `DataException`

- HTTP 503: Usługa czasowo niedostępna.; application/json → `DataException`

- HTTP 201: Utworzono nowy zasób; application/json → `DataException`

- HTTP 403: Dostęp zabroniony; application/json → `DataException`

- HTTP 409: Konflikt; application/json → `DataException`

- HTTP 400: Błędne żądanie; application/json → `DataException`

- HTTP 304: Nie modyfikowano od czasu wskazanego w zapytaniu; application/json → `DataException`

- HTTP 204: Brak zawartości; application/json → `DataException`

- HTTP 504: Przekroczony czas oczekiwania na odpowiedź serwera wewnętrznego.; application/json → `DataException`

- HTTP 401: Brak autoryzacji; application/json → `DataException`

- HTTP 301: Przeniesiono na stałe; application/json → `DataException`

### GET `/rest/portal/threshold`





operationId: `getThresholdValues`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of ThresholdValueDTO`

### GET `/rest/portal/news`





operationId: `getArticles`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of BaseArticleDTO`

### GET `/rest/portal/news/{id}`





operationId: `getArticle`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| id | path | True | integer / int64 | {} |  |

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `ArticleDTO`

### GET `/rest/portal/legend`





operationId: `getLegend`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `array of ParamThresholdDTO`

### GET `/rest/date`





operationId: `getDateTime`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|

Odpowiedzi:

- HTTP 429: Too Many Requests; */* → `object`

- HTTP 404: Not Found; */* → `object`

- HTTP 200: OK; */* → `ServerDateTimeDTO`

## Pełny słownik schematów

### `VersionDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| major | string | False | {} |  |
| minor | string | False | {} |  |
| patch | string | False | {} |  |
| dateMod | string / date | False | {} |  |

### `StatisticsLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista statystyk | object | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `DataException`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| error_result | string | False | {} |  |
| error_reason | string | False | {} |  |
| error_solution | string | False | {} |  |
| error_help | string | False | {} |  |
| error_code | string | False | {} |  |

### `SensorLd`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista stanowisk pomiarowych dla podanej stacji | array of SensorLdDTO | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `SensorLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Identyfikator stanowiska | integer / int64 | False | {} |  |
| Identyfikator stacji | integer / int64 | False | {} |  |
| Wskaźnik | string | False | {} |  |
| Wskaźnik - wzór | string | False | {} |  |
| Wskaźnik - kod | string | False | {} |  |
| Id wskaźnika | integer / int64 | False | {} |  |

### `StationLd`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista stacji pomiarowych | array of StationLdDTO | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `StationLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Identyfikator stacji | integer / int64 | False | {} |  |
| Kod stacji | string | False | {} |  |
| Nazwa stacji | string | False | {} |  |
| WGS84 φ N | string | False | {} |  |
| WGS84 λ E | string | False | {} |  |
| Identyfikator miasta | integer / int64 | False | {} |  |
| Nazwa miasta | string | False | {} |  |
| Gmina | string | False | {} |  |
| Powiat | string | False | {} |  |
| Województwo | string | False | {} |  |
| Ulica | string | False | {} |  |

### `StationMetaDataLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista metadanych stacji pomiarowych | array of StationMetadata | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `StationMetadata`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Nr | integer / int64 | False | {} |  |
| Kod stacji | string | False | {} |  |
| Kod międzynarodowy | string | False | {} |  |
| Nazwa stacji | string | False | {} |  |
| Stary Kod stacji | string | False | {} |  |
| Data uruchomienia | string | False | {} |  |
| Data zamknięcia | string | False | {} |  |
| Typ stacji | string | False | {} |  |
| Typ obszaru | string | False | {} |  |
| Rodzaj stacji | string | False | {} |  |
| Województwo | string | False | {} |  |
| Miejscowość | string | False | {} |  |
| Adres | string | False | {} |  |
| WGS84 φ N | string | False | {} |  |
| WGS84 λ E | string | False | {} |  |

### `SensorMetaDataLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista metadanych stanowisk pomiarowych | array of SensorMetadata | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `SensorMetadata`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Nr | integer / int64 | False | {} |  |
| Kod stanowiska | string | False | {} |  |
| Kod stacji | string | False | {} |  |
| Nazwa stacji | string | False | {} |  |
| Stary Kod stacji | string | False | {} |  |
| Wskaźnik - kod | string | False | {} |  |
| Wskaźnik | string | False | {} |  |
| Czas uśredniania | string | False | {} |  |
| Typ pomiaru | string | False | {} |  |
| Data uruchomienia | string | False | {} |  |
| Data zamknięcia | string | False | {} |  |
| Województwo | string | False | {} |  |
| Nazwa strefy | string | False | {} |  |

### `AlExcReasonTypeDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| alarmExcReasonTypeCode | string | False | {} |  |
| alarmExcReasonType | string | False | {} |  |
| alarmExcReasonTypeEng | string | False | {} |  |

### `AlarmExcTypeDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| sdValue | string | False | {} |  |
| sdValueCode | string | False | {} |  |
| sdValueEng | string | False | {} |  |
| sdValueCodeEng | string | False | {} |  |

### `AlarmLevelDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| param | ParamDTO | False | {} |  |
| alarmExcType | AlarmExcTypeDTO | False | {} |  |
| standard | StandardDTO | False | {} |  |
| sensor | SensorDTO | False | {} |  |
| zone | ZoneDTO | False | {} |  |
| areaInfo | string | False | {} |  |
| timestampValue | integer / int64 | False | {} |  |
| duration | integer / int64 | False | {} |  |
| maxConcentration | number / double | False | {} |  |
| no2Concentration | number / double | False | {} |  |
| maxConcentrationS8 | number / double | False | {} |  |
| population | integer / int64 | False | {} |  |
| restrictionsInfo | string | False | {} |  |
| additionalInfo | string | False | {} |  |
| websiteInfo | string | False | {} |  |
| websitePlan | string | False | {} |  |
| expectedArea | string | False | {} |  |
| expectedChanges | string | False | {} |  |
| populationGroups | string | False | {} |  |
| symptoms | string | False | {} |  |
| recommendedPrecaution | string | False | {} |  |
| infoSource | string | False | {} |  |
| timestampCreated | integer / int64 | False | {} |  |
| active | boolean | False | {} |  |
| reasons | array of AlExcReasonTypeDTO | False | {} |  |

### `ParamDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| paramName | string | False | {} |  |
| paramFormula | string | False | {} |  |
| paramCode | string | False | {} |  |
| idParam | integer / int64 | False | {} |  |

### `ProtectionTargetDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| sdValue | string | False | {} |  |
| sdValueCode | string | False | {} |  |
| sdValueEng | string | False | {} |  |
| sdValueCodeEng | string | False | {} |  |

### `SensorDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| stationId | integer / int64 | False | {} |  |
| param | ParamDTO | False | {} |  |

### `StandardDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| param | ParamDTO | False | {} |  |
| protectionTarget | ProtectionTargetDTO | False | {} |  |
| standardValue | number / float | False | {} |  |
| acceptNumber | number / float | False | {} |  |
| comments | string | False | {} |  |
| standardTypeCode | string | False | {} |  |
| standardType | string | False | {} |  |

### `ZoneDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| zoneName | string | False | {} |  |
| zoneCode | string | False | {} |  |
| zoneHeader | string | False | {} |  |
| zoneHeaderDec | string | False | {} |  |

### `ExceedingDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Typ normy | string | False | {} |  |
| Strefa | string | False | {} |  |
| Informacje dotyczące obszaru przekroczenia | string | False | {} |  |
| Przyczyny przekroczenia | string | False | {} |  |
| Stanowisko pomiarowe | string | False | {} |  |
| Data i godzina | string | False | {} |  |
| Czas trwania | string | False | {} |  |
| Liczba mieszkańców | integer / int64 | False | {} |  |
| Wartość maksymalnego stężenia (µg/m3) | number / double | False | {} |  |
| Informacje o podjętych ograniczeniach | string | False | {} |  |
| Dodatkowe informacje | string | False | {} |  |
| Odnośnik do strony internetowej z informacjami | string | False | {} |  |
| Odnośnik do strony internetowej z planem działań | string | False | {} |  |
| Prognoza zmian stężeń | string | False | {} |  |
| Obszar geograficzny, na którym spodziewane są przekroczenia | string | False | {} |  |
| Informacje w sprawie grup ludności objętych ryzykiem | string | False | {} |  |
| Opis prawdopodobnych symptomów | string | False | {} |  |
| Zalecane środki ostrożności | string | False | {} |  |
| Wskazanie, gdzie można uzyskać dalsze informacje | string | False | {} |  |

### `ExceedingLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Przekroczenia | array of ExceedingDTO | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `CurrentDataDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista danych pomiarowych | array of DataDTOLd | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `DataDTOLd`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Kod stanowiska | string | False | {} |  |
| Data | string | False | {} |  |
| Wartość | number / double | False | {} |  |

### `ConcentrationDistributionsDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |
| features | array of Feature | False | {} |  |

### `Feature`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| type | string | False | {} |  |
| geometry | Geometry | False | {} |  |
| properties | Properties | False | {} |  |

### `Geometry`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| type | string | False | {} |  |
| coordinates | array of array of array of object | False | {} |  |

### `Properties`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| nazwa_wska | string | False | {} |  |
| typ_wskaz | string | False | {} |  |
| rok | integer / int32 | False | {} |  |
| wartosc | number / double | False | {} |  |

### `ArchivalDataDto`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| Lista archiwalnych wyników pomiarów | array of StationDataDTO | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `StationDataDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Nazwa stacji | string | False | {} |  |
| Kod stanowiska | string | False | {} |  |
| Data | string | False | {} |  |
| Wartość | number / double | False | {} |  |

### `AqIndexMetaDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| @context | object | False | {} |  |
| AqIndex | StationAqIndexLdDTO | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |

### `StationAqIndexLdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Identyfikator stacji pomiarowej | integer / int64 | False | {} |  |
| Data wykonania obliczeń indeksu | string | False | {} |  |
| Wartość indeksu | integer / int64 | False | {} |  |
| Nazwa kategorii indeksu | string | False | {} |  |
| Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika st | string | False | {} |  |
| Data wykonania obliczeń indeksu dla wskaźnika SO2 | string | False | {} |  |
| Wartość indeksu dla wskaźnika SO2 | integer / int64 | False | {} |  |
| Nazwa kategorii indeksu dla wskażnika SO2 | string | False | {} |  |
| Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika SO2 | string | False | {} |  |
| Data wykonania obliczeń indeksu dla wskaźnika NO2 | string | False | {} |  |
| Wartość indeksu dla wskaźnika NO2 | integer / int64 | False | {} |  |
| Nazwa kategorii indeksu dla wskażnika NO2 | string | False | {} |  |
| Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika NO2 | string | False | {} |  |
| Data wykonania obliczeń indeksu dla wskaźnika PM10 | string | False | {} |  |
| Wartość indeksu dla wskaźnika PM10 | integer / int64 | False | {} |  |
| Nazwa kategorii indeksu dla wskażnika PM10 | string | False | {} |  |
| Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika PM10 | string | False | {} |  |
| Data wykonania obliczeń indeksu dla wskaźnika PM2.5 | string | False | {} |  |
| Wartość indeksu dla wskaźnika PM2.5 | integer / int64 | False | {} |  |
| Nazwa kategorii indeksu dla wskażnika PM2.5 | string | False | {} |  |
| Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika PM2.5 | string | False | {} |  |
| Data wykonania obliczeń indeksu dla wskaźnika O3 | string | False | {} |  |
| Wartość indeksu dla wskaźnika O3 | integer / int64 | False | {} |  |
| Nazwa kategorii indeksu dla wskażnika O3 | string | False | {} |  |
| Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika O3 | string | False | {} |  |
| Status indeksu ogólnego dla stacji pomiarowej | boolean | False | {} |  |
| Kod zanieczyszczenia krytycznego | string | False | {"enum":["PYL","OZON"]} |  |

### `AggregateDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Województwo | string | False | {} |  |
| Kod stanowiska | string | False | {} |  |
| Powiat | string | False | {} |  |
| Data | string | False | {} |  |
| Maksimum ze średnich 8-godzinnych | number / double | False | {} |  |
| Średnia 24-godzinna z wyników 1-godzinnych | number / double | False | {} |  |

### `AggregatePM10DataDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| Lista danych zagregowanych | array of AggregateDTO | False | {} |  |
| meta | object | False | {} |  |
| links | object | False | {} |  |
| totalPages | integer / int32 | False | {} |  |
| @context | object | False | {} |  |

### `MainParamDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| paramCode | string | False | {} |  |
| paramUnit | string | False | {} |  |
| paramCodeHtml | string | False | {} |  |
| paramNameEng | string | False | {} |  |

### `ThresholdValueDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| param | MainParamDTO | False | {} |  |
| min | number / float | False | {} |  |
| max | number / float | False | {} |  |
| thresholdId | integer / int64 | False | {} |  |

### `BaseArticleDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| contentId | integer / int64 | False | {} |  |
| header | string | False | {} |  |
| createDate | integer / int64 | False | {} |  |

### `ArticleDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| contentId | integer / int64 | False | {} |  |
| header | string | False | {} |  |
| createDate | integer / int64 | False | {} |  |
| content | string | False | {} |  |
| link | string | False | {} |  |

### `ParamThresholdDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer / int64 | False | {} |  |
| name | string | False | {} |  |
| backgroundColor | string | False | {} |  |
| textColor | string | False | {} |  |
| nameEng | string | False | {} |  |
| available | boolean | False | {} |  |

### `ServerDateTimeDTO`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dateTime | integer / int64 | False | {} |  |
