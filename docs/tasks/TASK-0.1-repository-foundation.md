# TASK 0.1 — Repository Foundation

## Goal

Założyć monorepo `za-oknem` z minimalnym szkieletem mobile + backend + infra + docs,
zgodnie ze strukturą z Master Planu (§16), tak żeby kolejne taski (Phase 1+) miały
gdzie wchodzić bez decyzji strukturalnych po drodze.

## Scope

- Repozytorium GitHub (prywatne), gałąź `main`.
- Struktura katalogów: `apps/mobile`, `apps/api`, `packages/api-contract`,
  `packages/config`, `infrastructure/{docker,caddy,scripts}`, `docs/{architecture,
  api,data,privacy,release,tasks}`, `.github/workflows`.
- `CLAUDE.md` w root (wersja z tego pakietu).
- `docs/architecture/Development-Master-Plan-v1.2.md` (po zatwierdzeniu przez
  użytkownika) + `ADR-001`, `ADR-002`, `ADR-003`.
- `apps/api`: szkielet FastAPI (Poetry lub uv), `GET /api/v1/health` zwraca 200,
  Alembic zainicjalizowany (pusta migracja bazowa), pydantic-settings do configu
  z env vars.
- `apps/mobile`: szkielet Expo + TypeScript + Expo Router, jeden ekran Home
  wywołujący `/api/v1/health` i wyświetlający status.
- `docker-compose.yml` (development): PostgreSQL+PostGIS, Redis, api.
- `.env.example` dla development (bez sekretów).
- CI: GitHub Actions — lint + typecheck na PR (backend: ruff/mypy; mobile: eslint/tsc).
- README.md z instrukcją uruchomienia lokalnie (`docker compose up`, `expo start`).

## Acceptance Criteria

- [ ] `docker compose up` lokalnie podnosi Postgres+PostGIS, Redis i API.
- [ ] `GET /api/v1/health` zwraca 200 z backendu w kontenerze.
- [ ] Expo app łączy się z lokalnym API i renderuje status z `/health`.
- [ ] Alembic `alembic upgrade head` przechodzi na czystej bazie (nawet bez modeli
      domenowych — sama infrastruktura migracji).
- [ ] CI (lint+typecheck) przechodzi na PR do `main`.
- [ ] `CLAUDE.md` i ADR-y są w repo pod właściwymi ścieżkami.
- [ ] Brak sekretów w repo (`.env` w `.gitignore`, tylko `.env.example` w repo).

## Tests

- Manualny smoke test: `docker compose up` → curl `/api/v1/health` → 200.
- CI zielony na pustym PR (weryfikacja, że pipeline w ogóle się odpala).

## Non-goals

- Żaden connector źródła danych (GIOŚ dopiero w Phase 4).
- Żaden model domenowy (measurements/forecasts/alerts) — to Phase 2/3.
- Żadne UI poza jednym ekranem-smoke-testem.
- VPS/staging/production (Phase 1/15) — tu tylko local dev.

## Dependencies

Brak (pierwszy task). Blokuje wszystkie kolejne fazy.

## Data Contract

`GET /api/v1/health` → `{"status": "ok"}` (200). Brak innych kontraktów na tym etapie.

## Security

- `.env` nigdy w repo. `.env.example` bez realnych wartości.
- CORS na backendzie ograniczony do originu Expo dev (localhost) w development.

## Architecture Impact

Brak zmian architektury — to jest jej pierwsze materialne wdrożenie zgodnie z Master
Planem v1.2 i ADR-001/002/003. Jeśli podczas realizacji pojawi się potrzeba odejścia
od któregoś z tych dokumentów, zatrzymaj się i zgłoś to zamiast implementować "przy okazji".
