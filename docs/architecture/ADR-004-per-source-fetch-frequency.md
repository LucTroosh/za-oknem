# ADR-004: Częstotliwość fetchowania = rzeczywisty cykl aktualizacji źródła, nie stała globalna

**Status:** Accepted
**Data:** 2026-09-28

## Context

ADR-001 wprowadził snapshot per gmina zamiast zapytań on-demand, ale zostawił
harmonogram fetchowania jako "do ustalenia w Phase 5". Różne źródła aktualizują się
z różną częstotliwością: CAMS pollen raz dziennie, dane pogodowe z modeli — częściej,
pomiary stacji (GIOŚ) — praktycznie co godzinę, ostrzeżenia (IMGW) — nieregularnie,
kiedy się pojawią.

## Problem

Jeśli scheduler pobiera wszystko z jedną, arbitralną częstotliwością (np. "co godzinę
dla wszystkiego, na wszelki wypadek"), to dla źródeł wolno zmieniających się (pyłki:
1x/dzień) marnujemy budżet zapytań bez żadnej korzyści dla użytkownika — dane i tak
się nie zmieniły. Przy source'ach z twardym rate limitem (Open-Meteo, CAMS ADS) to
zwiększa ryzyko wyczerpania limitu lub zbanowania za nadużywanie API bez uzasadnienia.

## Decision

- Częstotliwość fetchowania per connector **wynika z rzeczywistego cyklu aktualizacji
  danego źródła**, nie jest arbitralną stałą globalną ani zgadywana "z zapasem".
- Rzeczywisty cykl aktualizacji musi być **zweryfikowany** (dokumentacja źródła, nie
  domysł) i zapisany w polu `frequency` w `docs/data/source-registry.md` jako część
  Source Approval Gate (§38) — connector nie wchodzi do implementacji bez tego wpisu.
- Domyślna zasada: **nie pollujemy częściej, niż źródło faktycznie publikuje nowe
  dane.** Jeśli źródło aktualizuje się raz na dobę — fetch raz na dobę. Jeśli co
  godzinę — fetch co godzinę. Szybsze pollowanie "na zapas" jest zabronione bez
  udokumentowanego uzasadnienia w tym pliku.
- Wyjątek: źródła safety-critical (ostrzeżenia meteo/hydro, zamknięcia kąpielisk)
  mogą być pollowane częściej niż ich własny typowy cykl publikacji, jeśli endpoint
  jest lekki (mały payload, niski koszt), bo koszt nieaktualnego ostrzeżenia
  przewyższa koszt dodatkowego zapytania. Musi to być jawnie zapisane w Source
  Registry z uzasadnieniem, nie domyślne.
- Harmonogram każdego joba w schedulerze (§46) jest konfigurowalny per source_code
  i ustawiany na podstawie `frequency` z Source Registry — zmiana częstotliwości
  fetchowania wymaga aktualizacji wpisu w rejestrze, nie tylko zmiany w kodzie.
- Każdy connector monitoruje swoje własne zużycie limitu (wzorem ADR-003 dla
  Open-Meteo: alert przy 70% dziennego limitu) niezależnie od częstotliwości fetchu.

## Consequences

- Przed implementacją connectora trzeba faktycznie zweryfikować cykl aktualizacji
  źródła (nie zgadywać) — to dodatkowy krok w Source Approval Gate, ale tani.
- Źródła, których cykl aktualizacji nie jest jeszcze zweryfikowany (Open-Meteo model
  refresh, GIOŚ, IMGW), mają w Source Registry status wskazujący, że częstotliwość
  fetchu jest **do potwierdzenia przed implementacją**, a nie przyjmują domyślnie
  "co godzinę" bez sprawdzenia.
- Realny efekt: mniej zużytego limitu API, mniejsze ryzyko zbanowania, dane w
  dashboardzie nadal odzwierciedlają rzeczywistą świeżość źródła (Principle 3).
