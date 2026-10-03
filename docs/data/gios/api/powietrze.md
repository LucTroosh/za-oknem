# POWIETRZE API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-powietrze.yaml. Pobrano 2026-10-03. SHA-256: `2097547a7cb7da32a8fa0fdb4a29d905758df5d9982b9ee3ec811a990961c896`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/powietrze

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/wyniki-ocen-rocznych`

Wyniki ocen jakości powietrza - wyniki ocen wraz z parametrami i metadanymi

Usługa sieciowa udostępniająca dane dotyczące wyników rocznych ocen jakości powietrza zgromadzone w Ekoinfonet - JPOAT 3.0, w zakresie wyników ocen wraz z parametrami i metadanymi, w tym. m.in. informacje o metodach oceny, stanowiskach pomiarowych, informacje o przekroczeniu

operationId: `getWynikiOcenRocznychV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| ocenianyRok | query | True | integer | {"minimum":2004,"maximum":9999} | Oceniany rok (rok, dla którego wykonywana jest ocena) np. 2022. – dostępne są dane od 2004 roku |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |
| powiat | query | False | string | {"maxLength":50} | Powiat, np. 'Warszawa', 'wałbrzyski' |
| gmina | query | False | string | {"maxLength":50} | Gmina, np. 'Warszawa', 'Wrocław', 'Gryfino' |
| strefa | query | False | string | {"maxLength":50} | Strefa, np. 'aglomeracja rybnicko-jastrzębska', 'miasto Gorzów Wielkopolski', 'strefa warmińsko-mazurska' |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. 'arsen w PM10', 'benzen', 'benzo(a)piren w PM10', 'dwutlenek azotu', 'dwutlenek siarki', 'kadm w PM10', 'nikiel w PM10', 'ołów w PM10', 'ozon', 'pył zawieszony PM10', 'pył zawieszony PM2.5', 'tlenek węgla', 'tlenki azotu' |
| typNormy | query | False | string | {"maxLength":100} | Typ normy, np. 'Poziom alarmowy', 'Poziom celu dlugoterminowego', 'Poziom docelowy', 'Poziom dopuszczalny', 'Poziom dopuszczalny (II faza)', 'Poziom dopuszczalny (ochr. rośl.)', 'Poziom informowania' |
| celOchrony | query | False | PowietrzeCelOchronyEnum | {"enum":["OZ","OR"]} | Cel ochrony (OZ oznacza kryterium pod kątem ochrony zdrowia ludzi, OR oznacza kryterium pod kątem ochrony roślin) |
| wynikOceny | query | False | string | {"maxLength":10} | Wynik oceny rocznej, np. 'A', 'A1', 'B', 'C', 'C1', 'D1', 'D2'.<br>Ocena: A, A1, D1 oznacza brak przekroczeń; ocena C, C1, D2 oznacza przekroczenie |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzewynikiOcenRocznychOdpowiedz`

### GET `/v1/wyniki-ocen-stezenia`

Wyniki ocen jakości powietrza - stężenia zanieczyszczeń uwzględnionych w ocenie jakości powietrza i danych uzupełniających

Usługa sieciowa udostępniająca dane dotyczące wyników rocznych ocen jakości powietrza zgromadzone w Ekoinfonet - JPOAT 3.0, w zakresie dot. stężeń zanieczyszczeń uwzględnionych w ocenie i danych uzupełniających

operationId: `getWynikiOcenStezeniaV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rok | query | True | integer | {"minimum":0,"maximum":9999} | Rok statystyk, np. 2022 |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego, np. 52 . Lista identyfikatorów stanowisk znajduje się w usłudze [Lista stanowisk monitoringu jakości powietrza](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id) |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeWynikiOcenStezeniaOdpowiedz`

### GET `/v1/wyniki-ocen-wieloletnich`

Wyniki ocen na potrzeby ustalenia metod wykonywania rocznych ocen jakości powietrza

Usługa sieciowa udostępniająca wyniki ocen na potrzeby ustalenia metod wykonywania rocznych ocen jakości powietrza (tzw. ocen wieloletnich)

operationId: `getWynikOcenWieloletnichV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| zakresLat | query | True | string | {"maxLength":11} | Zakres lat objętych oceną, np. '2019 - 2023'. Dane udostępniane w zakresach od 2009 roku (zakres lat '2009 - 2013') |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |
| strefa | query | False | string | {"maxLength":50} | Strefa, np. 'aglomeracja rybnicko-jastrzębska', 'miasto Gorzów Wielkopolski', 'strefa warmińsko-mazurska' |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. arsen w 'PM10', 'benzen', 'benzo(a)piren w PM10', 'dwutlenek azotu', 'dwutlenek siarki', 'kadm w PM10', 'nikiel w PM10', 'ołów w PM10', 'ozon', 'pył zawieszony PM10', 'pył zawieszony PM2.5', 'tlenek węgla', 'tlenki azotu' |
| celOchrony | query | False | PowietrzeCelOchronyEnum | {"enum":["OZ","OR"]} | Cel ochrony (OZ oznacza kryterium pod kątem ochrony zdrowia ludzi, OR oznacza kryterium pod kątem ochrony roślin) |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeWynikiOcenWieloletnichOdpowiedz`

### GET `/v1/pm25-metadane-metody`

Monitoring składu chemicznego pyłu zawieszonego PM2,5 - metadane stanowisk, metody pomiaru

Usługa sieciowa udostępniająca informacje na temat monitoringu składu chemicznego pyłu zawieszonego PM2,5, w zakresie  metadanych stanowisk, metod pomiaru

operationId: `getPm25MetadaneStanowiskV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego, np. 52 . Lista identyfikatorów stanowisk znajduje się w usłudze [Lista stanowisk monitoringu jakości powietrza](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id) |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. 'amony w PM2.5', 'azotany w PM2.5', 'chlorki w PM2.5', 'magnez w PM2.5', 'potas w PM2.5', 'siarczany w PM2.5', 'sód w PM2.5', 'wapń w PM2.5', 'węgiel organiczny (OC) w PM2.5', 'wolny węgiel (EC) w PM2.5' |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzePm25MetadaneStanowiskOdpowiedz`

### GET `/v1/pm25-wyniki-pomiarow`

Monitoring składu chemicznego pyłu zawieszonego PM2,5 - wyniki pomiarów stężeń

Usługa sieciowa udostępniająca informacje na temat monitoringu składu chemicznego pyłu zawieszonego PM2,5, w zakresie wyników pomiarów stężeń

operationId: `getPm25WynikiPomiarowV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego, np. 52 . Lista identyfikatorów stanowisk znajduje się w usłudze [Lista stanowisk monitoringu jakości powietrza](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id) |
| dataDo | query | False | string / date | {} | Data końcowa wyszukiwanych pomiarów w formacie RRRR-MM-DD |
| rok | query | False | integer | {"minimum":0,"maximum":9999} | Rok wyszukiwanych danych, np. 2022 |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzePm25WynikiPomiarowOdpowiedz`

### GET `/v1/pm25-statystyki`

Monitoring składu chemicznego pyłu zawieszonego PM2,5 - statystyki

Usługa sieciowa udostępniająca informacje na temat monitoringu składu chemicznego pyłu zawieszonego PM2,5, w zakresie wartości stężeń średnich rocznych

operationId: `getPm25StatystykiV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego, np. 52 . Lista identyfikatorów stanowisk znajduje się w usłudze [Lista stanowisk monitoringu jakości powietrza](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id) |
| rok | query | False | integer | {"minimum":0,"maximum":9999} | Rok wyszukiwanych danych, np. 2022 |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzePm25StatystykiOdpowiedz`

### GET `/v1/metody-pomiarowe`

Metody pomiarowe

Usługa sieciowa udostępniająca informacje o stosowaniu referencyjnych metod pomiarowych

operationId: `getMetodyPomiaroweV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego, np. 52 . Lista identyfikatorów stanowisk znajduje się w usłudze [Lista stanowisk monitoringu jakości powietrza](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id) |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. 'dwutlenek azotu' |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeMetodyPomiaroweOdpowiedz`

### GET `/v1/chemizm-opadow`

Monitoring chemizmu opadów atmosferycznych (depozycji) - metadane, metody pomiaru

Usługa sieciowa udostępniająca informacje z zakresu monitoringu chemizmu opadów atmosferycznych (depozycji) w zakresie  metadanych, metod pomiaru

operationId: `getChemizmOpadowV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. 'arsen (całk. depozycja)', 'benzo(a)antracen (całk. depozycja)', 'benzo(a)piren (całk. depozycja)', 'benzo(b)fluoranten (całk. depozycja)', 'benzo(j)fluoranten (całk. depozycja)', 'benzo(k)fluoranten (całk. depozycja)', 'dibenzo(a,h)antracen (całk. depozycja)', 'indeno(1,2,3-cd)piren (całk. depozycja)', 'kadm (całk. depozycja)', 'nikiel (całk. depozycja)', 'rtęć (całk. depozycja)'' |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego monitoringu chemizmu opadów atmosferycznych (depozycji),  np. 417. Lista identyfikatorów stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji) znajduje się w usłudze [Lista stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji)](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id-dep) |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeChemizmOpadowOdpowiedz`

### GET `/v1/chemizm-opadow-wyniki-pomiarow`

Monitoring chemizmu opadów atmosferycznych (depozycji) - wyniki pomiarów

Usługa sieciowa udostępniająca informacje z zakresu monitoringu chemizmu opadów atmosferycznych (depozycji) w zakresie wyników pomiarów

operationId: `getChemizmOpadowWynikiPomiarowV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| dataOd | query | False | string / date | {} | Data początkowa wyszukiwanych pomiarów w formacie RRRR-MM-DD |
| dataDo | query | False | string / date | {} | Data końcowa wyszukiwanych pomiarów w formacie RRRR-MM-DD |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego monitoringu chemizmu opadów atmosferycznych (depozycji),  np. 417. Lista identyfikatorów stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji) znajduje się w usłudze [Lista stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji)](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id-dep) |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. 'arsen (całk. depozycja)', 'benzo(a)antracen (całk. depozycja)', 'benzo(a)piren (całk. depozycja)', 'benzo(b)fluoranten (całk. depozycja)', 'benzo(j)fluoranten (całk. depozycja)', 'benzo(k)fluoranten (całk. depozycja)', 'dibenzo(a,h)antracen (całk. depozycja)', 'indeno(1,2,3-cd)piren (całk. depozycja)', 'kadm (całk. depozycja)', 'nikiel (całk. depozycja)', 'rtęć (całk. depozycja)' |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeChemizmOpadowWynikiPomiarowOdpowiedz`

### GET `/v1/chemizm-opadow-agregaty`

Monitoring chemizmu opadów atmosferycznych (depozycji) - wartości agregatów

Usługa sieciowa udostępniająca agregaty ze stanowisk zawierające informacje z zakresu monitoringu chemizmu opadów atmosferycznych

operationId: `getChemizmOpadowAgregatyV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| dataOd | query | False | string / date | {} | Data początkowa wyszukiwanych pomiarów w formacie RRRR-MM-DD |
| dataDo | query | False | string / date | {} | Data końcowa wyszukiwanych pomiarów w formacie RRRR-MM-DD |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego monitoringu chemizmu opadów atmosferycznych (depozycji),  np. 417. Lista identyfikatorów stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji) znajduje się w usłudze [Lista stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji)](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id-dep) |
| wskaznik | query | False | string | {"maxLength":100} | Wskaźnik, np. 'arsen (całk. depozycja)', 'benzo(a)antracen (całk. depozycja)', 'benzo(a)piren (całk. depozycja)', 'benzo(b)fluoranten (całk. depozycja)', 'benzo(j)fluoranten (całk. depozycja)', 'benzo(k)fluoranten (całk. depozycja)', 'dibenzo(a,h)antracen (całk. depozycja)', 'indeno(1,2,3-cd)piren (całk. depozycja)', 'kadm (całk. depozycja)', 'nikiel (całk. depozycja)', 'rtęć (całk. depozycja)' |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Succes; application/json → `PowietrzeChemizmOpadowAgregatyOdpowiedz`

### GET `/v1/chemizm-opadow-srednie-roczne`

Monitoring chemizmu opadów atmosferycznych (depozycji) - średnie stężenia roczne

Usługa sieciowa udostępniająca informacje z zakresu monitoringu chemizmu opadów atmosferycznych (depozycji) w zakresie średnich stężeń rocznych

operationId: `getChemizmOpadowSrednieRoczneV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rok | query | False | integer | {"minimum":0,"maximum":9999} | Rok np. 2022 |
| stanowiskoId | query | False | array of integer | {} | Identyfikator stanowiska pomiarowego monitoringu chemizmu opadów atmosferycznych (depozycji),  np. 417. Lista identyfikatorów stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji) znajduje się w usłudze [Lista stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji)](https://dane.gios.gov.pl/api/powietrze/v1/stanowisko-id-dep) |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeChemizmOpadowSrednieRoczneOdpowiedz`

### GET `/v1/stanowisko-id`

Lista stanowisk monitoringu jakości powietrza (stanowiskoId)

Lista stanowisk pomiarowych monitoringu jakości powietrza udostępniająca numer id stanowiska  (stanowiskoId) na potrzeby innych usług, np. pobierania po id stanowiska

operationId: `getStanowiskoIdV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| stanowiskoId | query | False | integer | {"minimum":0,"maximum":99999999} | Identyfikator stanowiska |
| idStacja | query | False | integer | {"minimum":0,"maximum":99999999} | Identyfikator stacji |
| idWskaznik | query | False | integer | {"minimum":0,"maximum":99999999} | Identyfikator wskaźnika - liczba. Przykład: 1 (id dla dwutlenek siarki), 3 (id dla  pyłu zawieszonego PM10), 5 (id dla ozonu), 6 (id dla dwutlenku azotu), 8 (id dla  tlenku węgla), 10 (id dla benzenu) |
| statusStanowisko | query | False | integer | {"minimum":1,"maximum":99999999} | Liczba odpowiadająca statusowi stanowiska, np. '2' - dla stanowisk o statusie "aktywny" |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeStanowiskoIdOdpowiedz`

### GET `/v1/stanowisko-id-dep`

Lista stanowisk dotyczących monitoringu chemizmu opadów atmosferycznych (depozycji) (stanowiskoId)

Lista stanowisk pomiarowych dotyczących monitoringu chemizmu opadów atmosferycznych - depozycji udostępniająca numer id  stanowiska (stanowiskoId) na potrzeby innych usług, np. pobierania po id stanowiska

operationId: `getIdStanowiskoIdDepV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| stanowiskoId | query | False | integer | {"minimum":0,"maximum":99999999} | Identyfikator stanowiska |
| idStacja | query | False | integer | {"minimum":0,"maximum":99999999} | Identyfikator stacji |
| idWskaznik | query | False | integer | {"minimum":0,"maximum":99999999} | Identyfikator wskaźnika - liczba. Przykład: 43 (id dla stanowiska DsOsieczow21-BjF(cdepoz)-1m) |
| statusStanowisko | query | False | integer | {"minimum":1,"maximum":99999999} | Liczba odpowiadająca statusowi stanowiska, np. '2' - dla stanowisk o statusie "aktywny" |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeStanowiskoIdDepOdpowiedz`

### GET `/v1/raporty-oceny-roczne`

Raporty - Wyniki ocen jakości powietrza

Usługa sieciowa udostępniająca raporty z rocznych ocen jakości powietrza, w zakresie raportów z rocznych ocen jakości powietrza za dany rok

operationId: `getRaportyOcenyRoczneV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| ocenianyRok | query | True | integer | {"minimum":2012,"maximum":9999} | Oceniany rok np. 2022. – dostępne są dane od 2012 roku |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeRaportOcenaRocznaOdpowiedz`

### GET `/v1/raporty-oceny-wieloletnie`

Raporty - Wyniki ocen na potrzeby ustalenia metod wykonywania rocznych ocen jakości powietrza

Usługa sieciowa udostępniająca raporty z ocen wykonywanych  na potrzeby ustalenia metod wykonywania rocznych ocen jakości powietrza w poszczególnych strefach (tzw. ocen wieloletnich)

operationId: `getRaportyOcenyWieloletnieV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rokOd | query | True | integer | {"minimum":2014,"maximum":9999} | Rok raportu od |
| rokDo | query | False | integer | {"minimum":2014,"maximum":9999} | Rok raportu do |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["dolnośląskie","kujawsko-pomorskie","lubelskie","lubuskie","łódzkie","małopolskie","mazowieckie","opolskie","podkarpackie","podlaskie","pomorskie","śląskie","świętokrzyskie","warmińsko-mazurskie","wielkopolskie","zachodniopomorskie"]} | Województwo |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `PowietrzeRaportOcenaWieloletniaOdpowiedz`

### GET `/v1/plik/{id}`

Pobieranie dokumentu w postaci pliku PDF lub JSON

Usługa sieciowa pozwalająca na pobranie dokumentu. Identyfikator dokumentu należy pobrać wywołując jedną z poniższych usług podając parametry zapytania zgodnie z dokumentacją: <br> - Raporty - Wyniki ocen jakości powietrza (/v1/raporty-oceny-roczne)<br> - Raporty - Wyniki ocen na potrzeby ustalenia metod wykonywania rocznych ocen jakości powietrza (/v1/raporty-oceny-wieloletnie)

operationId: `getDokumentV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| id | path | True | integer / int64 | {"minimum":1,"maximum":9223372036854775807} | Identyfikator pliku |
| format | query | True | FormatPlikuEnum | {"enum":["PDF","JSON"]} | Format pliku |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `unspecified`, application/pdf → `string / binary`

## Pełny słownik schematów

### `PowietrzeWynikiRocznychRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| idOcenaRoczna | integer | False | {} |  |
| ocenianyRok | integer | False | {} |  |
| wojewodztwo | Wojewodztwo | False | {} |  |
| ocena | object | False | {} |  |
| ocena.status | integer | False | {} |  |
| ocena.kod | string | False | {"maxLength":20} |  |
| odnosnikDoRaportu | string | False | {"maxLength":255} |  |
| czyAktualnaWersja | boolean | False | {} |  |
| idWynikuOcenyRocznejDlaWsk | integer | False | {} |  |
| klasaStrefyDlaWskaznika | string | False | {} |  |
| strefa | Strefa | False | {} |  |
| wskaznik | Wskaznik | False | {} |  |
| celOchrony | string | False | {"maxLength":255} |  |
| typNormy | string | False | {"maxLength":100} |  |
| idWynikOcenyDlaParametru | integer | False | {} |  |
| idCeluSrodowiskowego | integer | False | {} |  |
| miaraRaportowania | string | False | {"maxLength":50} |  |
| metodaOceny | string | False | {"maxLength":2} |  |
| czyWykorzystanoMetodaPomiarowa | boolean | False | {} |  |
| czyWykorzystanoMetodePomiarowAutomatycznych | boolean | False | {} |  |
| czyWykorzystanoMetodePomiarowManualnych | boolean | False | {} |  |
| czyWykorzystanoMetodePomiarowPasywnych | boolean | False | {} |  |
| czyWykorzystanoMetodeModelowania | boolean | False | {} |  |
| czyWykorzystanoMetodeSzacowania | boolean | False | {} |  |
| komentarzDoOceny | string | False | {"maxLength":4000} |  |
| najgorszaWartoscStatystyki | number | False | {} |  |
| wynikOceny | string | False | {} |  |
| kodPrzekroczenia | string | False | {"maxLength":100} |  |
| czyTypObszaruMiejski | boolean | False | {} |  |
| czyTypObszaruPodmiejski | boolean | False | {} |  |
| czyTypObszaruPozamiejski | boolean | False | {} |  |
| powierzchniaPrzekroczenia | number | False | {} |  |
| dlugoscDrogiZPrzekroczeniem | number | False | {} |  |
| liczbaMieszkancowNarazonych | integer | False | {} |  |
| komentarzDoPrzekroczenia | string | False | {"maxLength":4000} |  |
| idStatusOdliczenia | integer | False | {} |  |
| przyczynyPrzekroczenia | string | False | {"maxLength":4000} |  |
| idGminyPrzekroczenia | integer | False | {} |  |
| kodTerytGminyPrzekroczenia | string | False | {} |  |
| nazwaGminyPrzekroczenia | string | False | {} |  |
| nazwaGminyZTypemPrzekroczenia | string | False | {} |  |
| typGminyPrzekroczenia | string | False | {} |  |
| nazwaPowiatuPrzekroczenia | string | False | {} |  |
| nazwaWojewodztwaPrzekroczenia | string | False | {} |  |

### `PowietrzewynikiOcenRocznychOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeWynikiRocznychRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeWynikiOcenStezeniaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rok | integer | False | {} |  |
| stanowiskoId | integer | False | {} |  |
| sredniaRoczna | number | False | {} |  |
| sredniaZimowa | number | False | {} |  |
| minRoczne | number | False | {} |  |
| maxRoczne | number | False | {} |  |
| maxDobowe | number | False | {} |  |
| max8Godzinne | number | False | {} |  |
| kompletnosc | number | False | {} |  |
| kodStanowiska | string | False | {} |  |
| wskaznik | object | False | {} |  |
| wskaznik.id | integer | False | {} |  |
| wskaznik.nazwa | string | False | {} |  |
| czasUsredniania | string | False | {} |  |
| jednostka | string | False | {} |  |

### `PowietrzeWynikiOcenStezeniaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeWynikiOcenStezeniaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeWynikiOcenWieloletnichRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| idOceny | integer | False | {} |  |
| rokWykonaniaOceny | integer | False | {} |  |
| wojewodztwo | Wojewodztwo | False | {} |  |
| ocena | object | False | {} |  |
| ocena.status | integer | False | {} |  |
| ocena.kod | string | False | {"maxLength":20} |  |
| ocena.zakresLat | string | False | {} |  |
| odnosnikDoRaportu | string | False | {"maxLength":255} |  |
| idWynikuOcenyWieloletniejDlaWskaznika | integer | False | {} |  |
| klasaStrefyDlaWskaznika | string | False | {"maxLength":3} |  |
| strefa | Strefa | False | {} |  |
| wskaznik | Wskaznik | False | {} |  |
| celOchrony | string | False | {"maxLength":255} |  |
| liczbaMieszkancowStrefy | integer | False | {} |  |
| komentarzDoWynikuOceny | string | False | {} |  |
| idWynikuOcenyWieloletniejDlaParametru | string | False | {"maxLength":4000} |  |
| idCeluSrodowiskowego | integer | False | {} |  |
| miaraRaportowania | string | False | {"maxLength":50} |  |
| klasaStrefyDlaParametru | string | False | {"maxLength":3} |  |
| plan | object | False | {} |  |
| plan.pomiaryIntensywne | boolean | False | {} |  |
| plan.pomiaryWskaznikowe | boolean | False | {} |  |
| plan.modelowanie | boolean | False | {} |  |
| wymagane | object | False | {} |  |
| wymagane.pomiaryIntensywne | boolean | False | {} |  |
| wymagane.inne | boolean | False | {} |  |
| liczbaStanowiskIst | object | False | {} |  |
| liczbaStanowiskIst.tla | integer | False | {} |  |
| liczbaStanowiskIst.komunikacyjnych | integer | False | {} |  |
| liczbaStanowiskIst.przemyslowych | integer | False | {} |  |
| liczbaStanowiskPlan | object | False | {} |  |
| liczbaStanowiskPlan.tla | integer | False | {} |  |
| liczbaStanowiskPlan.komunikacyjnych | integer | False | {} |  |
| liczbaStanowiskPlan.przemyslowych | integer | False | {} |  |
| liczbaStanowiskWym | object | False | {} |  |
| liczbaStanowiskWym.tla | integer | False | {} |  |
| liczbaStanowiskWym.komunikacyjnych | integer | False | {} |  |
| liczbaStanowiskWym.przemyslowych | integer | False | {} |  |
| liczbaStanowiskWymInne | object | False | {} |  |
| liczbaStanowiskWymInne.tla | integer | False | {} |  |
| liczbaStanowiskWymInne.komunikacyjnych | integer | False | {} |  |
| liczbaStanowiskWymInne.przemyslowych | integer | False | {} |  |

### `PowietrzeWynikiOcenWieloletnichOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeWynikiOcenWieloletnichRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzePm25MetadaneStanowiskRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| wskaznik | Wskaznik | False | {} |  |
| stacja | Stacja | False | {} |  |
| gmina | string | False | {"maxLength":50} |  |
| powiat | string | False | {"maxLength":50} |  |
| wojewodztwo | WojewodztwoEnum | False | {} |  |
| czasUsredniania | string | False | {"maxLength":100} |  |
| metodaAnalizy | string | False | {} |  |
| dataPoczatkuMetodyAnalizy | string / date | False | {} |  |
| dataKoncaMetodyAnalizy | string / date | False | {} |  |
| metodaPoboruProby | string | False | {} |  |
| dataPoczatkuMetodyPoboruProby | string / date | False | {} |  |
| dataKoncaMetodyPoboruProby | string / date | False | {} |  |

### `PowietrzePm25MetadaneStanowiskOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzePm25MetadaneStanowiskRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzePm25WynikiPomiarowRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| dataPomiaru | string / date | False | {} |  |
| wartosc | number | False | {} |  |
| jednostkaPomiaru | string | False | {"maxLength":100} |  |
| dane | Dane | False | {} |  |
| rok | integer | False | {} |  |
| miesiac | integer | False | {} |  |
| dzien | integer | False | {} |  |

### `PowietrzePm25WynikiPomiarowOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzePm25WynikiPomiarowRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzePm25StatystykiRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| wskaznik | Wskaznik | False | {} |  |
| czasUsredniania | string | False | {"maxLength":100} |  |
| stacja | Stacja | False | {} |  |
| gmina | string | False | {"maxLength":50} |  |
| powiat | string | False | {"maxLength":50} |  |
| wojewodztwo | WojewodztwoEnum | False | {} |  |
| sredniaRoczna | number / double | False | {} |  |
| jednostkaPomiaru | string | False | {"maxLength":100} |  |
| kompletnosc | number / double | False | {} |  |
| rok | integer | False | {} |  |
| czyWPMS | boolean | False | {} |  |
| czyWykorzystane | boolean | False | {} |  |

### `PowietrzePm25StatystykiOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzePm25StatystykiRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeMetodaPomiarowaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| wskaznik | WskaznikNazwaKod | False | {} |  |
| czasUsredniania | string | False | {"maxLength":100} |  |
| stacja | Stacja | False | {} |  |
| gmina | string | False | {"maxLength":50} |  |
| powiat | string | False | {"maxLength":50} |  |
| wojewodztwo | WojewodztwoEnum | False | {} |  |
| rok | integer | False | {} |  |
| referencyjnoscMetody | string | False | {} |  |

### `PowietrzeMetodyPomiaroweOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeMetodaPomiarowaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeChemizmOpadowRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | StanowiskoRozszerzony | False | {} |  |
| stacja | StacjaRozszerzony | False | {} |  |
| gmina | string | False | {"maxLength":50} |  |
| powiat | string | False | {"maxLength":50} |  |
| wojewodztwo | WojewodztwoEnum | False | {} |  |
| gegrLat | string | False | {"maxLength":50} |  |
| gegrLon | string | False | {"maxLength":50} |  |
| coord1992X | string | False | {"maxLength":50} |  |
| coord1992Y | string | False | {"maxLength":50} |  |
| wysokoscNMP | string | False | {"maxLength":50} |  |
| typObszaru | string | False | {} |  |
| adres | string | False | {"maxLength":255} |  |
| komentarzDotOtoczenia | string | False | {"maxLength":2048} |  |
| wskaznik | Wskaznik | False | {} |  |
| pomiar | PomiarTypTryb | False | {} |  |
| czasUsredniania | string | False | {"maxLength":100} |  |
| metodaAnalizy | string | False | {} |  |
| dataPoczatkuMetodyAnalizy | string / date | False | {} |  |
| dataKoncaMetodyAnalizy | string / date | False | {} |  |
| metodaPomiaru | string | False | {} |  |
| dataPoczatkuMetodyPomiaru | string / date | False | {} |  |
| dataKoncaMetodyPomiaru | string / date | False | {} |  |
| metodaPoboruProby | string | False | {} |  |
| dataPoczatkuMetodyPoboruProby | string / date | False | {} |  |
| dataKoncaMetodyPoboruProby | string / date | False | {} |  |

### `PowietrzeChemizmOpadowOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeChemizmOpadowRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeChemizmOpadowWynikiPomiarowRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| wskaznik | Wskaznik | False | {} |  |
| czasUsredniania | string | False | {} |  |
| dataPoczatkuPomiaru | string / date | False | {} |  |
| dataKoncaPomiaru | string / date | False | {} |  |
| wartosc | number | False | {} |  |
| jednostkaPomiaru | string | False | {"maxLength":100} |  |
| weryfikacjaDanych | WeryfikacjaDanych | False | {} |  |
| jakoscDanych | JakoscDanych | False | {} |  |
| czyArchiwalny | boolean | False | {} |  |
| rok | integer | False | {} |  |
| miesiac | integer | False | {} |  |
| dzien | integer | False | {} |  |

### `PowietrzeChemizmOpadowWynikiPomiarowOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeChemizmOpadowWynikiPomiarowRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeChemizmOpadowAgregatyRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| wskaznik | WskaznikNazwaKod | False | {} |  |
| czasUsredniania | string | False | {"maxLength":100} |  |
| stacja | Stacja | False | {} |  |
| gmina | string | False | {"maxLength":50} |  |
| powiat | string | False | {"maxLength":50} |  |
| wojewodztwo | WojewodztwoEnum | False | {} |  |
| dzienPomiaru | string / date | False | {} |  |
| wartoscSredniaDobowaStezenia | number | False | {} |  |
| kompletnoscDanychDoSredniej | number | False | {} |  |
| wartoscSumyDobowej | number | False | {} |  |
| kompletnoscSumyDobowej | number | False | {} |  |
| jednostkaPomiaru | string | False | {"maxLength":100} |  |

### `PowietrzeChemizmOpadowAgregatyOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeChemizmOpadowAgregatyRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeChemizmOpadowSrednieRoczneRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | Stanowisko | False | {} |  |
| stacja | Stacja | False | {} |  |
| gmina | string | False | {"maxLength":50} |  |
| powiat | string | False | {"maxLength":50} |  |
| wojewodztwo | WojewodztwoEnum | False | {} |  |
| sredniaRoczna | number | False | {} |  |
| kompletnosc | number | False | {} |  |
| rok | integer | False | {} |  |
| czyWpms | boolean | False | {} |  |
| rocznaSumaOdpaduMokrego | number | False | {} |  |
| roczneSredniowazoneStezenie | number | False | {} |  |
| sredniRocznyOdczynPh | number | False | {} |  |
| rocznyLadunekOpadzieMokrym | number | False | {} |  |
| rocznyLadunekOpadzieCalkowitym | number | False | {} |  |
| jednostkaPomiaru | string | False | {} |  |

### `PowietrzeChemizmOpadowSrednieRoczneOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeChemizmOpadowSrednieRoczneRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeStanowiskoIdRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | StanowiskoRozszerzony | False | {} |  |
| stacja | object | False | {} |  |
| stacja.id | integer | False | {} |  |
| wskaznik | object | False | {} |  |
| wskaznik.id | integer | False | {} |  |
| pomiar | PomiarTypTryb | False | {} |  |
| godzinaPoboru | string | False | {} |  |
| czyStanowiskoMaDaneObliczane | boolean | False | {} |  |

### `PowietrzeStanowiskoIdOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeStanowiskoIdRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeIdStanowiskoIdDepRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| stanowisko | StanowiskoRozszerzony | False | {} |  |
| stacja | object | False | {} |  |
| stacja.id | integer | False | {} |  |
| wskaznik | object | False | {} |  |
| wskaznik.id | integer | False | {} |  |
| pomiar | PomiarTypTryb | False | {} |  |
| godzinaPoboru | string | False | {"maxLength":10} |  |
| czyStanowiskoMaDaneObliczane | string | False | {"maxLength":1} |  |

### `PowietrzeStanowiskoIdDepOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeIdStanowiskoIdDepRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeRaportOcenaRocznaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| plikId | integer | False | {} |  |
| plikNazwa | string | False | {} |  |
| dokumentTytul | string | False | {} |  |
| dataWykonania | string / date | False | {} |  |
| ocenianyRok | integer | False | {} |  |

### `PowietrzeRaportOcenaRocznaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeRaportOcenaRocznaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeRaportOcenaWieloletniaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| plikId | integer | False | {} |  |
| plikNazwa | string | False | {} |  |
| dokumentTytul | string | False | {} |  |
| dataWykonania | string / date | False | {} |  |
| rokOd | integer | False | {} |  |
| rokDo | integer | False | {} |  |

### `PowietrzeRaportOcenaWieloletniaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PowietrzeRaportOcenaWieloletniaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PowietrzeCelOchronyEnum`



```json
{
  "type": "string",
  "enum": [
    "OZ",
    "OR"
  ]
}
```

### `Wojewodztwo`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| nazwa | string | False | {"maxLength":50} |  |

### `Strefa`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| kod | string | False | {"maxLength":50} |  |
| nazwa | string | False | {"maxLength":50} |  |

### `Wskaznik`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| nazwa | string | False | {"maxLength":100} |  |
| kod | string | False | {"maxLength":50} |  |

### `WskaznikNazwaKod`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| nazwa | string | False | {"maxLength":100} |  |
| kod | string | False | {"maxLength":50} |  |

### `Stanowisko`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| kod | string | False | {"maxLength":60} |  |

### `StanowiskoRozszerzony`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| kod | string | False | {} |  |
| status | integer | False | {} |  |
| dataUruchomienia | string / date | False | {} |  |
| dataZamkniecia | string / date | False | {} |  |
| typ | integer | False | {} |  |
| opis | string | False | {} |  |

### `Metoda`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| poboruProby | string | False | {} |  |
| analizy | string | False | {} |  |
| pomiaru | string | False | {} |  |

### `Stacja`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| kod | string | False | {"maxLength":50} |  |
| kodUE | string | False | {"maxLength":50} |  |
| nazwa | string | False | {"maxLength":255} |  |

### `StacjaRozszerzony`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} |  |
| kod | string | False | {"maxLength":50} |  |
| kodUE | string | False | {"maxLength":50} |  |
| nazwa | string | False | {"maxLength":255} |  |
| dataUruchomienia | string / date | False | {} |  |
| dataZamkniecia | string / date | False | {} |  |
| status | string | False | {"maxLength":255} |  |
| wlasciciel | string | False | {} |  |
| typ | string | False | {} |  |
| rodzaj | string | False | {} |  |
| dodatkowyOpis | string | False | {"maxLength":255} |  |

### `PomiarTypTryb`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| typ | string | False | {"maxLength":50} |  |
| tryb | string | False | {"maxLength":50} |  |

### `WeryfikacjaDanych`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| status | string | False | {"maxLength":50} |  |
| kod | string | False | {"maxLength":50} |  |

### `JakoscDanych`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| status | string | False | {"maxLength":50} |  |
| kod | string | False | {"maxLength":50} |  |

### `Dane`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| status | string | False | {"maxLength":50} |  |
| kod | string | False | {"maxLength":50} |  |

### `FormatPlikuEnum`



```json
{
  "type": "string",
  "enum": [
    "PDF",
    "JSON"
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
