# Za Oknem

Lokalny agregator danych środowiskowych dla Polski. Pełna specyfikacja:
[`docs/architecture/Development-Master-Plan-v1.2.md`](docs/architecture/Development-Master-Plan-v1.2.md).
Zasady pracy nad kodem: [`CLAUDE.md`](CLAUDE.md).

## Uruchomienie lokalne

```bash
cp .env.example .env
docker compose up --build
```

Sprawdź: `curl http://localhost:8000/api/v1/health` → `{"status": "ok"}`.

Migracje bazy (po `docker compose up`, w osobnym terminalu):

```bash
cd apps/api
uv sync --dev
uv run alembic upgrade head
```

### Mobile (Expo)

```bash
cd apps/mobile
npm install
npm start
```

Domyślnie łączy się z `http://localhost:8000`. Na emulatorze Androida ustaw
`EXPO_PUBLIC_API_URL=http://10.0.2.2:8000`, na fizycznym urządzeniu — LAN IP hosta.

## Status implementacji

TASK-0.1 (repository foundation) — patrz `docs/tasks/TASK-0.1-repository-foundation.md`
dla pełnych acceptance criteria.

**Nie zweryfikowane w tej sesji:** `docker compose up`, `alembic upgrade head` i
`npm install` nie zostały odpalone end-to-end przeze mnie — środowisko, w którym
pisałem ten kod, ma zablokowany dostęp do PyPI i npm registry (polityka sieciowa
sesji, potwierdzone bezpośrednim testem, nie zgaduję). Kod jest napisany starannie
i zgodnie ze standardowymi wzorcami (FastAPI/Alembic/Expo Router), ale **pierwsza
realna weryfikacja to Twoje `docker compose up` lokalnie albo zielone CI na GitHubie**
(GitHub Actions ma pełny dostęp do sieci, w przeciwieństwie do tej sesji) — dopóki
jedno z nich nie przejdzie, TASK-0.1 nie jest formalnie Done.
