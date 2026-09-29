# TASK 1.1 — Backup (PostgreSQL + config + sekrety), off-VPS, z testem odtworzenia

## Goal

§68 Master Planu: backup obejmuje PostgreSQL + konfigurację + kluczowe dane, przechowywany
POZA VPS, z regularnym automatycznym testem odtworzenia — "sam backup bez testu odtworzenia
nie jest wystarczający". Priorytet przed jakimkolwiek wdrożeniem produkcyjnym (rule z
CLAUDE.md), niezależnie od tego, czy reszta MVP jest gotowa.

## Scope

- `infrastructure/scripts/backup.sh` — dla jednego przebiegu:
  1. `pg_dump` bazy w formacie custom (`-Fc`, kompresja wbudowana).
  2. Tar plików konfiguracyjnych BEZ sekretów (`docker-compose.yml`, `.env.example`,
     `infrastructure/caddy/Caddyfile` jeśli istnieje).
  3. Zaszyfrowany (`age`) tar realnych sekretów (`.env`) — osobny artefakt, bo rule #3
     (żadnych sekretów w repo) nie zwalnia z ich backupu, tylko zabrania trzymać jawnie.
  4. Upload wszystkich trzech artefaktów przez `rclone` do zdalnego katalogu
     (`BACKUP_REMOTE`, np. `s3:za-oknem-backups` albo dowolny inny rclone remote) —
     świadomie przez rclone, nie własny kod S3, żeby nie przywiązywać się do jednego
     providera (ADR nie wymagane — to wybór narzędzia operacyjnego, nie architektury).
  5. Nazwy plików ze znacznikiem czasu (retencja = polityka na remote, np. lifecycle
     rule w buckecie — nie w tym skrypcie).
- `infrastructure/scripts/restore_test.sh` — pobiera NAJNOWSZY backup z `BACKUP_REMOTE`,
  odtwarza `pg_dump` do jednorazowej bazy (`za_oknem_restore_test`), odszyfrowuje i
  rozpakowuje config, i weryfikuje smoke-checkiem (baza ma oczekiwane tabele + `SELECT 1`
  przechodzi). Exit code ≠ 0 przy jakimkolwiek kroku, żeby dało się to wpiąć w
  monitoring/cron (realne wdrożenie w harmonogramie — TASK-15.2/15.3, poza zakresem
  tego tasku).
- `infrastructure/scripts/README.md` — jak uruchomić, wymagane zmienne środowiskowe,
  wymagane narzędzia (`postgresql-client`, `rclone`, `age`).
- `.env.example` — dodane (puste) placeholdery `BACKUP_REMOTE`, `AGE_RECIPIENT`
  (klucz publiczny do szyfrowania — nie sekret, bez sekretu nie da się jedynie
  odszyfrować).

## Non-goals

- Realne, zaplanowane uruchamianie na produkcyjnym VPS (cron/systemd timer) — to
  TASK-15.2 (Phase 15, dopiero gdy istnieje środowisko produkcyjne).
- Wybór konkretnego providera off-VPS storage (S3-compatible, Backblaze B2, inny VPS)
  — decyzja biznesowa użytkownika, skrypt jest storage-agnostic przez rclone.
- Monitoring/alerting przy nieudanym backupie — TASK-13.2/15.3.

## Acceptance Criteria

- [ ] `backup.sh` uruchomiony lokalnie (dev `docker compose`) produkuje 3 pliki:
      dump bazy, tar configu, zaszyfrowany tar sekretów.
- [ ] Bez ustawionego `BACKUP_REMOTE` skrypt kończy się czytelnym błędem (nie cichym
      pominięciem uploadu) — rule "nie zgadywać, jawny błąd".
- [ ] `restore_test.sh` przeciwko lokalnemu rclone remote (katalog na dysku — symulacja
      "off-VPS" do testów, realny provider to decyzja produkcyjna) odtwarza dump do
      `za_oknem_restore_test` i przechodzi smoke-check.
- [ ] Żaden sekret nie trafia do repo ani do nieszyfrowanego artefaktu configu.
- [ ] `infrastructure/scripts/README.md` opisuje pełen przepływ + wymagane narzędzia.

## Tests

- `infrastructure/scripts/test_backup_restore.sh` — ponytail-style self-check: pełny
  cykl backup→restore_test przeciwko dev `docker compose` Postgresowi i lokalnemu
  katalogowi jako rclone remote, `set -e` + asercja że przywrócona baza ma te same
  tabele co źródłowa. Uruchamiane ręcznie (`bash infrastructure/scripts/test_backup_restore.sh`),
  nie wpięte w CI (wymaga działającego `docker compose`, jak inne testy integracyjne
  w tym repo).

## Dependencies

Brak (Phase 1, niezależny od reszty MVP — zgodnie z priorytetem z CLAUDE.md).

## Data Contract

Brak zmian schematu bazy — to czysto operacyjne skrypty, żadnych migracji Alembic.

## Security

- Sekrety (`.env`) **i dump bazy** nigdy nie trafiają na zdalny storage w formie
  jawnej — zawsze przez `age -r $AGE_RECIPIENT` (asymetryczne szyfrowanie, prywatny
  klucz nie musi istnieć na VPS, który robi backup — tylko na maszynie, która kiedyś
  odtwarza). Dump bazy jest tak samo wrażliwy jak `.env` (pełny model danych, docelowo
  też identyfikatory urządzeń/tokeny push) — korekta po review (LucTroosh), w
  pierwszej wersji szyfrowane były tylko sekrety.
- `restore_test.sh` **wymaga prywatnego klucza** (`AGE_IDENTITY`), więc musi działać
  na osobnym, izolowanym hoście weryfikacyjnym — nigdy na backupującym VPS, który tego
  klucza nie posiada i nie powinien.
- Brak `.env` przy backupie jest domyślnie twardym błędem (nie cichym pominięciem) —
  tylko jawny `BACKUP_ALLOW_NO_SECRETS=1` (dev/self-check) go dopuszcza.
- `restore_test.sh` działa na jednorazowej, odizolowanej bazie (`_restore_test`
  sufiks, domyślnie z losowym komponentem w nazwie), nigdy nie nadpisuje bazy
  produkcyjnej — i nigdy nie usuwa istniejącej bazy PRZED utworzeniem (tylko po
  zakończeniu testu, i tylko bazę faktycznie utworzoną przez ten przebieg).
- Smoke-check porównuje liczby wierszy per tabela i wersję migracji zapisane w
  manifeście z backupu z tym, co faktycznie odtworzyło się w bazie testowej — nie
  tylko istnienie tabel.
- Manifest i dump pochodzą z jednej, wspólnej migawki bazy (`pg_export_snapshot`
  w transakcji `REPEATABLE READ`, `pg_dump --snapshot=...`), nie z dwóch osobnych
  odczytów w różnym czasie — korekta po review (LucTroosh), pierwsza wersja liczyła
  wiersze (i `alembic_version`) osobnymi zapytaniami PO `pg_dump`, więc współbieżny
  insert/delete/migracja dawały fałszywą rozbieżność mimo poprawnego backupu.
- `pg_dump` jest pipe'owany prosto do `age` w jednym poleceniu (`\!` wewnątrz
  transakcji snapshotu) — plaintext bazy NIGDY nie dotyka dysku, tak samo jak
  `.env` niżej. Wcześniejsza wersja (przy okazji dodawania spójnej migawki) pisała
  najpierw plaintext do pliku tymczasowego, potem szyfrowała osobno — realne okno,
  w którym cały zrzut produkcyjnej bazy leżał jawnie na dysku (LucTroosh review
  [P2], zauważone od razu, korekta w tym samym PR).
- `DATABASE_URL` nigdy nie jest wstawiany jako tekst do polecenia `\!` (`\!`
  uruchamia je w NOWEJ powłoce — psql docs) — hasło zawierające `$`/`` ` `` w URI
  zostałoby ponownie zinterpretowane przez tę drugą powłokę (command injection).
  Zamiast tego eksportujemy `DATABASE_URL` jako zmienną środowiskową i w treści
  polecenia `\!` odwołujemy się do niej po nazwie (`$PG_DATABASE_URL`) — druga
  powłoka podstawia wartość raz, ze swojego środowiska, bez ponownego parsowania
  jej zawartości jako kodu (LucTroosh review [P1]; zweryfikowane bezpośrednio: hasło
  `x$(touch ...)y` faktycznie wykonywało `touch` w starym wzorcu, nie wykonuje go
  w obecnym).
- `\!` nie przerywa skryptu przy błędzie polecenia powłoki (`ON_ERROR_STOP=1`
  dotyczy tylko błędów SQL) — `backup.sh` jawnie sprawdza po transakcji, że
  zaszyfrowany dump istnieje i nie jest pusty, żeby cichy błąd `pg_dump`/`age`
  wewnątrz `\!` nie skończył się uploadem brakującego/pustego/nieodszyfrowywalnego
  backupu jako "sukces".

## Architecture Impact

Brak — rule #12 nie dotyczy (skrypty operacyjne, nie zmiana stacku/schematu/kontraktu).
