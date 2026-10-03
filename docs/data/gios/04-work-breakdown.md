# Work breakdown — GIOŚ / Twoja okolica

Status wszystkich nowych zadań: TODO, chyba że wskazano BLOCKED. To plan dla Claude, nie wykaz zrealizowanej implementacji. Pracować małymi PR-ami, aktualizować ROADMAP po merge. Nie merge'ować automatycznie ani deployować produkcji z samego promptu dokumentacyjnego.

## Wspólna definicja Done

Zakres zadania i acceptance criteria spełnione, testy zachowania (nie tylko struktury), lint/typecheck repo, aktualne kontrakty/schema, Source Registry i ADR, downgrade izolacji źródeł, atrybucja oraz instrukcja odtworzenia. Brak danych oznaczony jawnie. Zrzuty UI jasny/ciemny, duża czcionka, długie nazwy i stan offline dla zadań mobile. Nowe zależności tylko z uzasadnieniem.

## GIOS-00 — evidence i source gates

Goal: operacyjny rejestr prawdziwych możliwości. Scope: porównać kopie OpenAPI ze źródłem, sprawdzić regulaminy, dodać wpisy do Source Registry, wykonać kontrolowany discovery używanych operacji. Dependencies: niniejszy pakiet. Data contract: raw response+request+HTTP+czas+hash, bez danych wrażliwych. Security: allowlist hostów, brak sekretów. Architecture: brak zmiany produkcji.

Acceptance: dla każdej planowanej sekcji są używane operacje, próbki niepuste/puste/błędne, parametry wymagane, pagination, jednostki, CRS, okres, cycle i jasny VERIFIED/BLOCKED; brak niepotwierdzonego „approved”. Tests: HTTP200/BLAD, brak strona przy zero, zmienne typy, strony 0/1 i repeated page. Non-goals: ogólnokrajowy wielki ingest i deploy.

## GIOS-01 — ADR modułu i kontrakt

Goal: włączenie profilu okolicy bez psucia MVP. Scope: rozszerzenie Master Planu, ADR z kolejnym wolnym numerem, encje, API `/neighborhood`, availability vs freshness, flagi i UI wejście. Dependencies: GIOS-00. Data: kontrakt z rozdziału 02. Security: reuse place_id, bez nowego śledzenia. Architecture: addytywny moduł i migracje.

Acceptance: oceny/historyczne rejestry nie są Alert/Forecast, brak uniwersalnego score i mapy, istniejące endpointy kompatybilne; decyzja o zmianie scope jawna w ADR. Tests: walidacja kontraktu i regresja dashboardu. Non-goals: replatforming stacka.

## GIOS-02 — ingestion foundation

Goal: niezawodny wspólny mechanizm nowych API. Scope: limiter współdzielony, HTTP status+BLAD, paginacja, checkpoint, snapshot staging/promocja, raw provenance, kwarantanna, konfiguracja. Dependencies: 00/01. Data: envelopes spec/live. Security: bounded retries i rozmiar dokumentów. Architecture: reuse SourceFetch, minimalne nowe tabele Alembic.

Acceptance: przerwany batch nie zastępuje dobrego snapshotu i nie usuwa danych; repeated page kończy run błędem; drugi worker respektuje lock/limiter; wymuszony timeout nie psuje innych źródeł. Tests: retry/429, BLAD200, empty, duplicate, page loop, crash/resume, atomowe promowanie. Non-goals: generowanie klientów bez adapterów.

## GIOS-03 — rozszerzenie istniejącego powietrza

Goal: uzupełnić szczegóły o dostępne zanieczyszczenia i oficjalny indeks. Scope: audyt parser/client/ingest i UI, pełna paginacja sensors/data tam gdzie potrzebna, indeks, jednostki, timestamp/DST, provenance. Dependencies: gate JPOAT; foundation tylko jeśli reuse jest sensowny. Data: `api/air-live.md`. Architecture: istniejący gios, nie nowy connector. Security: limity i brak fetch per user.

Acceptance: nieobecny PM2.5 nie oznacza dobrej jakości; indeks dostawcy zachowuje etykietę/skalę i czas; CO przeliczany tylko jawnie µg→mg jeśli UI tego wymaga; stara stacja i null value nie stają się świeżymi. Tests: wielostronicowy sensor, partial pollutants, null, stary indeks, zmiana czasu Europe/Warsaw, odmienne daty parametrów. Non-goals: zmiana providera pyłków/pogody.

## GIOS-04 — hałas, pomiary historyczne

Goal: pierwsza nowa użyteczna sekcja. Scope: pomiary w obsługiwanych województwach/kategoriach/okresach, punkty, okres, wartość/przekroczenie, widok nearby measurement. Dependencies: 00–02, zatwierdzony okres aktualizacji. Data: `api/halas.md`. Security: bez bieżących alarmów. Architecture: noise measurements+PostGIS point, API read DB.

Acceptance: widoczna data/okres i pora, odległość od wybranego miejsca, nie „hałas teraz”; brak bliskich punktów nie generuje wyniku miejscowości. Tests: lon/lat odwrotne, measurement interval, null, dzień/noc, dwa punkty identycznej odległości, awaria jednej sekcji. Non-goals: scoring mieszkania, arytmetyczna średnia dB.

## GIOS-05 — hałas, geometria i mapowanie ekspozycji

Status: BLOCKED dla ekspozycji punktu do rzeczywistej walidacji geometrii/CRS. Scope: zasięgi, runda/źródło/wskaźnik/przedział, point-in-polygon, agregaty i działania tylko jako kontekst. Dependencies: 04 + poprawny niepusty GeoJSON. Architecture: noise_zone GIST. Security: nie wnioskować przekroczenia prawnego bez rodzaju terenu/wskaźnika.

Acceptance: Point lub brak polygonów blokuje przypisanie, overlap rozstrzygany per runda i źródło, krawędź deterministyczna, wynik przypisany do punktu miejscowości z opisem ograniczenia. Tests: invalid geometry, CRS, polygon hole, boundary, overlapping bands, różne rundy. Non-goals: nowa mapa w UI.

## GIOS-06 — PRTR, lokalny rejestr i roczne emisje

Goal: lista zakładów raportujących w miejscowości/obszarze administracyjnym. Scope: uwolnienia i transfery, deduplikacja instalacji, rok, medium, substancja, źródło. Dependencies: 00–02; units gate dla liczb. Data: `api/prtr.md`. Architecture: facility/release/transfer. Security: brak medycznego/risk score.

Acceptance: lokalizacja opisuje administrację, nie promień km; bez jednostki liczby nie mają fałszywego kg/t; zero raportów to „brak rekordów w zbiorze za rok”, nie „zero emisji”; firma z dwoma zakładami nie zlewa się po REGON. Tests: mixed numeric/string amounts, duplicate company, różne media, brak unit, korekta raportu, casing województwa. Non-goals: płatne geokodowanie i mapa, rankingi toksyczności.

## GIOS-07 — zakłady ZZR/ZDR i historia zdarzeń

Goal: spokojna informacja z rejestrów. Scope: zakłady i historyczne awarie w odrębnych modelach, adresy, daty, klasyfikacja, source links. Dependencies: 00–02. Data: `api/powazne-awarie.md`. Security: sanitize linki HTTPS/HTTP, bez push. Architecture: facility classification + industrial_event.

Acceptance: ZZR/ZDR nie tworzy Alert; historyczna awaria ma datę i nie jest „aktywna”; brak coords usuwa distance; kod NACE zachowany bez domyślnego dopełnienia zer. Tests: event bez zakładu, null address, ten sam REGON wiele instalacji, string/numeric NACE, zły URL. Non-goals: operacyjny system bezpieczeństwa.

## GIOS-08 — wody powierzchniowe, program + discovery wyników

Goal: nie pomylić planu badań z jakością. Scope: programy JCWP/PPK, odnalezienie oficjalnego zbioru wyników i geometrii, własny gate dla nich. Dependencies: 00–02. Data: `api/wody-powierzchniowe.md`. Architecture: monitoring_program, nie Measurement. Security: bez decyzji kąpieliskowej.

Acceptance: przetestowane dokładne jcwpNazwa i rok; niepusty rekord wymagany do mappera; plan opisany jako plan; wyniki/geo mają osobne zweryfikowane URL i warunki albo status BLOCKED. Tests: brak nazwy=BLAD200, nieznana nazwa=empty, duplicate JCWP nazwy, rok string w odpowiedzi. Non-goals: zgadywanie pH i klasy wody. Stan karty jakości: BLOCKED do pozyskania wyników.

## GIOS-09 — wody podziemne

Goal: poprawnie zinterpretowana ocena JCWPd. Scope: programy, punkty, metodyki/oceny/trendy, dokumenty. Dependencies: 00–02 oraz potwierdzony CRS/polygony dla geo. Data: `api/wody-podziemne.md`. Architecture: program/site/assessment, kod jednostki i okres. Security: nie „woda pitna bezpieczna”.

Acceptance: runtime wymagany dorzeczeNazwa/jcwpdKod/jcwpdNumer uwzględniony; TAK/NIE jawnie parsowane, projected x/y nie przyjmowane jako WGS84; klasa chemiczna nie staje się pomiarem; unknown CRS blokuje lokalny match. Tests: object coords vs string, mixed bool, stan ilościowy vs chemiczny, plik błędny MIME, ocena bez polygonu. Non-goals: ocena prywatnej studni.

## GIOS-10 — historyczne powietrze

Goal: kontekst regionu i historia. Scope: 16 operacji nowych ocen/PM2.5/chemizmu/raportów wg priorytetu, rozdzielić operacje w gate i małych PR. Dependencies: 00–02. Data: `api/powietrze.md`. Architecture: assessment/observation/document. Security: jednostka rekordu i quality flag.

Acceptance: rok/cel ochrony/strefa zachowane, PM2.5 skład chemiczny nie mylony z bieżącym całkowitym PM2.5, metadane i pomiary łączone po właściwym namespace ID, dokumenty z ograniczeniem rozmiaru. Tests: brak jednostki, ocena roślin vs ludzi, korekta danych, PDF/JSON, zamknięte stanowisko. Non-goals: zastąpienie hourly JPOAT.

## GIOS-11 — NEC

Goal: udokumentowany regionalny monitoring ekosystemów. Scope: stanowiska/wskaźniki/wyniki i dates/qualifiers. Dependencies: 00–02. Data: `api/nec.md`. Architecture: monitoring_site i observation z ekosystemem.

Acceptance: string/number ID i współrzędne obsłużone, rok raportu różny od pomiaru, null parametry nie psuje strony; brak automatycznego „środowisko dobre”. Tests: text below-limit, null units, częściowa data, różne ekosystemy i sparse coverage. Non-goals: agregat Green Index.

## GIOS-12 — pozostałe obszary discovery

Goal: przygotować kolejne wiarygodne źródła. Scope: gleby, PEM, promieniowanie, przyroda, morze, pokrycie terenu, monitoring zintegrowany i INSPIRE z macierzy rozdziału 01. Dependencies: brak dla researchu; implementation po gate. Data: rzeczywisty plik/WFS schema. Security: wrażliwe lokalizacje gatunków, licencje właścicieli.

Acceptance per obszar: właściciel, URL, format, konkretny rekord i pola/jednostki, CRS i okres, licencja, cycle, ograniczenia, task implementacji albo jawny BLOCKED. Tests: walidacja pliku/rejestru; brak connectora bez próbki. Non-goals: twierdzenie, że brak REST oznacza brak danych.

## GIOS-13 — API/mobile, integracja i release

Goal: end-to-end Twoja okolica z zaliczonymi źródłami. Scope: DB-only endpoint, UI sekcje, źródła, accessibility, feature flags, observability/runbook. Dependencies: 01/02 + przynajmniej 04; kolejne sekcje niezależnie. Data: kontrakt repo i update API-contract. Architecture: addytywna nawigacja.

Acceptance: stany available/no_records/no_coverage/unavailable różne; świeże pobranie nie ukrywa rocznika; awaria PRTR nie psuje powietrza ani hałasu; wszystkie liczby mają jednostkę albo nie są publikowane jako pomiar; brak nowej zakładki i mapy; źródła dostępne z karty. Tests: E2E place→DB→API→UI, offline, duża czcionka, jasny/ciemny, timeout jednego providera, flag rollback. Non-goals: auto-deploy, reklamy, push z historii.

## Plan PR

PR-A: GIOS-00/01 (evidence, Registry, ADR, kontrakt). PR-B: 02 (foundation). PR-C: 03 (air hardening). PR-D: 04+minimalny 13 (pierwszy vertical slice). PR-E: 06. PR-F: 07. PR-G: 08 discovery. Kolejne: 05/09/10/11/12 według zamkniętych blockerów. Pełne katalogi obejmują wszystkie API, produkcyjne wdrażanie jest etapowe.
