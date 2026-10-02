# CLAUDE.md — Za Oknem

Ten plik jest operacyjnym przewodnikiem dla Claude Code podczas pracy nad repozytorium.
Pełna specyfikacja: `docs/architecture/Development-Master-Plan-v1.2.md` (source of truth).
Rejestr źródeł danych: `docs/data/source-registry.md`. Decyzje: `docs/architecture/ADR-*.md`.
Stan projektu (DONE/PARTIAL/BLOCKED/TODO vs Master Plan): `docs/ROADMAP.md`.

## Produkt (jedno zdanie)

Za Oknem = lokalny agregator: "co dzieje się wokół mnie?" — powietrze, pogoda, pyłki, woda,
hydrologia, alerty — dla Polski, na start Android, MVP bez mapy i bez obowiązkowego konta.

## Zasady nienaruszalne (nie pytaj, po prostu stosuj)

1. Jedno zepsute źródło nie może zepsuć całego dashboardu.
2. PostgreSQL = trwałe źródło prawdy. Redis = cache / stan krótkotrwały.
3. Żadnych sekretów w repo — tylko zmienne środowiskowe.
4. Zmiana schematu bazy = wyłącznie migracja Alembic. Nigdy ręcznie na produkcji.
5. Każdy request do zewnętrznego źródła ma timeout i kontrolowany retry (nie nieskończony).
6. Każdy connector jest izolowany, ma provenance (źródło, endpoint, timestampy, source record id).
7. Measurement ≠ Forecast ≠ Event ≠ Alert ≠ Notification — nie mieszamy tych pojęć w kodzie ani w bazie.
8. Stare dane muszą wyglądać na stare (status freshness: FRESH / RECENT / STALE / UNAVAILABLE).
9. Geo matching jest deterministyczny i testowalny (nearest station / point-in-polygon / grid read —
   patrz ADR-001), nigdy "na oko".
10. LLM nigdy nie jest źródłem prawdy dla danych bezpieczeństwa (alerty, zamknięcia kąpielisk,
    jakość wody). Wolno mu ekstrahować/klasyfikować tekst, z zachowaniem oryginalnego źródła i timestampu.
11. Brak zbędnych uprawnień. Brak background location w MVP. Brak obowiązkowego konta w MVP.
12. Żadna zmiana architektury bez ADR (`docs/architecture/ADR-XXX-title.md`: Context, Problem,
    Options, Decision, Consequences, Date, Status).
13. Żaden task bez acceptance criteria (patrz szablon zadania niżej).
14. Mobile API (`/api/v1/dashboard` i pochodne) czyta WYŁĄCZNIE z naszej bazy — nigdy nie woła
    zewnętrznego API na żądanie użytkownika (patrz ADR-001).
15. Przed użyciem produkcyjnym każde źródło przechodzi Source Approval Gate i ma wpis w
    `docs/data/source-registry.md` (licencja, commercial_use, rate_limit, attribution, status).
16. Częstotliwość fetchowania per connector = rzeczywisty, zweryfikowany cykl aktualizacji
    danego źródła (patrz ADR-004), nigdy zgadywana stała "na wszelki wypadek". Wyjątek tylko
    dla źródeł safety-critical (ostrzeżenia) i tylko z jawnym uzasadnieniem w Source Registry.
17. FREE-FIRST: jeśli funkcję da się zbudować na wiarygodnym darmowym/open-data źródle, nie integrujemy płatnego odpowiednika w MVP (free-first ≠ approved — gate #15 dalej obowiązuje; endpointy i klucze providerów tylko w env) — patrz ADR-022.

## Stack (nie zmieniać bez ADR)

Mobile: React Native + Expo + TypeScript + Expo Router + NativeWind.
Backend: Python + FastAPI + Pydantic + SQLAlchemy + Alembic, modular monolith + workers.
DB: PostgreSQL + PostGIS. Cache: Redis. Infra: Ubuntu 24.04 + Docker + Caddy na VPS.
API: wersjonowane pod `/api/v1/`. Build: EAS. CI: GitHub Actions.

## Struktura repo

```
za-oknem/
├── CLAUDE.md
├── apps/{mobile,api}/
├── packages/{api-contract,config}/
├── infrastructure/{docker,caddy,scripts}/
├── docs/{architecture,api,data,privacy,release,tasks}/
└── .github/workflows/
```

## Workflow

Nie dostajesz polecenia "zbuduj całą aplikację". Pracujemy task po tasku:
PROJECT SPEC → PHASE → TASK → IMPLEMENT → TEST → REVIEW → COMMIT → NEXT TASK.

Każdy task ma: Goal, Scope, Acceptance Criteria, Tests, Non-goals, Dependencies,
Data Contract, Security, Architecture Impact. Task jest Done, gdy: implementacja działa,
acceptance criteria spełnione, testy i lint/typecheck przechodzą, dokumentacja aktualna,
brak scope creep, commit jest logiczny i mały.

Git: feature branch → PR → main. `main` = production-ready. Nie omijaj hooków/testów.

Po każdym zmergowanym PR aktualizuj `docs/ROADMAP.md` (punktowo — nowy status
✅/🟡/⛔/⬜ tam gdzie coś się zmieniło, nowy wiersz w historii PR), nie tylko
kod/testy/ADR. To jedyne miejsce, gdzie użytkownik śledzi postęp projektu
na bieżąco.

## Czego NIE robić bez pytania

- Nie dodawaj zależności bez uzasadnienia w PR.
- Nie twórz connectora poza strukturą `connectors/<source>/` z kontraktem
  `fetch / parse / validate / normalize`.
- Nie wprowadzaj mikroserwisów, mapy, kont użytkowników, PWA, Green Index — to poza MVP
  (sekcja 11 Master Planu).
- Nie zmieniaj providera pogody/pyłków bez aktualizacji ADR-001 i Source Registry.
- Nie publikuj/nie włączaj monetyzacji (reklamy, subskrypcje/premium, Patronite) bez pytania — patrz
  ADR-003 i ADR-031. Reklamy i płatne/premium funkcje wymagają PRZED włączeniem planu komercyjnego
  Open-Meteo (`docs/release/business-gates.md`); darowizny na Free dozwolone, ale to decyzja właściciela.

## Pierwszy cel: Vertical Slice

GIOŚ → Connector → PostgreSQL → FastAPI → React Native → PM2.5 na ekranie.
To ważniejsze niż UI, niż kolejne connectory, niż mapa. Dopóki to nie działa end-to-end,
nie rozjeżdżamy się w wiele kierunków naraz.
