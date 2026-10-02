# ADR-031: Pisemne potwierdzenie OpenMeteo GmbH — zakres użycia Free API i bramka monetyzacji

**Status:** Accepted
**Data:** 2026-10-02
**Uzupełnia / częściowo zastępuje:** ADR-003 (Patronite nie jest już „szarą strefą”), ADR-022 (gate monetyzacji)

## Context

ADR-003 przyjął, że darmowy tier Open-Meteo jest wyłącznie niekomercyjny, a Patronite to „szara
strefa” wymagająca pisemnego potwierdzenia. Właściciel projektu otrzymał bezpośrednie pisemne
potwierdzenie od OpenMeteo GmbH dotyczące przypadku użycia Za Oknem (treść: patrz
`docs/business/provider-licensing.md`; oryginał korespondencji NIE jest w repo).

## Problem

Co dokładnie wolno na Free API, co robi użycie komercyjnym i co z tego wynika dla architektury i
dla momentu monetyzacji?

## Decision

Potwierdzone przez Open-Meteo (relacja właściciela, 2026-10-02):

| Pytanie | Odpowiedź |
|---|---|
| W pełni darmowa aplikacja Za Oknem na Free API | **Dozwolone** |
| Prowadzenie aplikacji przez zarejestrowaną JDG | Samo w sobie **nie** wymaga planu komercyjnego, dopóki aplikacja jest darmowa i bez reklam |
| Dobrowolne darowizny (np. Patronite) | **Dozwolone** na Free API |
| Reklamy | Czynią użycie **komercyjnym** |
| Płatne / premium funkcje | Czynią użycie **komercyjnym**, nawet jeśli same dane pogodowe/pyłkowe zostają darmowe |
| Architektura Open-Meteo → zaplanowany fetch backendu → storage/cache → API Za Oknem → wielu użytkowników | **Jawnie dozwolona** (okresowe pobieranie, przechowywanie ostatnich danych/prognozy, serwowanie wielu użytkownikom) |
| Po komercjalizacji | Odpowiedni jest plan **Standard** (komercyjny) dla tej architektury |
| Oferta handlowa | 50% rabatu na pierwszy rok komercyjny, ważna 6 miesięcy — **metadane biznesowe**, nie konfiguracja aplikacji |

Wnioski dla projektu:

1. **Status źródeł `open_meteo` i `open_meteo_pollen` = APPROVED** dla obecnej architektury
   (darmowa aplikacja, bez reklam, bez płatnych/premium funkcji). Wpisy w `source-registry.md`
   zaktualizowane.
2. **Cały dostęp do Open-Meteo zostaje po stronie serwera.** Mobile czyta wyłącznie API Za Oknem
   (reguła #14, ADR-001). Zapytań per użytkownik do Open-Meteo nie wprowadzamy.
3. **Zaplanowana ingestia + snapshoty w PostgreSQL** (ADR-001/ADR-004) zostają bez zmian — to
   dokładnie architektura wprost dopuszczona przez dostawcę.
4. **Konfiguracja providera pozostaje scentralizowana** (`app/config.py`, ADR-022): hosty i klucz
   wyłącznie z env — `OPEN_METEO_FORECAST_BASE_URL`, `OPEN_METEO_AIR_QUALITY_BASE_URL`
   (osobne zmienne, bo Forecast i Air Quality to różne hosty), `OPEN_METEO_API_KEY` (opcjonalny na
   Free, wymagany na planie komercyjnym; wysyłany jako `apikey`, nigdy nie trafia do logów,
   `source_fetches.endpoint` ani `last_error`). Domyślne hosty Free są zdefiniowane w jednym
   miejscu (`config.py`), nigdzie więcej w kodzie. **Bez zmian kodu** — implementacja już spełnia te zasady.
5. **Brak obsługi rozliczeń/subskrypcji Open-Meteo** w aplikacji — przejście na plan komercyjny to
   zmiana env na serwerze (ADR-022).
6. **Atrybucja Open-Meteo / CAMS pozostaje obowiązkowa** w metadanych źródeł i w UI (ekran Źródła,
   karta pyłków, pole `attribution` w odpowiedziach API).
7. **Bramka wydaniowa (business gate):** PRZED włączeniem reklam albo płatnych/premium funkcji
   trzeba zweryfikować, że Open-Meteo działa na odpowiednim planie komercyjnym (Standard+) —
   `docs/release/business-gates.md`. Patronite/darowizny tej bramki NIE uruchamiają (dobrowolne
   wsparcie jest dozwolone na Free), ale decyzja o jego włączeniu jest nadal decyzją produktową
   właściciela (CLAUDE.md).

## Czego to potwierdzenie NIE obejmuje

- Dotyczy **wyłącznie Open-Meteo** (pogoda, pyłki CAMS przez Open-Meteo). Pozostałe źródła mają
  własne warunki: IMGW (`commercial_use: NIE` / niejasna licencja, patrz `source-registry.md` i
  checklista ADR-003), GIOŚ, GeoNames (CC BY 4.0). Dla reklam / funkcji premium każde z nich
  trzeba rozważyć osobno.
- Nie zmienia limitów Free API (600/min, 5000/h, 10000/dzień, 300000/mies.) ani braku gwarancji uptime.
- Nie zastępuje własnej weryfikacji prawnej właściciela; ten ADR to zapis relacji z korespondencji.

## Consequences

- Brak zmian architektury i kodu; zmiany dotyczą dokumentacji, gate'ów i rejestru źródeł.
- Reklamy i premium pozostają zablokowane do przejścia przez `docs/release/business-gates.md`.
- Rabat 50% (oferta handlowa) jest śledzony w `docs/business/provider-licensing.md` razem z terminem
  ważności, który trzeba uzupełnić datą oferty.
