# ADR-003: Open-Meteo (darmowy, niekomercyjny tier) jako dostawca pogody w fazie social-impact

**Status:** Accepted — częściowo uzupełniony przez ADR-031 (pisemne potwierdzenie Open-Meteo, 2026-10-02): darowizny/Patronite dozwolone na Free; reklamy i płatne/premium funkcje nadal wymagają planu komercyjnego PRZED włączeniem
**Data:** 2026-09-28

## Context

Produkt startuje jako projekt "social impact": bezpłatna aplikacja, bez reklam, bez
subskrypcji. Open-Meteo (weather + CAMS air/pollen) oferuje darmowy tier wyłącznie do
użytku niekomercyjnego (CC BY 4.0, limity 600/min, 5000/h, 10000/dzień, 300000/miesiąc).
Wg ich Terms of Use: niekomercyjne = m.in. prywatne/non-profit aplikacje bez subskrypcji
i reklam; komercyjne = aplikacje z subskrypcją/reklamami lub integracja w produkcie
komercyjnym. Wsparcie przez Patronite (crowdfunding, cykliczne wpłaty) nie jest wprost
zaadresowane w ich Terms — to szara strefa interpretacyjna.

## Problem

Czy i na jakich warunkach można używać darmowego, niekomercyjnego tieru Open-Meteo dla
pogody i CAMS, biorąc pod uwagę, że użytkownik prowadzi JDG i docelowo rozważa
monetyzację (niekoniecznie Open-Meteo jako takie, ale ogólnie produkt)?

## Decision

- Dopóki aplikacja jest **bezpłatna, bez reklam, bez subskrypcji, bez Patronite ani innej
  formy stałego wsparcia finansowego** — korzystamy z darmowego tieru Open-Meteo.
- **Nie włączamy** Patronite ani żadnej monetyzacji, dopóki nie zostanie to jawnie
  zrewidowane w tym ADR (zmiana statusu na Superseded) — patrz Trigger niżej.
- Budżet wywołań: liczymy realnie (nasz słownik ~22 zmienne pogodowe → więcej niż
  1 "API call" na punkt wg zasad rozliczania Open-Meteo), pobieramy tylko aktywne
  gminy (ADR-001), monitorujemy dzienne zużycie, alert przy 70% z 10 000/dzień.
- Atrybucja Open-Meteo (CC BY 4.0) i Copernicus/CAMS musi być widoczna w aplikacji
  (ekran "Źródła") zgodnie z Source Registry (§37) i Source Approval Gate (§38).
- Pyłki i CAMS Air pobieramy bezpośrednio z Copernicus Atmosphere Data Store (ADS) —
  dane opisane przez Copernicus jako dostępne bez ograniczeń użycia, wymagana
  atrybucja programu Copernicus. Nie zależy to od statusu komercyjnego Open-Meteo.
  **Zaktualizowane przez ADR-020 (2026-10-01):** bez klucza ADS pyłki MVP idą przez
  Open-Meteo Air Quality API (ten sam model CAMS Europe), więc podlegają TEJ SAMEJ
  zasadzie niekomercyjnego tieru i triggerom rewizji poniżej. Bezpośredni ADS
  zostaje opcją po rewizji. Patrz ADR-020.

## Trigger do rewizji tego ADR

Rewidujemy **przed**, nie po, włączeniu jakiejkolwiek z poniższych:
1. Patronite / dowolna forma stałego wsparcia finansowego.
2. Reklamy w aplikacji.
3. Subskrypcja / funkcje premium.

W momencie rewizji: albo pisemne potwierdzenie od Open-Meteo, że dany model finansowania
mieści się w "non-commercial use", albo przejście na płatny plan API Standard
(commercial use, ceny w portalu Open-Meteo), albo zmiana dostawcy pogody na taki z
licencją jawnie dopuszczającą komercyjne użycie (np. MET Norway — CC BY 4.0, bez
rozróżnienia komercyjne/niekomercyjne, ale z limitem 20 req/s na całą aplikację i mniej
bogatym zestawem zmiennych — wymaga osobnej weryfikacji przed wyborem).

## Consequences

- Zero kosztu na start, zero ryzyka prawnego dopóki zasada "bez monetyzacji" jest
  przestrzegana.
- Roadmapa monetyzacji (§109 Master Planu — "monetyzacja nie może blokować MVP") nie
  jest tym ADR zablokowana, ale **wymaga** przejścia przez ten dokument, zanim jakikolwiek
  mechanizm zarobkowy zostanie włączony w produkcji.
- Connector `open_meteo` musi być zaimplementowany za kontraktem `DataConnector` (§35),
  żeby zmiana dostawcy przy rewizji tego ADR nie wymagała zmian w Geo Engine, API ani
  w modelu danych — tylko w connectorze i w mapowaniu pól w Data Dictionary.

## Checklista „przed monetyzacją” (dodane 2026-10-01, ADR-022)

Żadna z pozycji monetyzacji (reklamy, subskrypcja/premium, Patronite/stałe wsparcie) nie jest
włączana, dopóki wszystkie punkty nie są odhaczone w PR rewizji tego ADR:

- [ ] Aktywny komercyjny plan Open-Meteo (Standard+; licencja komercyjna) — albo pisemne
      potwierdzenie Open-Meteo dla danego modelu finansowania, albo inny dostawca (patrz Trigger).
- [ ] Produkcyjne env ustawione: `OPEN_METEO_FORECAST_BASE_URL`, `OPEN_METEO_AIR_QUALITY_BASE_URL`
      (hosty `customer-*`), `OPEN_METEO_API_KEY` (sekret poza repo); jedno żądanie testowe OK,
      w `source_fetches.endpoint`, logach i `/health/sources` brak klucza.
- [ ] Pozostałe źródła z `commercial_use: NIE` w `source-registry.md` (m.in. IMGW) mają
      załatwioną licencję komercyjną lub są wyłączone.
- [ ] IMGW: płatna umowa (biznes@imgw.pl) albo potwierdzenie, że używane zbiory to dane o
      wysokiej wartości (HVD, rozp. UE 2023/138 — dziś NIEZWERYFIKOWANE); wyjaśnione z IMGW
      CC BY-NC-ND 4.0 zbioru na dane.gov.pl (rekord 3120) vs API.
- [ ] Open-Meteo: pisemne potwierdzenie dla Patronite (szara strefa), jeśli to ta forma;
      ceny planów zweryfikowane u źródła (w registry NIEZWERYFIKOWANE).
- [ ] Atrybucje (Open-Meteo, CAMS, GIOŚ, IMGW…) nadal widoczne w ekranie Źródła.
- [ ] ADR-003 zmieniony na Superseded z nową decyzją.

## Addendum 2026-10-02 (ADR-031)

Pisemne potwierdzenie OpenMeteo GmbH rozstrzyga „szarą strefę”: dobrowolne darowizny (Patronite) są
dozwolone na Free API; reklamy i płatne/premium funkcje czynią użycie komercyjnym. Trigger 1 powyżej
(Patronite) nie wymusza już zmiany planu Open-Meteo; triggery 2 i 3 (reklamy, premium) bez zmian i
mają bramkę w `docs/release/business-gates.md`. Zakaz „Patronite ani innej formy stałego wsparcia”
z sekcji Decision dotyczył ryzyka licencyjnego Open-Meteo, które potwierdzenie usuwa; decyzja o samym
włączeniu darowizn pozostaje decyzją produktową właściciela. Punkty checklisty o IMGW i innych źródłach
nie są objęte potwierdzeniem Open-Meteo.
