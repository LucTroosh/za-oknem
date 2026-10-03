# Licencje i rejestr źródeł

## Potwierdzone

Każdy z siedmiu pobranych plików OpenAPI 1.0.0 ma `info.license.name: CC BY 4.0` i https://creativecommons.org/licenses/by/4.0/ . CC BY 4.0 dopuszcza komercyjne wykorzystanie, kopiowanie i opracowanie z uznaniem autorstwa, linkiem do licencji i oznaczeniem zmian. Oficjalna strona GIOŚ o ponownym wykorzystaniu obejmuje informacje w aplikacjach przedsiębiorców i wymaga czytelnego `Źródło danych: GIOŚ` lub pełnej nazwy urzędu.

Zapisanie specyfikacji, cache i normalizacja oraz reklamowy/premium produkt są zgodne z zakresem CC BY dla tych zbiorów. Nie oznacza to zatwierdzenia całej aplikacji do monetyzacji: inne źródła zachowują swoje odrębne ograniczenia (zwłaszcza Open-Meteo i IMGW). Nie włączać reklam/premium przy tej zmianie.

Atrybucja w każdym szczególe sekcji oraz w Ustawienia → Źródła danych:

> Źródło danych: GIOŚ · CC BY 4.0. Dane zostały uporządkowane i przetworzone przez Za Oknem. Okres danych: {period}. Pobrano: {fetched_at}.

Linki: strona źródła, licencja; etykieta „przetworzone” opisuje normalizację/łączenie. Nie sugerować poparcia GIOŚ dla produktu. Nie wykorzystywać logo, zdjęć lub map bazowych na podstawie licencji danych. Grafiki/audiowizualne gov.pl mogą mieć inne zasady.

Bieżące JPOAT: oficjalny opis API wymaga akceptacji regulaminu portalu, podania źródła i uprzedza o nieweryfikowanych na bieżąco danych. Nie przypisywać mu licencji nowego `powietrze` tylko z podobnej nazwy. Zachować istniejący zatwierdzony wpis i sprawdzić aktualny regulamin przy rozszerzeniu.

Opłaty: oficjalna strona GIOŚ dopuszcza opłatę za dodatkową pracę przy indywidualnym wniosku lub dostosowaniu stałego bezpośredniego dostępu. Nie jest to wykaz cen publicznego API. Brak podanego limitu/SLA nowych API nie oznacza nielimitowanej usługi ani gwarancji uptime.

## Wpisy do source-registry.md

W implementation PR dodać osobne wpisy, NIE przestawiać wszystkich na PRODUCTION w PR dokumentacyjnym.

| source_id | endpoint bazowy | licencja | commercial_use | evidence/status |
|---|---|---|---|---|
| gios_air_assessments | https://dane.gios.gov.pl/api/powietrze | CC BY 4.0 w OpenAPI | yes, attribution+license+changes | VERIFIED spec, LIVE_PARTIAL |
| gios_noise | https://dane.gios.gov.pl/api/halas | CC BY 4.0 w OpenAPI | yes, warunki jak wyżej | VERIFIED spec, LIVE_PARTIAL, geometry pending |
| gios_surface_water_programs | https://dane.gios.gov.pl/api/wody-powierzchniowe | CC BY 4.0 w OpenAPI | yes, warunki jak wyżej | VERIFIED spec, pusty wynik i błąd live; nie wyniki jakości |
| gios_groundwater | https://dane.gios.gov.pl/api/wody-podziemne | CC BY 4.0 w OpenAPI | yes, warunki jak wyżej | VERIFIED spec, LIVE_PARTIAL, CRS pending |
| gios_prtr | https://dane.gios.gov.pl/api/prtr | CC BY 4.0 w OpenAPI | yes, warunki jak wyżej | VERIFIED spec, LIVE_PARTIAL, units/geo pending |
| gios_major_accidents | https://dane.gios.gov.pl/api/powazne-awarie | CC BY 4.0 w OpenAPI | yes, warunki jak wyżej | VERIFIED spec, LIVE_PARTIAL, historical only |
| gios_nec | https://dane.gios.gov.pl/api/nec | CC BY 4.0 w OpenAPI | yes, warunki jak wyżej | VERIFIED spec, LIVE_PARTIAL |

Każdy wpis: owner=GIOŚ, source URL i checksum, last_verified_at=2026-10-03, publication_frequency=UNKNOWN dopóki nie sprawdzona, rate_limit=UNKNOWN, polling=disabled/manual discovery, caching=backend snapshots, coverage=per query/dataset, attribution powyżej, approval zależny od wyników gate. Licencja VERIFIED nie jest dowodem gotowości technicznej.

## Gate przed włączeniem danej operacji

1. Pobieralny oficjalny kontrakt i licencja konkretnego zbioru.
2. Co najmniej niepusty wynik, pusty wynik/błąd, wszystkie używane parametry, paginacja i jednostki przetestowane i zapisane.
3. Wszelkie różnice spec/live obsługiwane jawnie, bez domysłów.
4. Zweryfikowany cykl publikacji/częstotliwość lub uzasadniony wyjątek zgodny z ADR-004; limity zapisane jako fakt albo UNKNOWN z własnym limiterem.
5. Geo i okres danych mają jasną interpretację; UI nie przedstawia ich jako aktualnego zagrożenia.
6. Kwarantanna, timeout/retry, izolacja, testy, atrybucja i feature flag działają.

Brak spełnienia blokuje tylko daną operację/sekcję, nie całą dokumentację i nie istniejące powietrze. Pisemne pytanie do GIOŚ jest przydatne dla niejasnych jednostek, CRS, paginacji, cyklu i dodatkowych datasetów; nie udawać, że wysłano wiadomość.

## Gotowa treść pytań technicznych do GIOŚ

Prosimy o potwierdzenie: (1) jednostek lacznaIlosc i masaOdpadow w PRTR, (2) semantyki liczbaRekordow, sortowania i sposobu pobrania kompletnego zbioru, (3) CRS współrzędnych punktów wód podziemnych i geometrii hałasu, (4) cyklu aktualizacji i limitów publicznych API, (5) strefy czasowej wynik.data bez offsetu, (6) źródła geometrii zakładów PRTR/ZZR/ZDR, (7) interfejsu wyników jakości wód powierzchniowych i warunków jego użycia. Architektura: publiczne API → okresowy backend cache/normalizacja → aplikacja wielu użytkowników; planowane przyszłe reklamy/premium, atrybucja i link CC BY 4.0. Wyjaśnić także niespójności pól ze specyfikacją opisane w raporcie weryfikacji.
