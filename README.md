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
python -m app.connectors.open_meteo.ingest            # obszary z weather_polling_active (ADR-019); --slug wymusza wybrane
python -m app.connectors.imgw_hydro.ingest            # wszystkie stacje hydro, jednym wywołaniem
python -m app.connectors.imgw_warningshydro.ingest    # ostrzeżenia hydrologiczne (Alert, ADR-009)

curl http://localhost:8000/api/v1/dashboard/latest    # powinno zwrócić air + weather
curl http://localhost:8000/api/v1/hydro/latest        # stan wody, osobny endpoint (ADR-008)
curl http://localhost:8000/api/v1/alerts/latest       # aktywne ostrzeżenia, osobny endpoint (ADR-009)
```

Jeśli `dashboard.air` jest `null` dla Twojej lokalizacji — najbliższa stacja GIOŚ
jest dalej niż 50 km (ADR-006, próg celowo konserwatywny) albo nie zrobiłeś
ingestu dla stacji w pobliżu.

**Automatyczne odświeżanie zamiast ręcznego ingestu** (ADR-007): ustaw
`GIOS_STATION_IDS=38,42` (Twoje stacje, przecinkami) w `.env`, potem
`docker compose up scheduler` — pętla sama woła `open_meteo` co 3h, `gios` co 1h,
`imgw_hydro` co 1h i `imgw_warningshydro` co 1h (wszystkie stacje/ostrzeżenia, bez
konfiguracji), bez ręcznego CLI. Ustawione `GIOS_STATION_IDS` = override: dokładnie te
stacje. Puste = scheduler sam wybiera dla każdego aktywnego obszaru najbliższą stację
GIOŚ w promieniu 50 km z katalogu zapisanego w bazie (odświeżanego raz na dobę, ADR-025);
brak obszarów albo stacji w zasięgu = GIOŚ pominięty (jawnie loguje).

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

### Ingest danych (manualny; automatyczny wariant — `docker compose up scheduler`, ADR-007)

```bash
docker compose exec api python -m app.connectors.gios.ingest --list
docker compose exec api python -m app.connectors.gios.ingest --station-id 38

docker compose exec api python -m app.connectors.open_meteo.ingest
docker compose exec api python -m app.connectors.open_meteo.ingest --slug klodzko

docker compose exec api python -m app.connectors.imgw_hydro.ingest
docker compose exec api python -m app.connectors.imgw_warningshydro.ingest
```

`open_meteo.ingest` bez flag ładuje pogodę dla wierszy `geo_areas` z
`weather_polling_active` (seed z ADR-005; zaimportowane gminy — nie, ADR-019;
`--slug` wybiera konkretny obszar niezależnie od flagi), `imgw_hydro.ingest` — analogicznie, dla wszystkich stacji
hydrologicznych IMGW (jedno wywołanie API, bez flag do wyboru stacji — ADR-008).
`imgw_warningshydro.ingest` — ostrzeżenia hydrologiczne, tym samym wzorcem
jednego wywołania bez flag (Alert, nie Measurement — rule #7, ADR-009).

### Rejestr miejscowości (wybór dowolnej miejscowości, ADR-029)

Jednorazowo i potem np. raz na kwartał, na maszynie z dostępem do internetu (produkcyjny VPS):

```bash
docker compose exec api python -m app.connectors.geonames_places.ingest --download
# albo z własnego pliku: ... --file /data/PL.zip --admin1-file ... --admin2-file ...
# podgląd bez bazy: ... --download --validate-only --sample Gliwice
```

Źródło: GeoNames (CC BY 4.0, atrybucja w odpowiedziach `/places`), URL bazowy w
`GEONAMES_BASE_URL`. Bez importu `GET /api/v1/places` zwraca pustą listę.

### Mobile (Expo)

```bash
cd apps/mobile
npm install
npm start
```

Pierwsze uruchomienie: Welcome → „Ustaw lokalizację” → Start (kolejne uruchomienia od razu
Start). Wybrana miejscowość jest zapamiętana tylko na urządzeniu (AsyncStorage); zmienisz ją
tapem w nazwę miejscowości na Start albo w Ustawieniach → Lokalizacja. Żeby przejść ekran
lokalizacji od zera, wyczyść dane aplikacji (Android: Ustawienia → Aplikacje → Expo Go →
Pamięć → Wyczyść dane) albo odinstaluj ją.

**Miejscowości w lokalnym stacku.** Wyszukiwarka czyta `GET /api/v1/places`, a ta tabela jest
pusta, dopóki nie zaimportujesz GeoNames (wyszukiwanie zwraca wtedy „Nie znaleziono…”, a pod
polem są „Większe miasta” z `GET /api/v1/areas`, więc ekran nadal działa). Import (komenda z
sekcji „Rejestr miejscowości”, ADR-029; wymaga internetu, na VPS albo lokalnie):

```bash
docker compose exec api python -m app.connectors.geonames_places.ingest --download
```

Aplikacja ma trzy zakładki (Start / Alerty / Ustawienia) i podąża za jasnym/ciemnym
motywem systemu (przełącz go w ustawieniach telefonu lub emulatora, bez restartu).
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
