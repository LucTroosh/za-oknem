# WODY-PODZIEMNE API — katalog development

Źródło: https://dane.gios.gov.pl/apispec/openapi-wody-podziemne.yaml. Pobrano 2026-10-03. SHA-256: `e2a52bda75999238b971b0699d6f16e2fc0a8cb6d51cd9d44c1550adb150e69c`.

OpenAPI: 3.1.1; wersja: 1.0.0.

Base URL: https://dane.gios.gov.pl/api/wody-podziemne

Licencja deklarowana: {"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"}. Brak deklaracji licencji w tym pliku nie oznacza braku warunków.

To katalog deklarowanego kontraktu, nie potwierdzenie działania wszystkich operacji. Runtime różnice: 06-verification.md. Cykle, jednostki i reprezentatywność: 01/02/03.

## Operacje

### GET `/v1/programy-monitoringu`

Programy monitoringu jednolitych części wód podziemnych

Usługa sieciowa udostępniająca część opisową programu monitoringu jednolitych części wód podziemnych

operationId: `getProgramyMonitoringuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rokOd | query | True | integer | {"minimum":2022,"maximum":9999} | Rok programu od (dane dostępne od 2022 roku co 6 lat) |
| rokDo | query | True | integer | {"minimum":2022,"maximum":9999} | Rok programu do |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `ProgramyMonitoringuOdpowiedz`

### GET `/v1/plik/{id}`

Pobieranie dokumentu w postaci pliku PDF lub JSON

Usługa sieciowa pozwalająca na pobranie dokumentu. Identyfikator dokumentu należy pobrać wywołując jedną z poniższych usług podając parametry zapytania zgodnie z dokumentacją: <br> - Programy monitoringu jednolitych części wód podziemnych (/v1/programy-monitoringu)<br> - Pobieranie opisu metodyki i wyników oceny stanu jednolitych części wód podziemnych (/v1/metodyki-oceny-stanu)

operationId: `getDokumentV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| id | path | True | unspecified / int64 | {"minimum":1,"maximum":9223372036854775807} | Id dokumentu |
| format | query | True | FormatPlikuEnum | {"enum":["PDF","JSON"]} | Format pliku |

Odpowiedzi:

- HTTP 200: Sukces; application/json → `unspecified`, application/pdf → `string / binary`

### GET `/v1/punkty-pomiarowe-monitoringu`

Pobieranie zestawienia danych o sieci pomiarowej monitoringu jednolitych części wód podziemnych

Usługa sieciowa udostępniająca zestawienie danych o punktach pomiarowych krajowej sieci pomiarowej

operationId: `getPunktyPomiaroweMonitoringuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rokOd | query | True | integer | {"minimum":2022,"maximum":9999} | Rok programu od (dane dostępne od 2022 roku co 6 lat) |
| rokDo | query | True | integer | {"minimum":2022,"maximum":9999} | Rok programu do |
| dorzeczeNazwa | query | False | string | {"maxLength":50} | Nazwa dorzecza (np. Wisła) (wymagane, jeśli brak jcwpdNumer lub jcwpdKod) |
| jcwpdNumer | query | False | integer | {"minimum":0,"maximum":999999999} | Numer JCWPd (wymagane, jeśli brak dorzeczeNazwa lub jcwpdKod). Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |
| jcwpdKod | query | False | string | {"maxLength":20} | Kod JCWPd (wymagane, jeśli brak dorzeczeNazwa lub jcwpdNumer). Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |

Odpowiedzi:

- HTTP 200: Lista punktów pomiarowych monitoringu; application/json → `PunktyPomiaroweOdpowiedz`

### GET `/v1/metodyki-oceny-stanu`

Pobieranie opisu metodyki i wyników oceny stanu jednolitych części wód podziemnych

Usługa sieciowa udostępniająca opis metodyki i wyniki oceny stanu jednolitych części wód podziemnych

operationId: `getMetodykiOcenyStanuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rok | query | True | integer | {"minimum":2020,"maximum":9999} | Rok, którego dotyczy ocena stanu (dane dostępne od 2022) lub rok opracowania metodyki (dane dostępne od 2020) |

Odpowiedzi:

- HTTP 200: Metadane plików opisujących metodyki i wyniki oceny stanu jednolitych wód podziemnych; application/json → `MetodykaOcenyOdpowiedz`

### GET `/v1/wyniki-oceny-stanu`

Pobieranie podsumowania wyników oceny stanu jednolitych części wód podziemnych

Usługa sieciowa udostępniająca podsumowanie wyników oceny stanu jednolitych części wód podziemnych

operationId: `getWynikiOcenyStanuV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rok | query | True | integer | {"minimum":2022,"maximum":9999} | Rok opracowania (dane dostępne od 2022 roku) |
| dorzeczeNazwa | query | True | string | {"maxLength":50} | Nazwa dorzecza (np. Wisła) |
| jcwpdNumer | query | False | integer | {"minimum":0,"maximum":999999999} | Numer JCWPd. Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |
| jcwpdKod | query | False | string | {"maxLength":20} | Kod JCWPd. Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |

Odpowiedzi:

- HTTP 200: Wyniki oceny stanu; application/json → `WynikiOcenyOdpowiedz`

### GET `/v1/wyniki-analizy-trendow`

Pobieranie wyników analizy trendów jednolitych części wód podziemnych

Usługa sieciowa udostępniająca wyniki analizy trendów zmian stężeń wskaźników fizyczno-chemicznych w punktach pomiarowych monitoringu stanu chemicznego JCWPD

operationId: `getWynikiAnalizyTrendowV1`

Parametry (wymagalność wg spec, dodatkowe wymagania runtime opisano osobno):

| Nazwa | Gdzie | Wymagany | Typ | Ograniczenia / wartości | Opis |
|---|---|---|---|---|---|
| numerStrony | query | False | integer | {"minimum":0,"maximum":99999,"default":0} | Parametr mechanizmu stronicowania określający, którą stronę wyników chce pobrać użytkownik. Numer indeksu żądanej strony (liczony od zera). Domyślna wartość → 0 |
| liczbaElementowNaStronie | query | False | integer | {"minimum":1,"maximum":50,"default":10} | Parametr mechanizmu stronicowania określający ilość oczekiwanych rekordów w odpowiedzi na stronie. Jest to dodatnia liczba całkowita podawana z kluczem parametru. Domyślna wartość → 10, Maksymalna wartość → 50 |
| rok | query | True | integer | {"minimum":2022,"maximum":9999} | Rok opracowania (dane dostępne od 2022 roku) |
| monitoringId | query | False | integer | {"minimum":0,"maximum":999999999} | ID monitoringu. Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |
| punktPomiarowyNumer | query | False | integer | {"minimum":0,"maximum":999999999} | Numer punktu pomiarowego. Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |
| punktPomiarowyKod | query | False | string | {"maxLength":20} | Identyfikator UE punktu pomiarowego. Wartości są dostępne na stronie internetowej monitoringu jakości wód podziemnych pod adresem: [https://mjwp.gios.gov.pl/](https://mjwp.gios.gov.pl/) |
| trendyZmianStezen | query | True | TrendyZmianStezenEnum | {"enum":["Bez prognozy","Z prognozą"]} | Trendy zmian stężeń wskaźników fizyczno-chemicznych |

Odpowiedzi:

- HTTP 200: Wyniki analizy trendów; application/json → `WynikiAnalizyTrendowOdpowiedz`

## Pełny słownik schematów

### `ProgramyMonitoringRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| plikId | integer | False | {} |  |
| plikNazwa | string | False | {"maxLength":255} |  |
| dokumentTytul | string | False | {"maxLength":255} |  |
| dataPowstania | string / date | False | {} |  |
| rokOd | integer | False | {} |  |
| rokDo | integer | False | {} |  |

### `PunktyPomiaroweRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rokOd | integer | False | {} |  |
| rokDo | integer | False | {} |  |
| dorzeczeNazwa | string | False | {"maxLength":255} |  |
| jcwpdNumer | integer | False | {} |  |
| jcwpdKod | string | False | {"maxLength":255} |  |
| jcwpdOcenaRyzyka | string | False | {"maxLength":255} |  |
| punktPomiarowyNumer | integer | False | {} |  |
| punktPomiarowyKod | string | False | {"maxLength":255} |  |
| polozenieAdministracyjne | string | False | {"maxLength":255} |  |
| punktPomiarowyWspolrzedne | string | False | {"maxLength":255} |  |
| punktPomiarowyCharakter | string | False | {"maxLength":255} |  |
| punktPomiarowyRodzaj | string | False | {"maxLength":255} |  |
| stratygrafia | string | False | {} |  |
| kompleksWodonosny | integer | False | {} |  |
| punktPomiarowyFunkcja | object | False | {} |  |
| punktPomiarowyFunkcja.monitoringChemDiag | boolean | False | {} |  |
| punktPomiarowyFunkcja.monitoringChemOper | boolean | False | {} |  |
| punktPomiarowyFunkcja.monitoringIlosciowy | boolean | False | {} |  |
| punktPomiarowyFunkcja.monitoringBadawczy | boolean | False | {} |  |
| punktPomiarowyFunkcja.monitoringWplywJcwpsElzpdz | boolean | False | {} |  |
| punktPomiarowyFunkcja.monitoringWplywJcwpsSpozycie | boolean | False | {} |  |

### `MetodykaOcenyRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| plikId | integer | False | {} |  |
| plikNazwa | string | False | {"maxLength":255} |  |
| dokumentTytul | string | False | {"maxLength":255} |  |
| dataPowstania | string / date | False | {} |  |
| rok | integer | False | {} |  |

### `WynikiOcenyRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rok | integer | False | {} |  |
| jcwpdNumer | integer | False | {} |  |
| jcwpdKod | string | False | {"maxLength":255} |  |
| dorzeczeNazwa | string | False | {"maxLength":255} |  |
| jcwpdKompleksyLiczba | integer | False | {} |  |
| jcwpdRyzykoOcena | string | False | {"maxLength":255} |  |
| jcwpdStanChemOcena | string | False | {"maxLength":255} |  |
| jcwpdStanIloscOcena | string | False | {"maxLength":255} |  |
| jcwpdStanOgolnyOcena | string | False | {"maxLength":255} |  |

### `WynikiAnalizyTrendowRekord`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| rok | integer | False | {} |  |
| monitoringId | integer | False | {} |  |
| punktPomiarowyNumer | integer | False | {} |  |
| punktPomiarowyKod | string | False | {"maxLength":255} |  |
| trendyZmianStezen | TrendyZmianStezenEnum | False | {} |  |
| jcwpdNumer | string | False | {"maxLength":255} |  |
| jcwpdKod | string | False | {"maxLength":255} |  |
| badaniaRok | integer | False | {} |  |
| analizaTrenduWyniki | object | False | {} |  |
| analizaTrenduWyniki.pewTeren | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.as | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.sb | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.nh4 | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.no3 | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.no2 | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.ba | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.be | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.b | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.cl | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.zn | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.f | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.al | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.cd | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.co | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.mg | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.cu | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.mo | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.ni | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.pb | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.k | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.se | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.so4 | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.na | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.tl | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.ti | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.u | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.v | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.ca | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.toc | string | False | {"maxLength":255} |  |
| analizaTrenduWyniki.hco3 | string | False | {"maxLength":255} |  |

### `ProgramyMonitoringuOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of ProgramyMonitoringRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `PunktyPomiaroweOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of PunktyPomiaroweRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `MetodykaOcenyOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of MetodykaOcenyRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `WynikiOcenyOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of WynikiOcenyRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

### `WynikiAnalizyTrendowOdpowiedz`



| Pole | Typ / referencja | Required | Ograniczenia / enum | Opis |
|---|---|---|---|---|
| dane | object | False | {} |  |
| dane.strona | array of WynikiAnalizyTrendowRekord | False | {} |  |
| dane.liczbaRekordow | integer | False | {} |  |
| wynik | WynikTyp | False | {} |  |

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

### `TrendyZmianStezenEnum`



```json
{
  "type": "string",
  "enum": [
    "Bez prognozy",
    "Z prognozą"
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
