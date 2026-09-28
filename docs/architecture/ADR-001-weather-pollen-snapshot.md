# ADR-001: Pogoda i pyłki jako snapshot w bazie, nie zapytania on-demand

**Status:** Accepted
**Data:** 2026-09-28

## Context

Master Plan (§55, §106, zasada 14 w CLAUDE.md) zakłada, że mobile API czyta zagregowany
lokalny kontekst z naszej bazy, a nie woła zewnętrznych API bezpośrednio przy każdym
żądaniu użytkownika. To musi być jawnie ustalone dla pogody (Open-Meteo) i pyłków/CAMS,
bo w przeciwnym razie każdy connector mógłby próbować robić to inaczej.

Dodatkowe ograniczenia:
- Open-Meteo, darmowy tier: max 10 000 wywołań/dzień, 5 000/h, 600/min, wyłącznie
  użycie niekomercyjne (patrz ADR-003).
- Współrzędne użytkownika nie powinny trafiać do stron trzecich (Principle 7 — nie
  zbieramy/nie ujawniamy danych bez powodu).
- Docelowo produkt ma działać jako "hub" dla całej Polski, niezależnie od liczby
  aktualnie aktywnych użytkowników w danym miejscu.

## Problem

Jak pobierać i serwować dane pogodowe i pyłkowe tak, żeby:
1. koszt (liczba wywołań do zewnętrznych API) nie rósł liniowo z liczbą użytkowników,
2. współrzędne użytkownika nigdy nie opuszczały naszego backendu,
3. przejście z małej liczby testerów do całej Polski nie wymagało zmiany architektury?

## Options

**A. On-demand per-user z cache.** API woła Open-Meteo/CAMS przy pierwszym request z danej
okolicy, cache'uje wynik na krótko. Prosty start, ale koszt rośnie z ruchem i wciąż istnieje
ścieżka "request użytkownika → zewnętrzne API".

**B. Snapshot całej Polski, pełna siatka, od dnia 1.** Najbardziej "docelowe", ale przy
darmowym limicie Open-Meteo (10k/dzień) i naszym słowniku (~22 zmienne, więc realnie
liczone jako >1 wywołanie/punkt) przekracza limit już przy siatce rzędu 700+ punktów
odświeżanej kilka razy dziennie.

**C. Snapshot tylko aktywnych obszarów, docelowo cała Polska (wybrana).** Scheduler
pobiera dane tylko dla obszarów, w których są zarejestrowane urządzenia/obserwowane
lokalizacje (patrz ADR-002), zapisuje do bazy jako snapshot z `fetched_at`/`valid_until`.
Mobile API zawsze czyta z bazy, nigdy z zewnętrznego API. Zasięg pobierania (aktywne
obszary → cała Polska) jest parametrem konfiguracyjnym schedulera, nie zmianą architektury.

## Decision

Wybieramy opcję **C**.

- Jednostka geograficzna pobierania: **gmina** (centroid, powiązanie przez TERYT), nie
  surowa siatka współrzędnych — bo i tak mapujemy do TERYT dla push (ADR-002) i dla
  Administrative Context (§26 Master Planu).
- Tabela `weather_snapshots` / `pollen_snapshots` (lub rozszerzenie `forecasts` z §30)
  z kluczem `geo_area_id + valid_from`, `source_id`, `fetched_at`, `freshness_status`.
- Scheduler: job per źródło, harmonogram i lista aktywnych gmin konfigurowalne (env/DB),
  nie hardcode'owane w connectorze.
- Endpoint mobile (`GET /api/v1/weather`, `/api/v1/pollen`, `/api/v1/dashboard`) zawsze
  czyta z tych tabel przez Geo Engine (§27) — nigdy nie wywołuje Open-Meteo/CAMS w locie.
- Wyjątek: pierwszy request dla gminy spoza obecnego zasięgu pobierania może wywołać
  jednorazowy fetch z timeoutem, po czym gmina trafia na listę aktywnych — wymaga to
  blokady przeciw duplikacji równoległych fetchy dla tej samej gminy.
- Licznik dziennych wywołań per źródło w bazie, alert przy 70% dziennego limitu.

## Consequences

- Mobile API jest szybkie i tanie (czyta z Postgresa), niezależnie od dostawcy pogody.
- Zmiana dostawcy (Open-Meteo → MET Norway/Standard) to zmiana connectora i mapowania
  pól, nie zmiana kontraktu API ani modelu danych.
- Koszt wywołań zewnętrznych rośnie z liczbą **obsługiwanych gmin**, nie z liczbą
  użytkowników ani ich zapytań — łatwe do policzenia i zabudżetowania.
- Wymaga utrzymania tabeli "aktywne obszary" i prostego mechanizmu jej rozszerzania.
- Świeżość danych pogodowych zależy od częstotliwości schedulera, nie od momentu
  otwarcia aplikacji — trzeba to uwzględnić w progach freshness (§42).
