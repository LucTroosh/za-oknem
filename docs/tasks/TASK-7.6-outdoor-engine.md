# TASK 7.6 — Outdoor Interpretation Engine (§52 Master Planu)

## Goal

Deterministyczna, testowalna funkcja zamieniająca bieżące wejścia
(temperatura/odczuwalna, opady, wiatr/porywy, UV, widoczność, PM2.5/PM10) na
`GOOD | MODERATE | POOR | UNKNOWN` + `reasons[]` + `missing[]`. Bez LLM
(rule #10, §52/§53). Decyzje: ADR-016.

## Scope

- `apps/api/app/outdoor.py` — `evaluate(inputs, rules=RULES)`, tabela progów
  `RULES` (jedno miejsce, każdy próg z `basis`: źródło + data lub "PRODUCT
  DECISION - do kalibracji").
- `apps/api/tests/test_outdoor.py`.
- ADR-016, ten dokument.

## Acceptance Criteria

1. Czysta funkcja, tylko stdlib; bez DB/I/O/zegara/LLM.
2. Najgorszy czynnik wyznacza wynik; MODERATE+MODERATE nie daje POOR.
3. Każdy próg: zweryfikowane źródło z URL i datą albo jawna decyzja produktowa.
4. `None`/STALE/UNAVAILABLE/NaN/inf nigdy nie dają cichego GOOD: brak grupy
   rdzeniowej przy dobrych pozostałych → `UNKNOWN`; zła dostępna ocena stoi
   mimo braków; nieświeże wejście nie wpływa na wynik; wszystko w `missing[]`.
5. `reasons[]`: `code, param, value, threshold, comparison, unit, level`,
   kolejność deterministyczna (POOR najpierw, potem kolejność `RULES`).
6. Pogorszenie któregokolwiek wejścia nigdy nie poprawia wyniku
   (`GOOD < UNKNOWN < MODERATE < POOR`).
7. Zero zmian w `dashboard.py`, modelach, migracjach, mobile.

## Tests

`tests/test_outdoor.py`: granice każdej reguły (tuż pod/na/nad, inkluzywność),
kombinacje, None/stale/NaN, semantyka UNKNOWN, kolejność reasons, brak efektów
ubocznych, dokumentacja reguł, własność monotoniczności (siatka + pary).
Bez `parametrize` — działa też pod gołym `python3`.

## Non-goals

- Wpięcie w `dashboard_latest()` (TASK-7.7), `OutdoorCard` mobile (TASK-7.8).
- Profil/wrażliwość/preferencje użytkownika (TASK-12.4) — jest tylko punkt
  wpięcia: parametr `rules`.
- Konwersja jednostek, wybór stacji GIOŚ, prognoza godzinowa ("kiedy wyjść"),
  śnieg, pyłki, NO2/O3.
- Kalibracja progów "product decision" na realnych danych.

## Dependencies

TASK-5.1/5.3/5.4 (pola Open-Meteo), TASK-4.1 (PM2.5/PM10 GIOŚ).

## Data Contract

Wejście: `OutdoorInputs` z polami `Reading(value, freshness) | None`:
`temperature_2m, apparent_temperature, precipitation, wind_speed_10m,
wind_gusts_10m, uv_index, visibility, pm25, pm10` (°C, mm, km/h, indeks, m,
µg/m³). Wyjście: `OutdoorResult(rating, reasons, missing)`;
`Missing(group, params, status MISSING|STALE|INVALID, core)`.

## Security

Brak I/O i sekretów. Wynik to DERIVED, nie dane bezpieczeństwa: nie zastępuje
ostrzeżeń IMGW/alertów (rule #10).

## Architecture Impact

Jeden nowy moduł bez zależności od reszty aplikacji; nie zmienia schematu ani
API. Decyzja architektoniczna: ADR-016.
