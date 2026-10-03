# Design Lead — GIOŚ + IMGW, bieżące dane w Za Oknem

## Zadanie

Zaprojektuj aktualizację istniejącego UI zgodnie z misją „Co dzieje się u Ciebie za oknem”.
Przygotuj dashboard, szczegóły Powietrza/Pogody, Alerty i stany brakujących danych.
Zachowaj dolną nawigację **Start / Alerty / Ustawienia**, jedną lokalizację i brak mapy.
„Co dziś robimy?” pozostaje wysoko na Start, z krótkim wyjaśnieniem „Co to oznacza?”.
Nowe dane rozwijają cztery główne tematy; nie zamieniaj każdego parametru w osobny kafelek.

## Gotowość danych

| Dane | Rzeczywisty stan |
|---|---|
| GIOŚ: 7 parametrów, aktualna stacja, historia24/48h | kod na main (#146–148); nie każdy parametr jest dostępny na każdej stacji; QA urządzenia czeka |
| Oficjalny indeks GIOŚ | kod na main, domyślnie off do migracji/rolloutu; osobny od EAQI |
| IMGW: METEO, selekcja temp/wilgotności, ostrzeżenia powiatowe | pierwszy etap implementacji pod flagami; timezone/semantyka/approval/rollout oczekują |
| Prognozy IMGW/COSMO, radar | plan i discovery; brak gotowego dekodera/produkcyjnych danych |
| Rzeki/hydro | istniejący backend, publikacja wyłączona zgodnie z researchem do wyjaśnienia warunków |
| Hałas, jakość wody, PRTR/okresowe oceny | on hold albo zablokowane; nie projektować jako pomiary „teraz” |

Projektuj warianty dla aktywacji danych, ale wdrożenie nie pokazuje stałych placeholderów
funkcji wyłączonych. Makiety z danymi testowymi muszą być podpisane jako scenariusze.

## Start i Welcome

Cztery tematy: Pogoda, Powietrze, Pyłki, Ostrzeżenia. Najpierw wartość dla użytkownika,
krótka interpretacja i godzina; pełne źródło/stacja/odległość w szczegółach.
Nie dodawaj wyboru dostawcy, kodów TERYT, flag ani innych ustawień technicznych.
Welcome może eksponować: „Pogoda, powietrze, pyłki i ostrzeżenia w Twojej okolicy”.
Nie obiecuj pomiaru dokładnie pod domem ani większej dokładności IMGW bez danych.
Zachowaj kierunek istniejących mockupów i oba motywy; źródła są w aplikacji, bez obowiązkowej
listy operatorów w dolnej części Welcome.

## Powietrze — GIOŚ

Jedna karta podsumowania, szczegóły z PM2.5, PM10, NO2, O3, SO2, CO, benzenem (C6H6).
Pokazuj tylko dostępne pomiary z jednostką z API. Brak wartości ≠ zero.
Najbliższa stacja z bieżącymi danymi ma pierwszeństwo; stare pomiary mają widoczną datę.
Wyświetl nazwę stacji, odległość i czas każdego parametru. Zasięg: ≤10km exact,
10–50km nearby, 50–100km regional; dane regionalne nie są lokalnym pomiarem pod domem
ani podstawą pozytywnej rekomendacji „Na dwór”.

Historia24/48h: zmiana parametru w jednym widoku; oś czasu, jednostka, wartości, jawne luki,
zero widoczne jako zero, lista pomiarów dla dostępności. Nie rysuj ciągłości przez brak danych.
Podczas zmiany czasu dwie lokalne godziny02:00 są różnymi odczytami; szczegóły muszą je odróżnić.
Nie obiecuj kompletnego okna, jeśli źródło go nie dostarczyło.

EAQI jest Europejskim Indeksem Jakości Powietrza. Oficjalny indeks GIOŚ jest osobnym wskaźnikiem:
nie łącz kategorii, legend ani skali. Zachowaj nazwę kategorii operatora. Jego indeksy cząstkowe
obejmują SO2/NO2/PM10/PM2.5/O3; CO i benzen mają pomiary, ale nie takie indeksy.
Wyłączony indeks nie tworzy pustej karty. `no_index` nie znaczy „dobrze”, a awaria może
pozostawić ostatni indeks z oznaczeniem nieaktualności.

## Pogoda — IMGW + model

Nowy kontrakt: `/api/v1/weather/selected?geo_area_id=...`, także optional
`dashboard.areas[].selected_weather`. Każda wartość ma provider/type/time/unit/station/distance
oraz reason selekcji. Dotychczasowy blok Pogody i obecne reguły nadal korzystają z Open-Meteo;
przełączenie UI/insights ma używać wspólnego nowego bloku, po zamknięciu bramek.

Priorytet startowy obejmuje świeżą, reprezentatywną temperaturę/wilgotność IMGW;
pozostałe pola mają model fallback. Nie zakładaj jednego operatora dla całej karty.
Pomiar: „Pomiar IMGW • 21:10”, szczegóły: nazwa stacji, odległość, czas pomiaru.
Model: „Prognoza Open-Meteo”/„Dane modelowe”; osobno horyzont przyszły.
Nie używaj czasu pobrania jako czasu pomiaru. Starszy poryw nie może wyglądać świeżo dlatego,
że temperatura odświeżyła się przed chwilą.

METEO zawiera osobne obserwacje: temperaturę powietrza/gruntu, wilgotność, kierunek,
średnią/maksymalną prędkość wiatru, poryw10min i opad10min. Nie nazywaj max prędkości porywem,
„opad10min” natężeniem ani temperatury gruntu temperaturą przy gruncie.
SYNOP bez zweryfikowanych współrzędnych nie jest wybierany jako najbliższa stacja.
Nie dodawaj radaru, prognozy IMGW ani komunikatu „deszcz za20min” do wdrażanego zakresu.

## Ostrzeżenia

IMGW meteo: oryginalne zjawisko, neutralny „Stopień X”, prawdopodobieństwo, treść,
czas od/do i biuro. Rozróżnij nadchodzące i obowiązujące według czasu początku.
Dopasowanie `county` oznacza powiat, `voivodeship` województwo, `unresolved` „Do sprawdzenia”.
Bez zweryfikowanego powiatu nie twierdź, że ostrzeżenie dotyczy lokalizacji.
Nie pokazuj kodów TERYT jako UX dla użytkownika. Nie zgaduj nazw administracyjnych.

Powiatowy match może dać chip „Dotyczy Twojej lokalizacji” i w szczegółach „Dotyczy Twojego powiatu”.
Nie mapuj automatycznie stopni1/2/3 na nowe klasy danger/warning. Zachowaj neutralny hero szczegółu.
Meteo musi być sprawdzone w ciągu15min, a błąd po ostatnim sukcesie unieważnia potwierdzenie
pustej listy. Brak aktualnej weryfikacji: „Nie udało się sprawdzić aktualnych ostrzeżeń”.
Nie używaj „Brak zagrożeń”. Wyłączona hydrologia nie tworzy karty z rzekomą awarią źródła.

## Co dziś robimy? / Co to oznacza?

Użyj obecnego rulebooka. Projektuj krótkie wyjaśnienie odnoszące się do dostępnych wartości
oraz ograniczeń. Nie dodawaj nowego wyliczonego scoringu, deklaracji „bezpiecznie” ani
rekomendacji bazujących na niedostępnych danych. Dopasowane ostrzeżenie w czasie aktywności
ma pierwszeństwo przed pozytywną pogodą. Implementacja nowego źródła reguł jest kolejnym etapem;
makieta nie dowodzi, że logika została przełączona.

## Oddanie projektu

Makiety: Start, Powietrze z historią i dwoma odrębnymi indeksami, Pogoda z mieszanymi źródłami,
Alerty i szczegół. Dla każdego: dane świeże/stare/brak/awaria; dodatkowo nieznana lokalność,
niekompletna historia i ostrzeżenie nadchodzące. Jasny/ciemny, font130/200%, kontrast,
TalkBack, hit-area≥48dp, status słowem/glifem, nie wyłącznie kolorem.

Dostarcz mapowanie element UI→pole API, teksty, zasady ukrywania danych wyłączonych i scenariusze
przejść stanów. Po zatwierdzeniu: implementacja UI, wspólna selekcja dla insights, build i QA urządzenia.

## Aktualizacja 2026-10-03 — rzeki i hałas w zakresie produktu

Decyzja właściciela: dodajemy oba tematy. Obecny kod zapewnia bazę i osobne wejścia ze Start;
Design Lead może zaprojektować ich karty obok istniejących tematów, bez zmiany Start/Alerty/Ustawienia.

**Rzeki w okolicy:** stacje wodowskazowe IMGW w promieniu 50 km od lokalizacji. Pokazać nazwę stacji
(z rzeką), odległość, poziom cm, czas pomiaru, aktualność oraz dostępne progi ostrzegawczy/alarmowy.
W grupach najpierw stany alarmowe/ostrzegawcze, wewnątrz grup bliższe stacje. Brak progów = brak oceny;
nie zastępować go zielonym „bezpiecznie”. Odległość nie oznacza, że stacja leży w tej samej zlewni ani
że mierzy ryzyko pod adresem użytkownika. Stan cm jest względem lokalnego zera wodowskazu, nie
„głębokością rzeki”. Brak punktu w promieniu to osobny stan; awaria i stare dane zachowują poprzednie
odczyty z ostrzeżeniem. Nieprojektowane w tym etapie: prognoza powodzi, mapa, trend bez danych historii.

**Hałas w okolicy:** ostatnie opublikowane pomiary GIOŚ z wybranych punktów do 10 km, osobno
Droga/Kolej/Przemysł/Lotnisko. Każdy wynik musi mieć okres pomiaru, porę dnia/nocy podaną przez źródło,
dB i odległość. Wyróżnik na karcie: „Pomiary historyczne”, a nie aktualność importu. Pokazać przekroczenie
wyłącznie jako informację źródła, bez własnych progów i ocen „cicho/głośno teraz”. Brak punktu nie oznacza
ciszy. Nie używamy mikrofonu telefonu. Dostępne kategorie zależą od rzeczywistych pomiarów.

Oba tematy mają niezależne stany ładowania/awarii. Publiczne karty pojawiają się po aktywacji źródeł;
prototypy mogą wykorzystać zweryfikowane fixtures, oznaczone jako przykładowe. Hydro wymaga jeszcze
potwierdzenia czasu/warunków; hałas sprawdzenia operatora i aktualnego importu. Nie ogłaszać funkcji
„live” przed aktywacją i QA. Nie wpływają obecnie na Co dziś robimy / ocenę Outdoor.
