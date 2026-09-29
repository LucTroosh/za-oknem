# Za Oknem

Lokalny agregator danych środowiskowych dla Polski. Pełna specyfikacja:
[`docs/architecture/Development-Master-Plan-v1.2.md`](docs/architecture/Development-Master-Plan-v1.2.md).
Zasady pracy nad kodem: [`CLAUDE.md`](CLAUDE.md).

## Szybki test dzisiaj

Minimalna ścieżka od zera do PM2.5 + pogody na ekranie telefonu/emulatora:

```bash
cp .env.example .env
docker compose up --build -d

cd apps/api
uv sync --dev
uv run alembic upgrade head

python -m app.connectors.gios.ingest --list          # znajdź --station-id blisko siebie
python -m app.connectors.gios.ingest --station-id 38
python -m app.connectors.open_meteo.ingest            # wszystkie geo_areas (seed ADR-005)

curl http://localhost:8000/api/v1/dashboard/latest    # powinno zwrócić air + weather
```

Jeśli `dashboard.air` jest `null` dla Twojej lokalizacji — najbliższa stacja GIOŚ
jest dalej niż 50 km (ADR-006, próg celowo konserwatywny) albo nie zrobiłeś
ingestu dla stacji w pobliżu.

```bash
cd apps/mobile
npm install
npm start
```

Zobacz sekcję "Fizyczne urządzenie" niżej, jeśli testujesz na realnym telefonie, nie
w emulatorze.

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

### Ingest danych (manualny, Phase 4/5 — scheduler to osobny task)

```bash
docker compose exec api python -m app.connectors.gios.ingest --list
docker compose exec api python -m app.connectors.gios.ingest --station-id 38

docker compose exec api python -m app.connectors.open_meteo.ingest
docker compose exec api python -m app.connectors.open_meteo.ingest --slug klodzko
```

`open_meteo.ingest` bez flag ładuje pogodę dla wszystkich wierszy w `geo_areas`
(seed z ADR-005). Zgodnie z ADR-004 docelowy scheduler ma odpytywać co 3h — nie
częściej.

### Mobile (Expo)

```bash
cd apps/mobile
npm install
npm start
```

Domyślnie łączy się z `http://localhost:8000`. Na emulatorze Androida ustaw
`EXPO_PUBLIC_API_URL=http://10.0.2.2:8000`, na fizycznym urządzeniu — LAN IP hosta
(patrz niżej). Zobacz `.env.example` w `apps/mobile/`.

#### Fizyczne urządzenie (Android, Expo Go)

Trzy rzeczy, które inaczej kosztują długą sesję debugowania:

1. **Wersja Expo Go musi zgadzać się z SDK projektu** (obecnie SDK 52). Wersja ze
   Sklepu Play bywa nowsza i wtedy aplikacja się nie uruchomi ("Project is
   incompatible..."). Zainstaluj właściwą wersję ze strony:
   `https://expo.dev/go?sdkVersion=52&platform=android&device=true`.
2. **`localhost` na telefonie to sam telefon**, nie Twój komputer. Ustaw
   `EXPO_PUBLIC_API_URL` na adres LAN komputera (np. `http://192.168.1.42:8000`),
   znajdziesz go przez `ipconfig getifaddr en0` (macOS Wi-Fi) / `hostname -I`
   (Linux). Telefon i komputer muszą być w tej samej sieci Wi-Fi (nie dane
   komórkowe). Szybki test bez Expo: otwórz ten adres w przeglądarce na telefonie
   — jeśli tam też nie działa, problem jest sieciowy/firewall, nie w aplikacji.
3. **Zmiana `EXPO_PUBLIC_*` wymaga czyszczenia cache**, bo wartość jest wypiekana
   w bundlu JS przy starcie: `npx expo start -c`, a na telefonie całkowicie zamknij
   i otwórz Expo Go od nowa (samo "reload" nie wystarczy).

## Status implementacji

TASK-0.1 (repository foundation) — patrz `docs/tasks/TASK-0.1-repository-foundation.md`.
Phase 4, pierwszy vertical slice (GIOŚ → connector → PostgreSQL → FastAPI →
React Native → PM2.5 na ekranie) zweryfikowany end-to-end na żywym API i fizycznym
urządzeniu Android — patrz `docs/architecture/Development-Master-Plan-v1.2.md` §107.
