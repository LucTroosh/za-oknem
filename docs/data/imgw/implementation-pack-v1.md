# Za Oknem — IMGW Implementation Pack v1

Data: 03.10.2026. Odbiorca: Claude, backend/mobile developers, reviewer.
Status: specyfikacja implementacji, nie potwierdzenie wdrożenia w repozytorium.

## 1. Decyzja produktowa i zakres

IMGW jest źródłem pierwszego wyboru dla pogody w Polsce. Open-Meteo uzupełnia brakujące parametry, horyzonty i awarie. Priorytet działa per parametr i przedział czasu, po weryfikacji semantyki, jakości, lokalizacji oraz prawa wykorzystania. Nie oznacza automatycznie większej dokładności każdego modelu IMGW.

Cel: jedna warstwa agregacji danych → własne API → Android, dashboard, alerty i „Co dziś robimy?”. Aplikacja nie wykonuje bezpośrednich zapytań do IMGW. Zachować istniejący onboarding, jedną lokalizację, brak mapy na start i nawigację Strona główna / Alerty / Ustawienia.

Nie zastępować pyłków i jakości powietrza danymi meteorologicznymi. Powietrze: oddzielna integracja GIOŚ/CAMS. Pyłki: Open-Meteo/CAMS. Hydrologia pozostaje oddzielnym modułem z wyłączoną publikacją do czasu wyjaśnienia warunków.

## 2. Źródła, dowody i ograniczenia weryfikacji

Oficjalne źródła:

1. API i regulamin: https://dane.imgw.pl/apiinfo
2. Katalog produktów: https://danepubliczne.imgw.pl/api/data/product
3. SYNOP: https://danepubliczne.imgw.pl/api/data/synop
4. METEO: https://danepubliczne.imgw.pl/api/data/meteo
5. Ostrzeżenia: https://danepubliczne.imgw.pl/api/data/warningsmeteo
6. UE: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R0138
7. Ponowne wykorzystanie: https://bip.imgw.pl/ponowne-wykorzystanie-danych/

W trakcie przygotowania odczytano odpowiedzi JSON SYNOP, METEO, warningsmeteo i katalog produktów. Szczegóły pobierania plików produktu nie zostały skutecznie zweryfikowane; nie deklarujemy sprawnego parsera GRIB/HDF5 ani kompletnego zakresu parametrów COSMO. Schemat niepustego ostrzeżenia wymaga fixture z rzeczywistej odpowiedzi. Nie analizowano kodu aktualnego repo — nazwy wewnętrznych endpointów i struktur poniżej są propozycją kontraktu.

Wszystkie progi odległości, TTL, retencji i jakości w tym dokumencie są decyzjami projektowymi do strojenia, nie wymaganiami IMGW ani gwarancją dokładności.

## 3. HVD i rejestr warunków

Rozporządzenie 2023/138 obejmuje meteorologiczne obserwacje, klimat, ostrzeżenia, radar i NWP. Warunki HVD dopuszczają otwarte ponowne wykorzystanie. Regulamin IMGW przewiduje korzystanie z HVD w każdym celu, z oznaczeniem źródła i przetworzenia. Sama publiczna dostępność endpointu nie rozstrzyga statusu wszystkich jego produktów. To kwalifikacja zakresu danych; nie przypisujemy automatycznie nazwy konkretnej licencji bez metadanych.

| Zbiór | Dowód | Decyzja implementacyjna |
|---|---|---|
| SYNOP — obserwacje meteorologiczne | oficjalne API; odpowiada kategorii HVD obserwacje | implementować; rejestrować podstawę kwalifikacji |
| METEO — obserwacje meteorologiczne | oficjalne API; odpowiada kategorii HVD obserwacje | implementować wyłącznie rozpoznane zmienne |
| warningsmeteo | oficjalne API; kategoria ostrzeżeń pogodowych | primary dla oficjalnych ostrzeżeń |
| COSMO_HVD_* | jawne HVD w aktualnym katalogu | implementować pobieranie i dekodowanie; primary po technicznej walidacji |
| radar COMPO_* | aktualny katalog, kategoria radaru HVD | przygotować adapter; powiązać produkt z metadanymi i warunkami przed aktywacją |
| radar HVD_* | wskazany w wcześniejszym researchu; brak w odczytanym katalogu API | nie hardkodować jako dostępnego; discovery w portalu |
| klimat/historyczne | kategoria HVD zwalidowanych obserwacji | późniejsza iteracja; kontrola statusu walidacji i zakresu |
| hydro, warningshydro | dostępne oficjalne endpointy | flaga publication=false do rozstrzygnięcia zakresu/warunków |
| PERUN, wewnętrzne tiles/API, grafiki | brak zweryfikowanego kontraktu dla projektu | poza zakresem |

Mail do IMGW został już wysłany według kontekstu użytkownika. Nie wysyłać ponownie. Nie mamy tutaj jego oryginalnej treści ani odpowiedzi. Po otrzymaniu odpowiedzi zaktualizować rejestr, bez przepisywania adapterów.

Rejestr dataset_registry: dataset_id, provider, official_url, hvd_basis, evidence_url, evidence_checked_at, terms_url, license_name (nullable), commercial_status [hvd_basis/confirmed/pending], publication_enabled, attribution, transformation_notice, review_notes. Zmiana commercial_status nie może nastąpić wyłącznie na podstawie odpowiedzi HTTP 200.

## 4. Macierz pierwszeństwa

| Parametr / zastosowanie | Pierwszy wybór | Uzupełnienie |
|---|---|---|
| temperatura / wilgotność teraz | reprezentatywna świeża obserwacja IMGW | model IMGW dla czasu teraz, następnie Open-Meteo |
| wiatr teraz | świeża obserwacja IMGW z poprawną statystyką | IMGW NWP → Open-Meteo |
| porywy | świeży rzeczywisty poryw IMGW | model porywów; nie podmieniać maks. prędkością bez zgodności |
| ciśnienie | IMGW z potwierdzonym poziomem odniesienia | równoważny parametr modelowy |
| opad teraz | poprawny radar IMGW dla punktu | reprezentatywny opad 10 min; potem model z etykietą |
| oficjalne ostrzeżenia | IMGW warningsmeteo | brak zastępczych „oficjalnych” alertów modelowych |
| prognoza | IMGW NWP w dostępnym zwalidowanym zakresie | Open-Meteo dla luk i dalszego horyzontu |
| UV, zachmurzenie, odczuwalna, słońce | IMGW wyłącznie przy równoważnym dostępnym produkcie | Open-Meteo / jawnie opisane wyliczenie |
| pyłki / AQ | oddzielna polityka źródeł | Open-Meteo/CAMS i GIOŚ |

Priorytet nie jest średnią źródeł. Nie mieszać obserwacji i prognozy w jednej wartości. Dopuszczalny dashboard z różnych źródeł wymaga provenance dla każdego pola.

## 5. API publiczne — kontrakt transportowy

Base URL: https://danepubliczne.imgw.pl/api/data/
GET, HTTPS. Odczytane endpointy działały bez tokena. Nie zidentyfikowano publicznej gwarancji limitów ani SLA. JSON jest formatem preferowanym.

| Ścieżka | Obsługa | Uwagi |
|---|---|---|
| synop | cały zbiór | jeden job krajowy |
| synop/id/12500 | pojedyncza stacja | oficjalnie udokumentowane |
| synop/station/jeleniagora | stacja po nazwie | oficjalnie udokumentowane; preferować stabilny ID |
| synop/format/xml, csv, html | alternatywne formaty | niepotrzebne do runtime |
| meteo/ | cały zbiór | nie zakładać filtrów SYNOP |
| warningsmeteo | aktualne ostrzeżenia | polymorphic response |
| warningshydro, hydro/ | hydrologia | oddzielny adapter, wyłączona publikacja |
| product | katalog id/url/opis | source of truth discovery |
| product/id/{id} | URL zwrócony przez katalog | format odpowiedzi i linki plikowe do zweryfikowania |

Bez wymyślonych query parameters, endpointów /latest lub szablonów nazw plików. Follow-up URL tylko z oficjalnego katalogu/portalu, z walidacją hosta i HTTPS. Nie pobierać całego portalu przez scraping.

## 6. SYNOP — mapowanie

Rzeczywisty odczyt pokazał tablicę obiektów; wartości liczbowe były stringami, ciśnienie bywało null. Poniżej nazwy pól zweryfikowane w odpowiedzi; jednostki/semantyka wymagają zapisania dowodu w słowniku przed publikacją.

| Pole źródłowe | Model docelowy | Interpretacja implementacyjna |
|---|---|---|
| id_stacji | station.provider_id | string, namespace synop |
| stacja | station.name | UTF-8 |
| data_pomiaru | observation date | YYYY-MM-DD |
| godzina_pomiaru | observation hour | string, zero-padding dopiero przy parsowaniu |
| temperatura | temperature_2m_c | °C, potwierdzić wysokość pomiaru |
| predkosc_wiatru | wind_speed_ms | konwencja m/s do udokumentowania |
| kierunek_wiatru | wind_direction_deg | kierunek pochodzenia; cisza bez wymuszonego kierunku |
| wilgotnosc_wzgledna | relative_humidity_pct | % |
| suma_opadu | precipitation_amount_mm | suma, nie natężenie; okres do potwierdzenia |
| cisnienie | pressure_hpa | nie nazywać sea_level bez potwierdzenia |

SYNOP nie dostarcza lat/lon w odczytanym payloadzie. Potrzebny wersjonowany katalog stacji z pochodzeniem współrzędnych; nie geokodować samego miasta i nie przedstawiać jego centrum jako położenia stacji. Nie utożsamiać id_stacji SYNOP i kod_stacji METEO. Tabela powiązań dopiero po weryfikacji identyfikatorów.

Nie wnioskować „pada teraz” z dodatniej suma_opadu bez znajomości okna pomiaru. Nie różnicować sum bez potwierdzenia resetów i okresu akumulacji.

## 7. METEO — dokładniejsze czasy per parametr

Zweryfikowane pola:

| Wartość | Timestamp | Docelowy parametr |
|---|---|---|
| temperatura_powietrza | temperatura_powietrza_data | air_temperature |
| temperatura_gruntu | temperatura_gruntu_data | ground_temperature; głębokość do potwierdzenia |
| wiatr_kierunek | wiatr_kierunek_data | wind_direction |
| wiatr_srednia_predkosc | wiatr_srednia_predkosc_data | mean_wind_speed; okno do potwierdzenia |
| wiatr_predkosc_maksymalna | wiatr_predkosc_maksymalna_data | maximum_wind_speed; osobno od porywu |
| wiatr_poryw_10min | wiatr_poryw_10min_data | gust_10min; semantyka do potwierdzenia |
| wilgotnosc_wzgledna | wilgotnosc_wzgledna_data | relative_humidity |
| opad_10min | opad_10min_data | precipitation_amount_10min |

Metadane: kod_stacji, nazwa_stacji, lon, lat, rok_zalozenia_stacji, wysokosc_npm. Wszystkie ID zachować jako string. Liczby konwertować kontrolowanym parserem; null/empty ≠ 0.

W rzeczywistym odczycie jedna stacja miała aktualny opad, a pozostałe pola null. Inna miała temperaturę z 08:10, wiatr z 08:30 i poryw datowany 23.09, mimo aktualnych innych pól. Dlatego freshness musi działać per parametr, nigdy per stacja ani fetched_at.

Temperatura gruntu nie jest temperaturą przy gruncie; bez udokumentowania głębokości nie używać jej do komunikatu o przymrozku przy powierzchni.

Czasy źródłowe nie zawierają offsetu. Przed aktywacją adaptera potwierdzić UTC/lokalny czas w oficjalnym opisie albo odpowiedzi IMGW. Nie wnioskować strefy z podobieństwa do aktualnej godziny. Konfiguracja source_timezone i fixture DST są obowiązkowe; nierozstrzygnięty czas → quarantine, fallback.

## 8. Ostrzeżenia i TERYT

Zweryfikowana odpowiedź bez ostrzeżeń: {"message":"Brak ostrzeżeń meteorologicznych"}. Parser ma rozpoznawać ten dokładny komunikat jako udany pusty snapshot. Inny obiekt message, HTML, błąd parsowania lub timeout ≠ brak ostrzeżeń.

Schema aktywnego ostrzeżenia musi powstać z prawdziwej fixture. Lista informacji do ekstrakcji, nie deklaracja zweryfikowanych nazw kluczy: identyfikator, wersja/aktualizacja, zjawisko, stopień, prawdopodobieństwo, start/end, treść, obszar/kody terytorialne, nadawca. Nie zgadywać kluczy w kodzie produkcyjnym. Brak fixture nie blokuje SYNOP/METEO.

Wewnętrzny Warning: provider_id, revision, phenomenon_raw, phenomenon_code, official_degree, probability_pct, valid_from, valid_to, issued_at?, area_codes[], text_original, source_url, fetched_at, match_status.

Lokalizacja musi mieć kod powiatu z wiarygodnego, wersjonowanego mapowania miejscowość → jednostka administracyjna. Zachować zera wiodące. Dopasowanie exact code, po potwierdzeniu poziomu kodów ostrzeżeń; nie startsWith ani substring. Miasta na prawach powiatu osobno. Bez mapowania: „Do sprawdzenia”, bez twierdzenia o lokalnym dopasowaniu. Uwzględnić ostrzeżenia przyszłe oraz aktualizacje i odwołania.

Udany pełny snapshot aktualizuje zestaw atomowo. Błąd zachowuje poprzedni snapshot i status degraded; nie zeruje ostrzeżeń. Po utracie świeżości: „Nie udało się sprawdzić aktualnych ostrzeżeń”. Nie wyświetlać „Brak zagrożeń”. Wygasłe ostrzeżenia nie są aktywne, ale mogą pozostać w historii.

UI zgodne z wcześniejszą decyzją: neutralne „Stopień X”, chip „Dotyczy Twojej lokalizacji” / „Do sprawdzenia”, neutralny hero szczegółu. Nie mapować mechanicznie stopnia 1/2/3 na nowe klasy danger/warning. Reguły aktywności mogą oddzielnie uwzględniać zjawisko, czas i dopasowanie.

## 9. COSMO HVD — prognoza primary

Zweryfikowane ID w katalogu: COSMO_HVD_00_00, COSMO_HVD_00_01, COSMO_HVD_06_00, COSMO_HVD_06_01, COSMO_HVD_12_00, COSMO_HVD_12_01, COSMO_HVD_18_00, COSMO_HVD_18_01. Opis: model COSMO 2k8 GRIB. To potwierdzenie obecności produktu, nie inwentaryzacja zawartości plików.

Nie zakładać, że końcówki 00/01 oznaczają lead time, ensemble lub dzień. Odczytać manifest i nagłówki GRIB.

Pipeline:

1. Katalog → URL produktu → rzeczywisty manifest/lista plików.
2. Pobranie do staging z limitami rozmiaru i timeout, weryfikacja formatu/checksum.
3. Inwentaryzacja ecCodes: edition, paramId/shortName, units, typeOfLevel, level, dataDate/dataTime, stepType, startStep/endStep, gridType, CRS i missing values.
4. Zbudowanie jawnego mappingu parametrów; nazwa shortName sama nie wystarcza.
5. Ekstrakcja pól wymaganych przez aplikację; temperatury K → °C dopiero z jednostek; ciśnienie Pa → hPa; wiatr u/v z właściwym poziomem i rotacją siatki.
6. Opad akumulowany → przyrost tylko w obrębie tego samego runu i poprawnego okna; reset runu nie daje ujemnego opadu. Nie sumować ponownie wartości akumulowanych.
7. Przeliczenie na punkty/komórki lokalizacji z jawnie zapisanym sposobem interpolacji. Kierunek wiatru wyliczać z wektora, nie średnią kątów.
8. Walidacja kompletności → atomowy promote. Nie publikować częściowo zapisanego runu jako kompletnego.

Nie obiecywać 48 h, kroków 1 h ani parametrów wyłącznie na podstawie wymagań UE. Dla każdego produktu zapisać rzeczywiste available_parameters, lead_times, run_time, domain, grid, levels, coverage. Dostępne zwalidowane parametry IMGW stają się primary; luki per parametr/time → Open-Meteo. Nie czekać z priorytetem na wynik wielomiesięcznego benchmarku, ale wymagane są testy jednostek, czasu, siatki i akumulacji.

Benchmark równoległy: zapisywać prognozę w momencie wydania, lead time 1/3/6/12/24/48 h, porównywać z obserwacją tej samej zmiennej/okna/poziomu. MAE/bias temperatury i wiatru; dla opadu także wykrycie/fałszywy alarm. Brak prognozy ≠ błąd 0. Raport zawiera liczebność i pokrycie. 30–60 dni to diagnostyka, nie dowód jakości w całym roku.

## 10. Radar — obserwacja, nie gotowy nowcast

Aktualny katalog zawiera m.in. COMPO_CAPPI.comp.cappi_h5, COMPO_SRI.comp.sri_h5, COMPO_CMAX_250.comp.cmax, COMPO_EHT.comp.eht oraz COMPO_CAPPI.comp.cappi_buf. Preferować produkt natężenia opadu po potwierdzeniu units/quantity. Reflectivity dBZ nie jest mm/h. CAPPI, CMAX, echotops nie są zamiennikami SRI.

Discovery musi połączyć konkretny produkt z HVD/warunkami. Nie dodawać prefiksu HVD do nazwy istniejącego produktu i nie opierać produkcji na wcześniej wspomnianej, dziś niewidocznej nazwie.

Parser HDF5/BUFR ma sprawdzać format, quantity, gain, offset, nodata, undetect, czas skanu, projekcję, rozmiar, orientację osi i granice. Nie zakładać ODIM bez sprawdzenia metadanych. nodata ≠ zero; undetect interpretować zgodnie z produktem. Punkt poza domeną → missing.

Pierwszy feature: radar_precipitation_rate z quality i scan_at, bez mapy. Radar pokazuje echo/opad szacowany, nie gwarantuje opadu przy ziemi. Zasłanianie wiązki, anomalie i odległość od radaru muszą obniżać pewność. Sama bliskość opadu nie pozwala powiedzieć „deszcz dotrze za 20 min”. Nowcast wymaga osobnego algorytmu ruchu z kilku klatek, testów i kalibracji.

## 11. Model danych i API własne

Proponowana struktura każdej wartości:

```json
{
  "parameter": "air_temperature",
  "value": 14.6,
  "unit": "degC",
  "provider": "IMGW",
  "dataset": "meteo",
  "source_type": "observation",
  "observed_at": "<ISO8601 z potwierdzonym offsetem>",
  "valid_at": null,
  "run_at": null,
  "fetched_at": "<ISO8601 UTC>",
  "interval_start": null,
  "interval_end": null,
  "station_id": "meteo:351230497",
  "station_name": "WŁODAWA",
  "distance_km": null,
  "elevation_difference_m": null,
  "quality": "fresh",
  "selection_reason": "imgw_fresh_representative",
  "fallback_reason": null,
  "transformed": true,
  "license_registry_id": "imgw-meteo"
}
```

Przykład ilustruje model; placeholder czasu nie jest poprawną fixture ani rekordem produkcyjnym. Value null wymaga statusu missing i przyczyny. Enum source_type: observation/radar_estimate/forecast/derived. Quality: fresh/stale/suspect/missing. Provider jako pole per parametr, nie wyłącznie w nagłówku dashboardu.

Proponowane tabele: stations, station_aliases, raw_snapshots, observations, forecast_runs, forecast_values, radar_frames, warnings, dataset_registry, ingestion_runs. Klucze: observation(dataset, station, parameter, observed_at), forecast(run, parameter, level, cell, valid_at), radar(product, scan_at), warning(provider_id, revision). Surowe odpowiedzi z checksum i parser_version umożliwiają replay.

Proponowane API własne, dopasować do istniejącego kontraktu:

- GET /v1/environment?location_id=... — selected values, forecast, sourceHealth, generated_at.
- GET /v1/alerts?location_id=... — active/upcoming, matching, last_successful_check, status.
- GET /v1/sources — źródła, warunki, atrybucje.

Nie zmieniać publicznego kontraktu Android bez migracji DTO i testu kompatybilności. Wspólny snapshot/selection_version dla dashboardu i reguł rekomendacji.

## 12. Resolver źródeł

```text
resolve(parameter, location, target_time, interval):
  candidates = equivalent_semantics_only(parameter, target_time, interval)
  candidates = allowed_for_publication(candidates)
  candidates = valid_units_and_timestamp(candidates)
  candidates = fresh_and_spatially_representative(candidates)
  if location.country == PL:
    prefer IMGW candidates within the proper source_type
  else:
    prefer the configured global provider
  select deterministically; retain reason and alternatives
  if no candidate: missing, never fabricate zero
```

Nie podstawiać dzisiejszej obserwacji do jutrzejszej prognozy. Radar preferowany dla opadu teraz; model dla przyszłości. Brak IMGW nie powinien blokować dostępnego Open-Meteo.

Domyślne kryteria startowe (konfigurowalne): temperatura/wilgotność ≤25 km i różnica wysokości ≤150 m; wiatr ≤15 km i ≤100 m; opad stacyjny ≤5 km jako obserwacja ze stacji, nie pewność w punkcie. Przy nieznanej wysokości ograniczyć zaufanie; w górach wybrać model, jeśli reprezentatywności nie da się potwierdzić. SYNOP bez poprawnych współrzędnych nie może wejść do selekcji odległościowej. Histereza wyboru: zmiana stacji dopiero gdy lepsza kandydatura utrzyma się dwa cykle albo dotychczasowa odpada jakościowo.

Nie stosować automatycznej korekty temperatury standardowym gradientem bez walidacji. Wszystkie progi mają reason codes i możliwość zmiany konfiguracji.

## 13. Ingestion, świeżość i awarie

| Job | Polling startowy | Próg fresh | Zachowanie po progu |
|---|---:|---:|---|
| SYNOP | 10 min | 90 min od obserwacji | fallback; pomiar tylko jako historyczny |
| METEO | 10 min | 30 min per parametr | fallback per pole |
| warnings | 5 min | 15 min od udanego pełnego snapshotu | status degraded, zachować znane aktywne |
| radar | 5 min | 15 min od skanu | bez pewnego rain_now |
| katalog produktów | 6 h | 24 h | ostatni poprawny katalog + alarm techniczny |
| NWP discovery | 30 min | run age ≤12 h i wymagany valid_at dostępny | fallback brakujących kroków |
| klimat | 24 h / według publikacji | zbiór historyczny | nie traktować jako current |

METEO: dla temperatury starszej niż 30 min można później dopuścić inne okno po analizie kadencji; obecnie wybrać fallback. Progi nie zastępują obserwacji faktycznej częstotliwości publikacji.

Jeden scheduler krajowy; distributed lock i zakaz nakładania jobów. Pobieranie nie zależy od liczby użytkowników. HTTP timeout startowo 15 s dla JSON, osobny limit dla plików; retry max 3 z exponential backoff+jitter; honorować Retry-After; po powtarzanych błędach circuit breaker. ETag/Last-Modified jeśli serwer obsługuje. Zapytania discovery nie pobierają ponownie identycznych plików.

Warstwy: raw → validate/quarantine → normalize → atomowy snapshot → resolver → API. Rekordy pojedynczo błędne mogą trafić do quarantine, ale odpowiedź z masową utratą pól nie zastępuje zdrowego snapshotu. Rozpoznany pusty snapshot ostrzeżeń jest odmiennym przypadkiem.

Cache API 60–120 s, invalidacja po promote; cache nigdy nie odświeża observed_at/run_at. Offline Android: ostatni snapshot z datą i etykietą; brak nowej rekomendacji na podstawie nieaktualnych danych bezpieczeństwa.

Retencja startowa: raw JSON 7 dni, obserwacje/wybrane punkty prognoz 90 dni, surowe duże runy NWP 48 h, radar 2 h. Osobne zamrożone fixtures. Limity dysku, sprzątanie i metryki bytes/day. Nie przechowywać całej siatki i wszystkich klatek bez celu i budżetu.

## 14. „Co dziś robimy?” i UX

Reguły korzystają z wybranych wartości i provenance, nie wykonują niezależnej selekcji źródeł. Ostrzeżenie dopasowane do lokalizacji i czasu planowanej aktywności ma pierwszeństwo przed pozytywną prognozą. Rozróżnić aktualne i nadchodzące ostrzeżenia.

Przykłady treści wymagające spełnienia reguł:

- „IMGW ostrzega przed silnym wiatrem. Dziś wybierz aktywność pod dachem.”
- „Radar wskazuje opad w okolicy. Wybierz krótszy spacer lub poczekaj na poprawę.”
- „Nie udało się sprawdzić aktualnych ostrzeżeń. Przed wyjściem sprawdź komunikaty IMGW.”

Nie mówić „bezpiecznie”, „brak zagrożeń” lub „idealne warunki”, gdy freshness/matching jest unknown. Missing pollen/AQ nie oznacza niskiego ryzyka. Uwzględnić poranek/południe/wieczór, czas trwania aktywności i alternatywy indoor według istniejącego rulebooka; nie przepisywać go bez porównania.

Dashboard: wartość i prosta etykieta „Pomiar IMGW • 10:30”; szczegóły: stacja, odległość i czas. Model: „Prognoza IMGW” lub „Prognoza Open-Meteo”. Pomiar odległej stacji opisany jako pomiar ze stacji, bez deklaracji dokładnie pod domem. Przy mieszanych źródłach szczegóły per parametr. Źródła danych w ustawieniach, bez dodawania technicznych wyborów dostawcy do onboarding.

## 15. Atrybucja

W Settings → Źródła danych umieścić wymagane brzmienie IMGW:

„Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy”.

„Dane Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu Badawczego zostały przetworzone”.

Dodać link do źródła i warunków oraz informację o aktualizacji. W eksporcie/udostępnionej karcie zachować atrybucję; nie tylko w ukrytych ustawieniach. Pełne brzmienie powyżej stanowi tekst do wdrożenia zgodnie z regulaminem, nie marketing.

## 16. Plan pracy i kryteria odbioru

| Task | Zakres | Definition of Done |
|---|---|---|
| IMGW-01 P0 | audit repo, istniejące adaptery, DTO, cache, rulebook | mapa plików, luki, brak dublowania integracji |
| IMGW-02 P0 | discovery + evidence fixtures | prawdziwe payloady, metadane jednostek/stref, lista pending |
| IMGW-03 P0 | rejestr datasets i flagi | jawna kwalifikacja; hydro disabled; atrybucja |
| IMGW-04 P0 | SYNOP + METEO ingestion | null, numery, per-field time, quarantine, dedup |
| IMGW-05 P0 | katalog stacji i geografia | współrzędne z pochodzeniem; poprawne namespaces |
| IMGW-06 P0 | resolver IMGW-first | testy świeżości, odległości, semantyki i fallback |
| IMGW-07 P0 | warnings | realna aktywna fixture; pusty response; matching TERYT; awaria ≠ zero |
| IMGW-08 P0 | Android + insights | provenance; neutralny stopień; zgodny rulebook |
| IMGW-09 P1 | COSMO discovery/inventory | realny manifest, GRIB inventory, parametry/horyzont/siatka |
| IMGW-10 P1 | NWP decode/promote | poprawne jednostki/czas/akumulacje; IMGW primary dla dostępnych pól |
| IMGW-11 P1 | radar | warunki powiązane z produktem, poprawny CRS/nodata/gain; brak fałszywego nowcast |
| IMGW-12 P1 | observability/benchmark | raport coverage+error, metryki jobów, alertowanie |
| IMGW-13 P2 | klimat/hydro | dopiero po konkretnym zakresie i warunkach |

Flagi: imgw_observations_enabled, imgw_warnings_enabled, imgw_nwp_enabled, imgw_radar_enabled, imgw_hydro_publication_enabled=false. Flags określają aktywację adaptera; dataset_registry osobno ogranicza publikację. Wdrażać małymi PR: obserwacje/resolver, warnings/UX, NWP, radar. Rollback adaptera przywraca Open-Meteo dla równoważnych parametrów; warnings zachowują jawny unknown.

## 17. Testy i monitoring

Wymagane testy behawioralne:

1. String „0” → zero; null/empty → missing, również opad i wiatr.
2. Aktualny fetched_at + stary poryw → poryw odrzucony, temperatura nadal dozwolona.
3. SYNOP bez współrzędnych → nie wybrany jako najbliższy.
4. UTC/local/DST po potwierdzeniu source timezone; przyszła obserwacja poza tolerancją 5 min → suspect.
5. Jednostki m/s versus km/h, K versus °C, Pa versus hPa.
6. Ciśnienie stacyjne nie zastępuje sea-level; maksymalny wiatr nie zastępuje gust.
7. Opad akumulowany resetującego się runu → brak ujemnego deszczu.
8. GRIB level/CRS/orientacja → znane punkty kontrolne, bez przesunięcia siatki.
9. Radar nodata → unknown; dBZ nie zostaje mm/h.
10. warnings „Brak…” → success empty; HTTP error/nieznany message → degraded.
11. TERYT z zerami, miasto powiatowe, missing mapping, przyszłe/odwołane ostrzeżenie.
12. Brak parametru IMGW → tylko ten parametr przechodzi do Open-Meteo.
13. Częściowy run → brak promote; czytelnik dostaje poprzedni spójny snapshot.
14. Rekomendacja indoor przy właściwym ostrzeżeniu; unknown nie daje „bez zagrożeń”.

Metryki: job_last_success, request_errors, parsing_errors, quarantine_count, snapshot_age, observation_age per parametr, forecast_run_age, radar_scan_age, coverage, fallback_share(reason), ingestion_bytes, disk_usage, warning_check_status. Alarm operacyjny dla braku warnings success >15 min i powtarzanych schema errors. Dashboard użytkownika nie pokazuje logów infrastruktury.

## 18. Prompt startowy dla Claude

> Przeczytaj cały Za_Oknem_IMGW_Implementation_Pack_v1.md i aktualną dokumentację repo. Wdrożenie ma preferować IMGW w Polsce dla każdego równoważnego, świeżego i reprezentatywnego parametru; Open-Meteo wypełnia luki i awarie. Nie usuwaj Open-Meteo. Najpierw sprawdź istniejące integracje i rulebook „Co dziś robimy?”, następnie wykonaj IMGW-01 do IMGW-08 w małych PR. Weryfikuj jednostki, strefę czasu, współrzędne stacji i aktywny schemat ostrzeżeń na oficjalnych danych; nie zgaduj nazw pól. Jeśli detal blokuje jeden adapter, udokumentuj go i kontynuuj pozostałe. Zachowaj surowe fixtures i evidence URLs. Priorytet IMGW dla prognozy uruchom po poprawnym dekodowaniu i walidacji konkretnych produktów COSMO_HVD, w ich rzeczywistym zakresie; benchmark prowadź równolegle. Radar aktywuj po powiązaniu produktu z warunkami i walidacji parsera. Hydro publication pozostaje false. Zachowaj neutralne „Stopień X”, matching TERYT i jawny unknown przy awarii ostrzeżeń. Nie wprowadzaj mapy ani nowego onboardingu. Każdy PR ma zawierać zakres zmian, testy, decyzje, pending items i instrukcję rollback. Nie deklaruj zakończonego zadania bez kodu, testów i sprawdzenia odpowiedzi własnego API.

## 19. Lista nierozstrzygnięta — do zamknięcia podczas implementacji

- Oficjalna semantyka jednostek, wysokości/okien pomiarowych i strefy czasu API.
- Źródło aktualnych współrzędnych/wysokości SYNOP i zweryfikowane crosswalk stacji.
- Niepusta fixture ostrzeżeń i poziom kodów terytorialnych.
- Odpowiedź endpointów produktu, manifesty i pobranie rzeczywistych GRIB/HDF5.
- Faktyczny zakres parametrów, poziomów i prognozy COSMO, znaczenie końcówek ID.
- Powiązanie konkretnych radarów COMPO z metadanymi HVD i warunkami.
- Odpowiedź na już wysłany mail IMGW dotycząca hydrologii i innych niejednoznacznych produktów.

Te punkty nie cofają decyzji IMGW-first. Określają, kiedy konkretny parametr jest gotowy do rzetelnej publikacji.
