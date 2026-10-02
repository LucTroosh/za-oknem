# Wdrożenie na VPS — runbook (zestaw gotowy, jeszcze niewdrożony)

Stan: **nic nie jest wdrożone** (brak VPS). Ten dokument + `docker-compose.prod.yml`, `.env.prod.example`
i `infrastructure/caddy/Caddyfile` to zestaw, który skraca wdrożenie do kilkudziesięciu minut, kiedy VPS
będzie kupiony. **Niezweryfikowane na prawdziwym serwerze**: plik compose przeszedł statyczną walidację
(`docker compose config`), a `Caddyfile` nie był uruchamiany (brak demona dockera w środowisku przygotowania).
Stack wg CLAUDE.md: Ubuntu 24.04 + Docker + Caddy; scheduler w tym samym obrazie (ADR-007); Redis nie jest
jeszcze używany przez kod, więc nie jest w produkcyjnym compose.

## 0. Przed wdrożeniem (decyzje właściciela)
- Wybór VPS i kraju hostingu (wpisać do polityki prywatności, `docs/privacy/privacy-policy-draft.md` rozdz. 6).
- Domena API (np. `api.twojadomena.pl`) i dostęp do jej DNS.
- Gate: wdrożenie publiczne = wszystkie źródła `APPROVED` w `source-registry.md` (TASK-15.0). Reklamy i płatne
  funkcje: `docs/release/business-gates.md`.

## 1. Serwer (jednorazowo)
```
# Ubuntu 24.04, użytkownik z sudo, klucz SSH
sudo apt update && sudo apt -y upgrade
sudo apt -y install docker.io docker-compose-v2 ufw git
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable
```
Rekord DNS: `A api.twojadomena.pl -> IP VPS` (Caddy potrzebuje go do certyfikatu).
Baza **nie** wystawia portu na świat (w produkcyjnym compose nie ma `ports` dla Postgresa).

## 2. Kod i konfiguracja
```
git clone https://github.com/LucTroosh/za-oknem.git && cd za-oknem
cp .env.prod.example .env.prod
nano .env.prod        # API_DOMAIN, POSTGRES_PASSWORD (+ to samo hasło w DATABASE_URL), opcjonalnie backup
```
`.env.prod` jest w `.gitignore` i nie może trafić do repo.

## 3. Start
```
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml ps
```
Krok `migrate` stosuje migracje Alembic (reguła #4) przed startem `api` i `scheduler`. Certyfikat HTTPS Caddy
pobiera sam przy pierwszym żądaniu (port 80 musi być otwarty).

## 4. Dane początkowe
```
docker compose -f docker-compose.prod.yml exec api python -m app.connectors.geonames_places.ingest --download
docker compose -f docker-compose.prod.yml exec api python -c "from app.scheduler import run_gios; print(run_gios())"
docker compose -f docker-compose.prod.yml exec api python -m app.connectors.open_meteo_pollen.ingest
```
(`scheduler` odpytuje źródła sam; ręczne uruchomienia tylko przyspieszają pierwsze dane. GIOŚ uruchamiamy tą samą funkcją co scheduler — `gios.ingest` bez argumentów wymaga `--station-id` i obsługuje jedną stację.) Opcjonalnie granice
gmin: `docs/data/prg-import.md`.

## 5. Test po wdrożeniu
Z dowolnego komputera:
```
python3 infrastructure/scripts/smoke_data.py wroclaw https://api.twojadomena.pl
curl -sI https://api.twojadomena.pl/api/v1/health | head -3
```
Oczekiwane: smoke test bez FAIL, HTTP 200, nagłówek `Strict-Transport-Security`.

## 6. Backup
Wg `infrastructure/scripts/README.md` (`backup.sh` w cronie, `restore_test.sh` na osobnej maszynie). Wymaga
`rclone` i `age` oraz celu poza VPS (decyzja biznesowa).

## 7. Aktualizacja
```
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
Migracje stosują się same. Przy błędzie: `docker compose -f docker-compose.prod.yml logs --tail 100 api migrate`.

## 8. Aplikacja mobilna na produkcję
- Profil `preview` w `eas.json` dopuszcza HTTP tylko do testów w sieci lokalnej. Do wydania trzeba profilu
  `production` z `EXPO_PUBLIC_API_URL=https://api.twojadomena.pl` (bez cleartext; `app.config.js` już
  włącza cleartext tylko dla `preview`). Do dodania przy pierwszym buildzie produkcyjnym.
- Przed Google Play: polityka prywatności pod stałym adresem https i formularz „Bezpieczeństwo danych”.

## Prywatność
Caddy nie zapisuje access logów (brak dyrektywy `log`), a API startuje z `--no-access-log`, więc parametr
wyszukiwania miejscowości (`/places?q=`) nie trafia na dysk. Jeśli kiedykolwiek włączysz logi, obetnij query
string i ustaw krótką retencję oraz zaktualizuj politykę prywatności.
