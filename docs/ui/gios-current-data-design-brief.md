# Za Oknem — bieżące dane GIOŚ dla Design Leada

Misja: „Co dzieje się u Ciebie za oknem”. Brief opisuje kontrakty zaimplementowane
w PR #146/#147 i ich kontynuacji. Nie oznacza wdrożenia ani gotowego finalnego UI.
Zachować Start / Alerty / Ustawienia, bez nowej zakładki i mapy.

| Dane | API / pola | Interpretacja |
|---|---|---|
| Stężenia PM2.5, PM10, NO2, SO2, O3, CO, C6H6 | `/dashboard/latest` → `air.params`, `/air/latest?geo_area_id=` | µg/m³ również dla CO; każdy parametr ma własne observed_at/freshness; brak pola ≠ zero |
| Stacja i zasięg | station_id/name, distance_km, coverage, assignment_method | od wybranego miejsca, nie telefonu; exact ≤10 / nearby ≤50 / regional ≤100 km; regional nie jest lokalnym werdyktem |
| Indeks EEA liczony w aplikacji | air.index | obecny indeks; własna metodologia EEA, kompletność/missing/valid_until; nie nazywać go oficjalnym indeksem GIOŚ |
| Polski indeks dostawcy GIOŚ | `/air/provider-index?geo_area_id=` → scale, data.index, data.params, status | osobna skala; kod 0–5, źródłowa etykieta; czas danych observed_at osobno od calculated_at |
| Krótka historia | `/air/history?geo_area_id=&param=&hours=24\|48` | jedna stacja i parametr, points + gaps; brak interpolacji; pomiar, nie prognoza |

## Sposób użycia

Dashboard ma odpowiadać krótko na „co teraz”. Szczegóły Powietrza: dostępne stężenia,
ich aktualność, historia i stacja. Wybór stacji preferuje pomiary ≤6 h; przy braku
bieżących zostają stare, jawnie oznaczone. Nie przenosić daty najnowszego parametru
na wszystkie pozostałe. Nie scalać wartości z różnych stacji.

Nie projektować dwóch konkurencyjnych głównych ocen EEA/GIOŚ bez jawnych nazw skal.
Indeks GIOŚ można pokazać jako osobny źródłowy kontekst w szczegółach. Zachować etykietę
źródła; nie mapować polskiego „Dobry” do poziomu EEA. Indeks nie jest alertem.

## Stany wymagane w UI

- `available`: indeks ogólny użyteczny tylko gdy availability jest available; freshness
  może być STALE. Pokazać czas danych, nazwę skali i atrybucję.
- `no_index`: dostawca nie wyznacza użytecznego indeksu ogólnego (status false/null lub
  brak kategorii). Zachowane indeksy cząstkowe wymagają własnej daty i walidacji kategorii.
- `no_data`: nie pobrano poprawnego indeksu wybranej stacji; nie pokazywać dobrego wyniku.
- `no_station`: brak stacji z pomiarami w zasięgu. To nie „czyste powietrze”.
- `disabled`: funkcja niewłączona w backendzie — ukryć indeks GIOŚ, zachować stężenia/EEA.
- `retrieval_status=degraded`: poprzedni snapshot z jawnym błędem odświeżenia; fetched_at
  nie odmładza observed_at. Same stężenia mogą nadal działać.
- Historia: available/no_station/no_data + loading/error. Puste godziny ≠ zero.
  Dokładne wartości i jednostki dostępne dla TalkBack/VoiceOver. Przy zmianie czasu
  podpis godzin zawiera offset, żeby dwa odczyty 02:00 były rozróżnialne.

Stan błędu odświeżenia, duża czcionka, długa nazwa stacji i jasny/ciemny motyw są częścią
projektu. Statusy muszą mieć słowo/symbol, nie sam kolor. Min. obszar dotyku 48 dp.

## Poza tym projektem UI

Historyczny hałas, PRTR, ZZR/ZDR, stare awarie, oceny roczne, plany wód i NEC są on hold.
Nie tworzyć dla nich kafelków, makiet danych, alertów ani rekomendacji aktywności.
Agregaty PM10 i aktywne przekroczenia nie mają jeszcze implementacji/gate; nie obiecywać
ich w aktualnym mockupie. Pogoda, pyłki, UV i IMGW zachowują własne źródła/kontrakty.

Po zatwierdzeniu projektu: implementacja finalnego UI, build i testy na urządzeniu.
