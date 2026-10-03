# Rzeki i hałas — realizacja lokalnych tematów

Date: 2026-10-03
Status: Implemented in branch, awaiting PR review/activation

## Goal / Scope

Dwa tematy dostępne z Start: bieżące obserwacje wodowskazów w okolicy oraz ostatnie
opublikowane pomiary hałasu. Reuse dotychczasowych adapterów i ekranów, ADR-035.

## Acceptance criteria / Data contract

- Hydro dla wybranej lokalizacji: source isolation, najnowszy rekord, promień 50 km,
  dystans, czas, cm i progi; nieznana lokalizacja 404, nieprawidłowy promień 422.
- API bez geo_area_id pozostaje krajowe. Zero zewnętrznych wywołań w żądaniu mobile.
- Publikacja disabled: stations[], UNAVAILABLE; brak fałszywego aktywnego wejścia.
- Niepotwierdzone/stare dane nie uspokajają. Przyszłe daty i nonfinite values nie są świeże.
- Hałas ma jednoznaczne wejście, okres pomiaru i distance. History ≠ live.
- Import niepełny/awaria ≠ brak pomiarów. Zmienność/przekroczenia tylko według źródła.
- Osobny agent review, backend SQL tests, mobile sorting/freshness tests, lint/types/contract checks.

## Non-goals / Architecture / Security

Bez map, kont, mikrofonu, nowych zależności, nowych tabel, push i automatycznego schedulera hałasu.
Nie oceniamy lokalnego zagrożenia powodziowego na podstawie samego dystansu. Parametry żądania
walidowane; brak sekretów; istniejące Source Approval Gate i atrybucja.

## Dependencies / Activation

1. Merge bazowego PR #150 i tego zestawu zmian; deploy istniejących migracji według instrukcji IMGW.
2. Hydro: potwierdzenie strefy czasu API i zakresu warunków wykorzystania; obecne Europe/Warsaw
   jest założeniem legacy. W razie innej konwencji konieczny osobny plan korekty danych/IDs.
3. Hydro: ingest, kontrola aktualności i progów, następnie IMGW_HYDRO_PUBLICATION_ENABLED=true.
   Flaga obejmuje również dotychczasowe warningshydro; dlatego ich adapter/geo/warunki także
   trzeba sprawdzić przed aktywacją. Nie traktować tego przełącznika jako wyłącznie river-only.
4. Noise: operator potwierdza aktualny import i stan Source Registry. Jest dowód pełnego importu
   64 kombinacji z 2026-10-03, 208826 rekordów; starszy wpis registry nadal wymienia otwarte
   bramki (np. pusty wynik poprawnych filtrów). Zamknąć je na podstawie odpowiedzi, nie deklaracji.
5. NEIGHBORHOOD_NOISE_ENABLED=true, sprawdzić pozytywne i puste lokalizacje przez własne API.
   Istniejący importer CLI, import ręczny (cykl źródła niepotwierdzony); nie pobierać całego kraju ponownie
   jeśli aktualne aktywne snapshoty już są w DB.
6. Brief Design Lead → nowe UI → build i QA urządzenia. Ten PR nie oznacza deploy/aktywacji.

Rollback: obie dotychczasowe flagi false; wcześniejsze kontrakty pozostają kompatybilne.
