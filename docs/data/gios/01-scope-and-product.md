# Zakres danych i sposób pokazania ich w aplikacji

## Macierz integracji

| Obszar | Interfejs / zakres potwierdzony w kontrakcie | Lokalizacja | Użycie w Za Oknem | Kolejność |
|---|---|---|---|---|
| Bieżące powietrze | JPOAT `/pjp-api/v1/rest`: stacje, stanowiska, pomiary, indeks, archiwum, metadane, statystyki i pozostałe operacje z katalogu | stacje i metadane | rozbudowa istniejącej karty powietrza i reguł aktywności | P1 |
| Powietrze historyczne | nowe `powietrze`: oceny roczne/wieloletnie, skład chemiczny PM2.5, chemizm opadów, raporty, metody | strefa/stacja/stanowisko według operacji | profil regionu i historia; nie bieżący AQI | P2/P3 |
| Hałas | pomiary, zasięgi GeoJSON, ekspozycja ludności, działania, środki ochrony, koszty, poziomy dopuszczalne, jednostki odpowiedzialne | punkty WGS84; geometria zasięgów do sprawdzenia | historyczny pomiar w pobliżu; ekspozycja miejsca tylko z prawidłowym polygonem | P2 |
| Wody powierzchniowe | wyłącznie plan monitoringu JCWP/PPK od 2022 r. | nazwy i kody, bez geometrii w rekordzie | informacja o zakresie monitoringu; jakość wody zablokowana do pozyskania wyników | P2 discovery |
| Wody podziemne | programy, punkty, dokumenty, ocena stanu chemicznego/ilościowego/ogólnego, trendy | kod JCWPd, punkty z niepotwierdzonym CRS | kontekst regionalny po poprawnym powiązaniu przestrzennym | P3 |
| PRTR | uwolnienia do powietrza/wody/gleby, transfer do ścieków i transfery odpadów | województwo/powiat/miejscowość, REGON | zakłady raportujące w miejscowości i roczne dane, bez oceny zagrożenia | P2 |
| Poważne awarie | historyczne zdarzenia oraz zakłady ZZR/ZDR | adres i administracja, bez współrzędnych | rejestr informacyjny; nie alarmy operacyjne | P2/P3 |
| NEC | stanowiska, wskaźniki i wyniki wpływu zanieczyszczeń na ekosystemy | współrzędne stanowisk, kod JCWP | regionalny monitoring, bez ogólnego „zielonego wyniku” | P3 |

### Powietrze bieżące — parametry

Podstawowe automatyczne zanieczyszczenia: PM2.5, PM10, NO2, SO2, O3, CO, C6H6. Dostępność zależy od stanowiska, nie każda stacja mierzy wszystko. Użyć metadanych stanowisk zamiast stałej listy oczekiwanych pomiarów. Metale i benzo(a)piren z monitoringu manualnego/ocen rocznych nie są danymi godzinowymi. Manualne wyniki JPOAT są udostępniane w archiwum z opóźnieniem opisanym w dokumentacji (4–8 tygodni).

W repo istnieje connector `apps/api/app/connectors/gios/`, katalog stacji, scheduler godzinowy i geo matching do 50 km. Rozszerzać go; nie tworzyć drugiego konkurencyjnego ingestu tych samych danych. Weryfikować obsługę wielu zanieczyszczeń i indeksu względem aktualnego kodu, nie zakładać jej tylko z README.

### Powietrze historyczne

Nowe API ma osobne operacje ocen i stężeń, PM2.5 (metadane/metody, pomiary, statystyki), chemizmu opadów (metadane, pomiary, agregaty, średnie roczne), słowniki stanowisk i raporty PDF/JSON. Jednostka jest polem rekordu tam, gdzie podaje ją API. Zakres chemicznych wskaźników pobierać z danych/metadanych; nie wymyślać listy jonów. Klasy ocen odnoszą się do strefy, roku, wskaźnika i celu ochrony. Nie tłumaczyć automatycznie klasy rocznej na dzisiejszą jakość powietrza.

### Hałas

Rzeczywista próbka: wynik 64.5 dB dla pory „Dzień 16h”, przedziału pomiarów z 2024 r., punktu w Żyglinie. To NIE „hałas teraz”. Zachować porę, daty od/do, kategorię i rodzaj wskaźnika. Nie zamieniać wartości z `pora` w LDWN/LN, jeśli źródło tego nie stwierdza. Nie uśredniać arytmetycznie decybeli. `przekroczenie=0` dotyczy tego pomiaru, nie certyfikuje całej miejscowości.

Zasięgi są deklarowane jako GeoJSON, ale schemat geometrii ma przykład Point i płaską tablicę coordinates. Nie generować fikcyjnych polygonów; dopiero próbka rzeczywistego zasięgu i CRS pozwoli na przypisanie ekspozycji do wybranego punktu. Agregaty populacji nie są wartością hałasu dla domu użytkownika.

### Woda

Rozdzielić: jakość środowiskową GIOŚ, hydrologię IMGW (poziom/przepływ), kąpieliska GIS i wodę pitną Sanepid. Jedna kategoria UI „Woda” może prowadzić do tych różnych informacji, ale każda ma osobne źródło, datę i semantykę. GIOŚ nie zastępuje decyzji o dopuszczeniu kąpieliska ani oceny wody z kranu.

Wody powierzchniowe: `jcwpKod`, `jcwpNazwa`, `ppkKod`, `ppkNazwa`, `wojewodztwo`, `wskaznik`, `rok` opisują plan. Brak wartości pomiaru, daty pobrania próbki, pH, klasy jakości i współrzędnych. Pobranie wyników z innego portalu/pliku jest osobnym zadaniem discovery z własnym gate.

Wody podziemne: oceny JCWPd obejmują stan chemiczny, ilościowy, ogólny i ryzyko; trendy mają wskaźniki m.in. NO3, NO2, NH4, As, Cd, Pb, Cl, SO4 i TOC (pełne pola w katalogu). To etykiety wyników analizy trendu, nie bieżące stężenia. Punkt reprezentuje określony poziom wodonośny, nie dowolną pobliską studnię.

### PRTR i PA

`typUwolnienia` rozróżnia Powietrze/Woda/Gleba/Ścieki. Ilości i masy są w schemacie opisane niejednoznacznie, bez jednostki: nie zakładać kg/t bez źródła metodycznego. Zachować liczbę jako wartość surową i oznaczyć `unit_unknown`, dopóki jednostka nie zostanie zweryfikowana. Nie sumować różnych substancji w „łączną szkodliwość”. REGON firmy nie zawsze identyfikuje pojedynczy zakład: firma może mieć kilka instalacji; nie deduplikować tylko po REGON.

ZZR = zakład o zwiększonym ryzyku, ZDR = zakład o dużym ryzyku wystąpienia poważnej awarii przemysłowej. To kategoria regulacyjna, nie aktywny incydent. Rejestr zdarzeń nie potwierdza trwającego zagrożenia. Brak rekordów nie oznacza „brak ryzyka”.

### NEC

Wyniki zawierają rok raportowania i osobno rok/miesiąc/dzień pomiaru, wskaźnik, jednostkę oraz wartość tekstową. Zachować granice oznaczalności i kwalifikatory. Typ ekosystemu MAES/EUNIS, status obszaru i region biogeograficzny są kontekstem badania, nie oceną zdrowotną mieszkańca. Nie rozciągać jednego stanowiska na całą okolicę.

## Pozostałe obszary GIOŚ — objęte dokumentacją discovery

Nie istnieje tu potwierdzony komplet REST dla poniższych obszarów. Claude ma udokumentować dostęp, nie pisać connectorów do wymyślonych adresów.

| Obszar | Dane / droga dostępu | Warunek przed implementacją | Niedopuszczalny wniosek |
|---|---|---|---|
| Gleby orne | oficjalny XLSX 1995–2025 i raport 2025; pH, próchnica, skład, nutrienty, WWA, metale; sieć 216 punktów, cykl 5 lat | pobrać plik, jednostki, kody punktów, współrzędne i CRS, warunki konkretnego pliku | jakość gleby na działce z odległego punktu |
| Promieniowanie jonizujące | raporty GIOŚ o skażeniach, m.in. wody/osady/gleba; brak potwierdzonego REST w siedmiu specyfikacjach | ustalić zbiór, datę, jednostki Bq vs dawka, zasięg i licencję | „brak anomalii teraz” z archiwalnego raportu |
| Pola elektromagnetyczne | monitoring PEM, oficjalny portal/raporty; oddzielny od promieniowania jonizującego | odnaleźć plik/usługę, częstotliwość, pasmo, V/m, punkt i okres | bieżąca ekspozycja domu na podstawie pojedynczego pomiaru |
| Przyroda i bioróżnorodność | monitoring gatunków, siedlisk, ptaków, lasów; portale tematyczne i INSPIRE | warunki, schemat, zakres przestrzenny, daty i ochrona dokładnych lokalizacji wrażliwych gatunków | brak rekordu = brak gatunku |
| Morze | monitoring środowiska morskiego, raporty/usługi przestrzenne do odnalezienia | zbiór parametrów, geometria, głębokość próbki, okres i jednostki | decyzja kąpieliskowa na podstawie oceny morza |
| Pokrycie terenu | Corine Land Cover wskazane w katalogu GIOŚ | właściwy właściciel/licencja (także Copernicus), rocznik, rozdzielczość i dokładność | bieżąca ilość zieleni przy domu |
| Zintegrowany monitoring środowiska | portale i raporty sieci, różne parametry | katalog danych i właścicieli, interfejs, reprezentatywność | uniwersalny „Green Index” bez metodologii |
| INSPIRE | droga dostępu do danych przestrzennych, nie osobna metryka | metadane zbioru, prawdziwy GetCapabilities, WMS/WFS/download, wersja, CRS i limity | obraz WMS = dostępny plik wektorowy |

Punkty startowe: https://www.gov.pl/web/gios/monitoring-jakosci-gleby-i-ziemi ; https://www.gov.pl/web/gios/monitoring-promieniowania-jonizujacego-oraz-jego-wyniki ; https://www.gov.pl/web/gios/monitoring-przyrody ; katalog https://www.gov.pl/web/gios/monitoring-i-ocena-stanu-srodowiska . Dokładne usługowe adresy pozostałych obszarów pozostają UNKNOWN, dopóki discovery ich nie potwierdzi.

## UX — nowy moduł „Twoja okolica”

Wejście: drugorzędna karta/wiersz na Start → ekran Twoja okolica. Zachować trzy obecne zakładki Start/Alerty/Ustawienia. Bez mapy, konta i dodatkowego uprawnienia lokalizacji. Zmiany scope Master Planu opisać ADR przed kodem.

Kolejność sekcji: Hałas → Zakłady raportujące emisje → Rejestr przemysłowy → Monitoring wód → Monitoring ekosystemów. Sekcje włączane osobno flagami po gate. Nie wyświetlać pustej makiety jako danych i nie zasypywać dashboardu kilkunastoma kafelkami.

| Stan / karta | Gotowa treść | Dodatkowe informacje |
|---|---|---|
| Hałas, historyczny pomiar | „Pomiary hałasu w pobliżu” / „Ostatni dostępny pomiar: {value} dB” | „{place}, {distance} km · {period} · {source_type}”; odległość tylko od prawdziwego punktu |
| Zasięg potwierdzony polygonem | „Hałas według mapy z {year}” / „{indicator}: {band} dB” | „Długookresowa ocena dla wybranego punktu. Nie jest pomiarem na żywo.” |
| PRTR | „Zakłady raportujące emisje” / „{count} w wybranej miejscowości” | „Rejestr PRTR · dane za {year}. Wpis nie oznacza naruszenia przepisów.” |
| ZZR/ZDR | „Rejestr zakładów przemysłowych” | „{name} · {classification}. Informacja z rejestru, nie aktywne ostrzeżenie.” |
| Plan wód powierzchniowych | „Monitoring pobliskich wód” / „{water_body} — plan badań na {year}” | „Zakres monitoringu: {indicator_list}. Nie jest to ocena przydatności do kąpieli.” |
| Ocena JCWPd | „Wody podziemne w regionie” / „Stan chemiczny: {source_label}” | kod, rok oceny i metodologia; tylko przy poprawnym geo match |
| Brak pokrycia | „Brak danych dla tej lokalizacji” | „Dostępne punkty nie pozwalają ocenić Twojej okolicy.” |
| Awaria | „Dane chwilowo niedostępne” | jeśli są wcześniejsze, pokazać je z datą i statusem nieaktualności |

Odległość do centrum miejscowości nie jest odległością do telefonu/domu użytkownika. Tekst ma brzmieć „od wybranej lokalizacji”. Punkty poza zakresem reprezentatywności można pokazać jako historyczne badania w regionie, nie lokalny wynik.

Nie stosować wspólnego score „bezpiecznie”, czerwonego alarmu za sam wpis PRTR/ZZR ani „brak istotnych alertów” z brakującego datasetu. Aktualne reguły „Co dziś robimy?” mogą korzystać z bieżącego powietrza; hałas historyczny, PRTR, plan monitoringu i NEC nie uruchamiają rekomendacji „zostań w domu” ani pushy.
