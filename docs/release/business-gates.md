# Bramki biznesowe przed wydaniem (business gates)

Techniczne checki (lint, testy, build) są w `CLAUDE.md` i CI. Ta lista dotyczy rzeczy, których CI nie
sprawdzi: licencje i monetyzacja. Każda pozycja ma właściciela i musi być odhaczona w PR, który
włącza daną funkcję.

## Gate 1 — reklamy lub płatne / premium funkcje (Open-Meteo, ADR-031)

**PRZED włączeniem reklam albo jakiejkolwiek płatnej / premium funkcji** (subskrypcja, jednorazowy
zakup, odblokowanie funkcji) — nawet jeśli same dane pogodowe/pyłkowe zostają darmowe:

- [ ] Open-Meteo przełączone na odpowiedni plan komercyjny (Standard+), potwierdzone w panelu klienta.
- [ ] Produkcyjne env ustawione (poza repo): `OPEN_METEO_FORECAST_BASE_URL`,
      `OPEN_METEO_AIR_QUALITY_BASE_URL` (hosty `customer-*`, adres hosta Air Quality zweryfikować w
      panelu), `OPEN_METEO_API_KEY`.
- [ ] Jedno żądanie testowe OK; w `source_fetches.endpoint`, logach i `GET /api/v1/health/sources`
      nie ma klucza.
- [ ] `OPEN_METEO_DAILY_CALL_LIMIT` dopasowany do planu (alert 70% ma sens).
- [ ] Oferta rabatowa (`docs/business/provider-licensing.md`): sprawdzona data ważności u dostawcy.
- [ ] Pozostałe źródła z `commercial_use: NIE` w `source-registry.md` (m.in. IMGW) mają licencję
      komercyjną lub są wyłączone — checklista ADR-003.
- [ ] Atrybucje (Open-Meteo, CAMS, GIOŚ, IMGW, GeoNames) nadal widoczne w aplikacji.

## Gate 2 — darowizny (np. Patronite)

Dozwolone na Free API Open-Meteo (ADR-031), więc **nie** wymagają zmiany planu. Mimo to:

- [ ] Decyzja właściciela o włączeniu (CLAUDE.md: nie włączać monetyzacji bez pytania).
- [ ] Darowizna jest dobrowolna i niczego w aplikacji nie odblokowuje (inaczej → Gate 1).
- [ ] Pozostałe źródła nie zabraniają takiego użycia (patrz uwaga o IMGW w `source-registry.md`).

## Jak to egzekwować

Przy review każdego PR dodającego SDK reklam, płatności, subskrypcje lub flagę premium: zablokować
merge, dopóki Gate 1 nie jest odhaczony w opisie PR. (Świadomie bez kodu blokującego na razie:
dodanie takiej funkcji jest decyzją produktową, a nie czymś, co wykryje test.)
