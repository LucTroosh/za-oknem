# TASK 7.2 — Ostrzeżenia w agregacie dashboardu + mobile (§55 Master Planu)

## Goal

§55 wymienia `alerts` wprost jako część agregatu dashboardu. Dotąd
`dashboard_latest()` miał tylko `air`/`weather`, a ostrzeżenia IMGW były
dostępne wyłącznie przez `/alerts/latest`, którego mobile nie czytało.

## Scope

- `api/v1/alerts.py`: zapytanie o aktywne ostrzeżenia wydzielone do
  `current_alerts(db)` — jedno miejsce dla `/alerts/latest` (odpowiedź bez
  zmian) i agregatu.
- `api/v1/dashboard.py`: nowy blok najwyższego poziomu `alerts`
  `{scope: "national", source: "imgw", attribution, items}` — **nie** w każdej
  gminie, bo przed TASK-9.5 lista jest niefiltrowana dla całej Polski i
  umieszczenie jej pod gminą sugerowałoby lokalność.
- Mobile: sekcja „Ostrzeżenia — cała Polska” (nagłówek listy), treści
  dosłownie ze źródła (zdarzenie, stopień jako surowa wartość, województwa,
  ważność, biuro, freshness) + atrybucja IMGW z source-registry.

## Non-goals

- Geo-matching ostrzeżeń do lokalizacji (TASK-9.5) — do tego czasu etykieta
  „cała Polska” jest obowiązkowa.
- Hydrologia na mobile (druga część TASK-7.2 w BACKLOG) — osobny PR.
- Komunikat „brak ostrzeżeń” — rozwiązany w TASK-7.4 (ADR-012): pokazywany
  tylko, gdy wszystkie źródła ostrzeżeń mają świeże udane pobranie.

## Acceptance Criteria

- [x] `dashboard_latest()` zwraca `alerts` z `scope="national"`, `source`,
      atrybucją IMGW i pozycjami z freshness; brak `alerts` w obiektach gmin
      (`test_dashboard_includes_national_alerts_block`).
- [x] `items == []` przy braku ostrzeżeń (`test_dashboard_alerts_items_empty_when_no_alerts`).
- [x] `/alerts/latest` bez zmian (istniejące `test_alerts.py`).
- [x] Mobile: nagłówek „Ostrzeżenia — cała Polska”; województwa z surowych
      `areas` bez zgadywania (`alerts.test.ts`).
- [x] `ruff check` czyste; CI: pytest, eslint, tsc, vitest.

## Dependencies

Brak. Dotyka `dashboard.py`/`index.tsx`/ROADMAP jak PR #56/#57 — konflikty
trywialne (inne fragmenty plików).

## Data Contract

Addytywne pole `alerts` w odpowiedzi `/api/v1/dashboard/latest`. Bez zmian
schematu bazy.

## Security

Brak nowej powierzchni — publiczny odczyt z naszej bazy (rule #14); LLM nie
uczestniczy (rule #10).

## Architecture Impact

Brak nowej decyzji — realizacja §55; bez ADR.
