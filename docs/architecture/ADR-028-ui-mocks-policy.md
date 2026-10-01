# ADR-028: Mocki UI — flaga, fixture'y z typami kontraktu, adapter `useX()`, zakaz mocków danych bezpieczeństwa

- **Date:** 2026-10-01
- **Status:** Proposed (do zaakceptowania wraz z merge PR „mapa ekranów UI”; implementacja w TASK-12.10)

## Context

Właściciel przygotowuje design osobno i chce zobaczyć strukturę ekranów, zanim backend ma wszystkie dane
(wybór gmin, wykres pyłków godzinowych, preferencje, powiadomienia). Mapa ekranów: `docs/ui/screen-map.md`.
Obowiązują: reguła #10 (dane bezpieczeństwa nie mogą być zmyślone), #8 (stare/brak danych widoczne), #14
(mobile czyta tylko z naszego API), ADR-024 (typy z kontraktu), ADR-027 (tokeny, kontrast testowany),
Master Plan §59/§80 (stany UI), §87 (profile EAS: development/preview/production).

## Problem

Jak pokazywać makiety danych tak, żeby (a) podmiana na live nie wymagała przepisywania komponentów,
(b) mock nigdy nie mógł zostać wzięty za realne dane — zwłaszcza alerty, kąpieliska i jakość wody — i
(c) produkcyjny build nie zawierał ani nie włączał mocków?

## Options

1. **Brak mocków** — ekrany powstają dopiero po backendzie. Właściciel nie widzi struktury, a design
   czeka; ryzyko, że UI zakłada pola, których backend nigdy nie da.
2. **Mocki wpisane w komponenty** (`if (DEV) <Fake/>`) — szybkie, ale podmiana = przepisanie komponentu,
   łatwo zostawić w release, brak jednego miejsca z polityką.
3. **Fixture'y + adapter `useX()` + flaga + obowiązkowe oznaczenie, bez mocków domeny bezpieczeństwa
   (wybrana).** Komponent dostaje ten sam typ z mocka i z API; mock jest widoczny z konstrukcji; bezpieczeństwo
   wyłączone typem, nie dyscypliną.
4. **Serwer mocków (MSW/json-server)** — nowa zależność i infrastruktura; mock działałby „jak prawdziwy
   backend”, czyli zwiększałby ryzyko pomyłki z live.

## Decision

Opcja **3**.

- Flaga `EXPO_PUBLIC_UI_MOCKS` + `EXPO_PUBLIC_APP_ENV` (`development`/`preview`/`production`, brak = production).
  `mocksEnabled()`: dev domyślnie włączone (`=0` wyłącza), preview tylko z `=1`, production **zawsze wyłączone**
  (flaga ignorowana; ustawienie jej w production to błąd builda).
- Fixture'y wyłącznie w `apps/mobile/lib/mock/`, typowane typami z `packages/api-contract/schema.ts`; pola spoza
  kontraktu mają typy `Proposed*` powiązane z zadaniem backendu (żaden mock nie zakłada pola bez taska).
- Adapter `useX(): Sourced<T>` z `origin: "live" | "mock"`; komponenty nie znają źródła. `MockBadge`/`MockBanner`
  („PRZYKŁADOWE DANE”) pojawiają się automatycznie z `origin`, kontrast ≥ 4.5:1 w obu motywach (tokeny
  `mockFg`/`mockBg` w `TEXT_PAIRS`).
- **Zakaz:** żadnych fixture'ów ostrzeżeń, stanów alarmowych stacji, statusu kąpielisk, jakości wody, werdyktu
  „Na dwór” ani indeksu powietrza. Hooki tych domen powstają bez parametru `mock` (typ). Test polityki skanuje
  `lib/mock/**`. Dla źródeł ⛔ sekcja nie istnieje w UI (spec UI właściciela: bez „wkrótce”, bez nieaktywnych kafelków); to samo dotyczy rekomendacji aktywności do czasu backendu (TASK-7.9).
- Mock nie dziedziczy tożsamości live (wymyślone nazwy, osobna karta przy polu spoza kontraktu), nie udaje
  świeżości, nie robi żądań.
- Znacznik `__UI_MOCK_FIXTURE__` w każdym pliku fixture; CI sprawdza jego brak w bundlu produkcyjnym.

## Consequences

- Dodatkowy kod (`lib/mock/`, dwa komponenty, hooki adapterów); w zamian podmiana na live = zmiana źródła w hooku.
- Zmiana kontraktu (nowe pole w `schema.ts`) łamie kompilację fixture'ów — to zamierzone (mock nie wyprzedza ani nie
  zostaje w tyle za rzeczywistością).
- W produkcji nie pokazujemy też kontrolek udających brakującą funkcję (wyszukiwarka bez danych, GPS bez TASK-12.3) — mock tych elementów istnieje tylko w dev/preview. Produkcja jest chroniona trzema warstwami: logika `mocksEnabled()`, test jednostkowy i skan bundla w CI.
  Dopóki nie istnieje `eas.json` (§87), „production” to `APP_ENV=production` lub brak zmiennej.
- Bez nowych zależności. Wymaga decyzji właściciela o wyglądzie `MockBadge`/`MockBanner` (kolor, kształt), nie o
  samym mechanizmie.
- Nie obejmuje: mocków po stronie backendu (fixture API), danych testowych w testach jednostkowych (te zostają
  tam, gdzie są).
