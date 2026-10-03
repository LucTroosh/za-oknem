# HALAS API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-halas.yaml. Pobrano 2026-10-03. SHA-256: `429f51e7d1ee001dfe673ef8729d0e280014e0dea8bd6906f00cda19eb5bfa51`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/halas

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/pomiar-halasu-w-srodowisku`

Dane z pomiarów hałasu w środowisku

Usługa sieciowa udostępniająca dane z pomiarów hałasu w środowisku

operationId: `getPomiarHalasuWSrodowiskuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| kodPunktuPomiarowego | query | False | string | {"maxLength":16} | Kod punktu pomiarowego |
| kategoria | query | True | HalasKategoriaHalasuEnum | {"enum":["Droga","Lotnisko","Przemysł","Kolej"]} | Kategoria hałasu |
| celPomiaru | query | False | string | {"maxLength":500} | Cel pomiaru. Dostępne wartości:<br> - Pomiar wykonany w ramach kontroli przeprowadzonej przez Urząd Marszałkowski <br> - Pomiar wykonany w ramach kontroli przeprowadzonej przez starostę <br> - Analiza porealizacyjna <br> - Inny <br> - Pomiar wykonany w ramach mapy akustycznej <br> - Pomiar w trybie art.147 ust.1 Poś (pomiary okresowe) <br> - Pomiar w trybie art.175 ust.3 Poś (przebudowa) <br> - Pomiar w trybie art.175 ust.2 Poś (pomiary ciągłe) <br> - Pomiar w trybie art.175 ust.1 Poś (pomiary okresowe) <br> - Pomiar wykonywany w ramach kontroli prowadzonej przez WIOŚ <br> - Państwowy monitoring środowiska, art. 26 Poś |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| powiat | query | False | string | {"maxLength":50} | Powiat, np. 'Wrocław', 'oławski' |
| gmina | query | False | string | {"maxLength":50} | Gmina, np. 'Wrocław (gmina miejska)', 'Oława (gmina miejska)' |
| dataOd | query | True | string / date | {} | Data od w formacie ISO 8601, np. 2023-11-29. <br>Format: yyyy-mm-dd |
| dataDo | query | True | string / date | {} | Data do w formacie ISO 8601, np. 2023-11-29. <br>Format: yyyy-mm-dd |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasPomiarHalasuWSrodowiskuOdpowiedz`

### GET `/v1/jednostka-odpowiedzialna`

Jednostki odpowiedzialne za sporządzanie lub gromadzenie strategicznych map hałasu oraz programów ochrony przed hałasem

Usługa sieciowa udostępniająca dane adresowe jednostek odpowiedzialnych za sporządzanie lub gromadzenie strategicznych map hałasu oraz programów ochrony środowiska przed hałasem w podziale na źródła hałasu

operationId: `getJednostkaOdpowiedzialnaV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wojewodztwo | query | False | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| miejscowosc | query | False | string | {"maxLength":255} | Miejscowość |
| rundaMapowania | query | False | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | False | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości: Drogi, Koleje, Miasta, Lotniska, wszystkie źródła |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasJednostkaOdpowiedzialnaOdpowiedz`

### GET `/v1/dzialania-w-zakresie-ochrony-srodowiska-przed-halasem`

Działania w zakresie ochrony środowiska przed hałasem

Usługa sieciowa udostępniająca informacje o planowanych działaniach w zakresie ochrony przed hałasem, jakie właściwe władze zamierzają podjąć w ciągu najbliższych pięciu lat lub w ramach długofalowej strategii, łącznie ze środkami zachowania obszarów ciszy na obszarze województwa, w podziale na rundy mapowania

operationId: `getDzialaniaWZakresieOchronySrodowiskaPrzedHalasemV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| rundaMapowania | query | True | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | False | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne lotniska poza aglomeracjami<br> - Hałas pochodzący od głównych dróg wewnątrz aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne drogi poza aglomeracjami<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Główne linie kolejowe poza aglomeracjami<br> - Hałas pochodzący od głównych linii kolejowych wewnątrz aglomeracji<br> - Hałas pochodzący z głównych lotnisk wewnątrz aglomeracji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasDzialaniaWZakresieOchronySrodowiskaPrzedHalasemOdpowiedz`

### GET `/v1/liczba-ludnosci-eksponowanej-na-halas`

Liczba ludności eksponowanej na hałas

Usługa sieciowa udostępniająca informacje o liczbie ludności eksponowanej na hałas dla wskaźników L den >= 55 dB lub L night >=50 dB na obszarze objętym programem środowiska przed hałasem (województwo) lub o zmniejszeniu liczby osób narażonych na hałas na podstawie wskaźników NHA i NHSD, w podziale na rundy mapowania

operationId: `getLiczbaLudnosciEksponowanejNaHalasV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| rundaMapowania | query | True | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | False | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne lotniska poza aglomeracjami<br> - Hałas pochodzący od głównych dróg wewnątrz aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne drogi poza aglomeracjami<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Główne linie kolejowe poza aglomeracjami<br> - Hałas pochodzący od głównych linii kolejowych wewnątrz aglomeracji<br> - Hałas pochodzący z głównych lotnisk wewnątrz aglomeracji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasLiczbaLudnosciEksponowanejNaHalasOdpowiedz`

### GET `/v1/srodki-ochrony-przed-halasem`

Informacje o istniejących środkach ochrony przed hałasem

Usługa sieciowa udostępniająca informacje o istniejących środkach ochrony przed hałasem na terenie województwa, w podziale na rundy mapowania

operationId: `getSrodkiOchronyPrzedHalasemV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| rundaMapowania | query | True | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | False | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne lotniska poza aglomeracjami<br> - Hałas pochodzący od głównych dróg wewnątrz aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne drogi poza aglomeracjami<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Główne linie kolejowe poza aglomeracjami<br> - Hałas pochodzący od głównych linii kolejowych wewnątrz aglomeracji<br> - Hałas pochodzący z głównych lotnisk wewnątrz aglomeracji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasSrodkiOchronyPrzedHalasemOdpowiedz`

### GET `/v1/zasiegi-halasu`

Zasięgi hałasu

Usługa sieciowa udostępniająca zasięgi hałasu dla wskaźnika hałasu L den lub L night w danym województwie/kraju w przedziałach co 5 dB, w podziale na rundy mapowania

operationId: `getZasiegiHalasuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| id | query | False | integer / int64 | {"minimum":1,"maximum":9223372036854775807} | Identyfikator |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| rundaMapowania | query | True | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | True | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne drogi z uwzględnieniem aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne linie kolejowe z uwzględnieniem aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Główne porty lotnicze z uwzględnieniem aglomeracji |
| wskaznik | query | False | string | {"maxLength":1020} | Wskaźnik, np. LN, LDWN |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasZasiegiHalasuOdpowiedz`

### GET `/v1/informacja-o-powierzchni-terenu`

Informacja o powierzchni terenu oraz liczbie lokali mieszkalnych, szkół, szpitali lub osób

Usługa sieciowa udostępniająca przybliżoną liczbę lokali mieszkalnych lub szkół lub szpitali lub osób, które na danym obszarze (powiat/województwo) znajdują się w zasięgu wskaźników L den lub L night w przedziałach co 5 dB, w podziale na rundy mapowania. Wielkość obszaru (narażony obszar) wyrażona w km2 dla danego zasięgu hałasu.

operationId: `getInformacjaOPowierzchniTerenuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| rundaMapowania | query | True | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | True | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne drogi z uwzględnieniem aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne linie kolejowe z uwzględnieniem aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Główne porty lotnicze z uwzględnieniem aglomeracji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasInformacjaOPowierzchniTerenuOdpowiedz`

### GET `/v1/koszty-dzialan-w-programach-ochrony-srodowiska`

Informacja o kosztach działań w programach ochrony środowiska przed hałasem

Usługa sieciowa udostępniająca informacje o kosztach działań w programie ochrony środowiska przed hałasem, ocenie efektywności kosztowej, ocenie relacji koszt/korzyść, na obszarze województwa

operationId: `getKosztyDzialanWProgramachOchronySrodowiskaV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| wojewodztwo | query | True | WojewodztwoEnum | {"enum":["DOLNOŚLĄSKIE","KUJAWSKO-POMORSKIE","LUBELSKIE","LUBUSKIE","ŁÓDZKIE","MAŁOPOLSKIE","MAZOWIECKIE","OPOLSKIE","PODKARPACKIE","PODLASKIE","POMORSKIE","ŚLĄSKIE","ŚWIĘTOKRZYSKIE","WARMIŃSKO-MAZURSKIE","WIELKOPOLSKIE","ZACHODNIOPOMORSKIE"]} | Województwo |
| rundaMapowania | query | True | string | {"maxLength":255} | Runda mapowania, np. 4 Runda Mapowania, 5 Runda Mapowania |
| zrodloHalasu | query | True | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne drogi z uwzględnieniem aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne linie kolejowe z uwzględnieniem aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Główne porty lotnicze z uwzględnieniem aglomeracji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasKosztyDzialanWProgramachOchronySrodowiskaOdpowiedz`

### GET `/v1/dopuszczalne-poziomy-halasu`

Dopuszczalne poziomy hałasu

Usługa sieciowa udostępniająca wartości dopuszczalnych poziomów hałasu dla wskaźników L den i L night dla hałasu drogowego, kolejowego, lotniczego i instalacyjnego dla określonych rodzajów terenów

operationId: `getDopuszczalnePoziomyHalasuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rodzajTerenu | query | True | HalasRodzajTerenuEnum | {"enum":["Strefa ochronna \"A\" uzdrowiska","Tereny domów opieki społecznej","Tereny mieszkaniowo-usługowe","Tereny rekreacyjno-wypoczynkowe","Tereny szpitali poza miastem","Tereny szpitali w miastach","Tereny w strefie śródmiejskiej miast powyżej 100 tys. mieszkańców","Tereny zabudowy mieszkaniowej jednorodzinnej","Tereny zabudowy mieszkaniowej wielorodzinnej i zamieszkania zbiorowego","Tereny zabudowy zagrodowej","Tereny zabudowy związanej ze stałym lub czasowym pobytem dzieci i młodzieży"]} | Rodzaj terenu |
| zrodloHalasu | query | False | string | {"maxLength":300} | Źródło hałasu. Dostępne wartości:<br> - Hałas kolejowy wewnątrz aglomeracji<br> - Główne lotniska poza aglomeracjami<br> - Hałas pochodzący od głównych dróg wewnątrz aglomeracji<br> - Hałas drogowy wewnątrz aglomeracji<br> - Główne drogi poza aglomeracjami<br> - Hałas lotniczy wewnątrz aglomeracji<br> - Hałas przemysłowy wewnątrz aglomeracji<br> - Główne linie kolejowe poza aglomeracjami<br> - Hałas pochodzący od głównych linii kolejowych wewnątrz aglomeracji<br> - Hałas pochodzący z głównych lotnisk wewnątrz aglomeracji |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `HalasDopuszczalnePoziomyHalasuOdpowiedz`

## Pełny słownik schematów

### `HalasPomiarHalasuWSrodowiskuRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| kodPunktuPomiarowego | string | False | {"maxLength":16} | Kod punktu pomiarowego |
| kategoria | HalasKategoriaHalasuEnum | False | {} | Kategoria |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| powiat | string | False | {"maxLength":50} | Powiat |
| gmina | string | False | {"maxLength":50} | Gmina |
| miejscowosc | string | False | {"maxLength":100} | Miejscowość |
| coordWgs84X | number / double | False | {} | Współrzędne WGS84X |
| coordWgs84Y | number / double | False | {} | Współrzędne WGS84Y |
| pora | string | False | {"maxLength":255} | Pora |
| celPomiaru | string | False | {"maxLength":500} | Cel |
| dataOd | string / date | False | {} | Data od |
| dataDo | string / date | False | {} | Data do |
| wynikPomiaru | number | False | {} | Wynik pomiaru [dB] |
| przekroczenie | number | False | {} | Przekroczenie [dB] |

### `HalasPomiarHalasuWSrodowiskuOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasPomiarHalasuWSrodowiskuRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasJednostkaOdpowiedzialnaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rundaMapowania | string | False | {} | Runda mapowania |
| zrodloHalasu | string | False | {"maxLength":300} | Źródło hałasu |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| miejscowosc | string | False | {"maxLength":255} | Miejscowość |
| rola | string | False | {"maxLength":255} | Rola |
| nazwaInstytucji | string | False | {"maxLength":255} | Nazwa instytucji |
| ulica | string | False | {"maxLength":255} | Ulica |
| numerBudynku | string | False | {"maxLength":255} | Numer budynku |
| kodPocztowy | string | False | {"maxLength":255} | Kod pocztowy |
| poczta | string | False | {"maxLength":255} | Poczta |

### `HalasJednostkaOdpowiedzialnaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasJednostkaOdpowiedzialnaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasDzialaniaWZakresieOchronySrodowiskaPrzedHalasemRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rundaMapowania | string | False | {} | Runda mapowania |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| zrodloHalasu | string | False | {"maxLength":300} | Źródło hałasu |
| planowaneDzialaniaDlaLotniskWMiescie | string | False | {"maxLength":4000} | Planowane działania dla lotnisk w mieście |
| planowaneDzialaniaDlaKoleiWMiescie | string | False | {"maxLength":4000} | Planowane działania dla linii kolejowych w mieście |
| planowaneDzialaniaDlaDrogWMiescie | string | False | {"maxLength":4000} | Planowane działania dla dróg w mieście |
| planowaneDzialaniaDlaPrzemysluWMiescie | string | False | {"maxLength":4000} | Planowane działania dla przemysłu w mieście |
| planowaneDzialaniaDlaDrog | string | False | {"maxLength":4000} | Planowane działania dla dróg |
| planowaneDzialaniaDlaKolei | string | False | {"maxLength":4000} | Planowane działania dla kolei |
| planowaneDzialaniaDlaLotnisk | string | False | {"maxLength":4000} | Planowane działania dla lotnisk |

### `HalasDzialaniaWZakresieOchronySrodowiskaPrzedHalasemOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasDzialaniaWZakresieOchronySrodowiskaPrzedHalasemRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasLiczbaLudnosciEksponowanejNaHalasRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rundaMapowania | string | False | {} | Runda mapowania |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| zrodloHalasu | string | False | {"maxLength":300} | Źródło hałasu |
| zredukowanyWskaznikHa | number | False | {} | Zredukowany wskaźnik HA |
| zredukowanyWskaznikHsd | number | False | {} | Zredukowany wskaźnik HSD |
| wskaznikHaPrzedRedukcja | number | False | {} | Wskaźnik HA przed redukcją |
| wskaznikHsdPrzedRedukcja | number | False | {} | Wskaźnik HSD przed redukcją |
| liczbaNarazonychPowLdwn55 | number | False | {} | Liczba narażonych mieszkańców dla wskaźnika Ldwn>55dB |
| liczbaNarazonychPowLn50 | number | False | {} | Liczba narażonych mieszkańców dla wskaźnika Ln>50dB |
| redukcjaNha | number | False | {} | Zmniejszenie wskaźnika NHA |
| redukcjaNhsd | number | False | {} | Zmniejszenie wskaźnika NHSD |

### `HalasLiczbaLudnosciEksponowanejNaHalasOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasLiczbaLudnosciEksponowanejNaHalasRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasSrodkiOchronyPrzedHalasemRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rundaMapowania | string | False | {} | Runda mapowania |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| zrodloHalasu | string | False | {"maxLength":300} | Źródło hałasu |
| istniejaceDzialaniaDlaLotniskWMiescie | string | False | {"maxLength":4000} | Istniejące działania dla lotnisk w mieście |
| istniejaceDzialaniaDlaKoleiWMiescie | string | False | {"maxLength":4000} | Istniejące działania dla linii kolejowych w mieście |
| istniejaceDzialaniaDlaDrogWMiescie | string | False | {"maxLength":4000} | Istniejące działania dla dróg w mieście |
| istniejaceDzialaniaDlaPrzemysluWMiescie | string | False | {"maxLength":4000} | Istniejące działania dla przemysłu w mieście |
| istniejaceDzialaniaDlaDrog | string | False | {"maxLength":4000} | Istniejące działania dla dróg |
| istniejaceDzialaniaDlaKolei | string | False | {"maxLength":4000} | Istniejące działania dla kolei |
| istniejaceDzialaniaDlaLotnisk | string | False | {"maxLength":4000} | Istniejące działania dla lotnisk |

### `HalasSrodkiOchronyPrzedHalasemOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasSrodkiOchronyPrzedHalasemRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasZasiegiHalasuProperties`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| id | integer | False | {} | Identyfikator |
| rundaMapowania | string | False | {} | Runda mapowania |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| zrodloHalasu | string | False | {"maxLength":80} | Źródło hałasu |
| przedzial | string | False | {"maxLength":50} | Przedział |
| wskaznik | string | False | {"maxLength":1020} | Wskaźnik |

### `HalasZasiegiHalasuGeoJSONFeature`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| type | string | False | {"example":"Feature"} |  |
| geometry | object | False | {} |  |
| geometry.type | string | False | {"example":"Point"} |  |
| geometry.coordinates | array of number | False | {"example":[102.0,0.5]} |  |
| properties | HalasZasiegiHalasuProperties | False | {} |  |

### `HalasZasiegiHalasuOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| liczbaRekordow | integer | False | {} |  |
| type | string | False | {"example":"FeatureCollection"} |  |
| features | array of HalasZasiegiHalasuGeoJSONFeature | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasInformacjaOPowierzchniTerenuRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rundaMapowania | string | False | {} | Runda mapowania |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| powiat | string | False | {} | Powiat |
| zrodloHalasu | string | False | {"maxLength":80} | Źródło hałasu |
| wskaznik | string | False | {"maxLength":1020} | Wskaźnik |
| przedzial | string | False | {"maxLength":50} | Przedział |
| narazonyObszar | number | False | {} | Obszar eksponowany na hałas |
| narazoneBudynkiMieszkalne | number | False | {} | Liczba budynków mieszkalnych eksponowanych na hałas |
| narazonaLudnosc | number | False | {} | Liczba mieszkańców narażonych na hałas |
| narazoneBudynkiSzpitalne | number | False | {} | Liczba budynków szpitalnych narażonych na hałas |
| narazoneBudynkiEdukacyjne | number | False | {} | Liczba budynków edukacyjnych narażonych na hałas |

### `HalasInformacjaOPowierzchniTerenuOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasInformacjaOPowierzchniTerenuRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasKosztyDzialanWProgramachOchronySrodowiskaRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rundaMapowania | string | False | {} | Runda mapowania |
| wojewodztwo | WojewodztwoEnum | False | {} | Województwo |
| zrodloHalasu | string | False | {"maxLength":300} | Źródło hałasu |
| planowaneKosztaWAglomeracjiDlaLotnisk | number | False | {} | Planowane koszty w aglomeracji dla lotnisk |
| planowaneKosztaWAglomeracjiDlaLiniiKolejowych | number | False | {} | Planowane koszty w aglomeracji dla linii kolejowych |
| planowaneKosztaWAglomeracjiDlaDrog | number | False | {} | Planowane koszty w aglomeracji dla dróg |
| planowaneKosztaWAglomeracjiDlaPrzemyslu | number | False | {} | Planowane koszty w aglomeracji dla przemysłu |
| planowaneKosztaDlaDrog | number | False | {} | Planowane koszty dla dróg |
| planowaneKosztaDlaKolei | number | False | {} | Planowane koszty dla kolei |
| planowaneKosztaDlaLotnisk | number | False | {} | Planowane koszty dla lotnisk |

### `HalasKosztyDzialanWProgramachOchronySrodowiskaOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasKosztyDzialanWProgramachOchronySrodowiskaRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasDopuszczalnePoziomyHalasuRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| wskaznikHalasu | string | False | {"maxLength":80} | Wskaźnik hałasu |
| wartoscDopuszczalna | number | False | {} | Wartość dopuszczalna |
| rodzajTerenu | HalasRodzajTerenuEnum | False | {} | Rodzaj terenu |
| zrodloHalasu | string | False | {"maxLength":300} | Źródło hałasu |

### `HalasDopuszczalnePoziomyHalasuOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of HalasDopuszczalnePoziomyHalasuRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `HalasKategoriaHalasuEnum`



```json
{
  "type": "string",
  "enum": [
    "Droga",
    "Lotnisko",
    "Przemysł",
    "Kolej"
  ]
}
```

### `HalasRodzajTerenuEnum`



```json
{
  "type": "string",
  "enum": [
    "Strefa ochronna \"A\" uzdrowiska",
    "Tereny domów opieki społecznej",
    "Tereny mieszkaniowo-usługowe",
    "Tereny rekreacyjno-wypoczynkowe",
    "Tereny szpitali poza miastem",
    "Tereny szpitali w miastach",
    "Tereny w strefie śródmiejskiej miast powyżej 100 tys. mieszkańców",
    "Tereny zabudowy mieszkaniowej jednorodzinnej",
    "Tereny zabudowy mieszkaniowej wielorodzinnej i zamieszkania zbiorowego",
    "Tereny zabudowy zagrodowej",
    "Tereny zabudowy związanej ze stałym lub czasowym pobytem dzieci i młodzieży"
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
