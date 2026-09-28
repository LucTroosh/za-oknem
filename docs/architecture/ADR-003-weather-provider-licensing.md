# ADR-003: Open-Meteo (darmowy, niekomercyjny tier) jako dostawca pogody w fazie social-impact

**Status:** Accepted — do rewizji przed jakąkolwiek monetyzacją
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
