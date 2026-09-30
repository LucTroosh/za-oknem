# TASK 1.1 — Backup (PostgreSQL + config + sekrety), off-VPS, z testem odtworzenia

## Goal

§68 Master Planu: backup obejmuje PostgreSQL + konfigurację + kluczowe dane, przechowywany
POZA VPS, z regularnym automatycznym testem odtworzenia — "sam backup bez testu odtworzenia
nie jest wystarczający". Priorytet przed jakimkolwiek wdrożeniem produkcyjnym (rule z
CLAUDE.md), niezależnie od tego, czy reszta MVP jest gotowa.

## Scope

- `infrastructure/scripts/backup.sh` — jeden przebieg:
  1. Jedna transakcja `REPEATABLE READ` + `pg_export_snapshot()`; w niej
     `pg_dump -Fc --snapshot=…` pipe'owany prosto do `age` (plaintext nigdy nie na
     dysku) oraz `alembic_version` i liczby wierszy tabel — dump i manifest opisują
     identyczny stan bazy.
  2. Tar configu BEZ sekretów (`docker-compose.yml`, `.env.example`, Caddyfile jeśli jest).
  3. Zaszyfrowany (`age`) tar `.env` — brak `.env` to twardy błąd (poza jawnym
     `BACKUP_ALLOW_NO_SECRETS=1` dla dev/self-check).
  4. `manifest-<STAMP>.txt`: nazwy artefaktów, `alembic_version`, `table_count.*`
     (wartości walidowane — pusty odczyt przerywa backup, nie zamienia się w 0).
  5. Upload przez `rclone` w kolejności config → sekrety → manifest → dump (dump
     ostatni = sygnał kompletnego zestawu). `STAMP` = czas UTC + 4 losowe bajty.
- `infrastructure/scripts/restore_test.sh` — na izolowanym hoście z kluczem
  prywatnym: wybiera najnowszy dump, odrzuca backup starszy niż
  `BACKUP_MAX_AGE_HOURS` (domyślnie 48h), weryfikuje config (wymagane pliki),
  manifest (kompletny, liczby całkowite) i sekrety (odszyfrowanie + obecność
  `.env`), odtwarza strumieniowo (`age -d | pg_restore`) do jednorazowej bazy
  `*_restore_test` (losowa nazwa, nigdy nie usuwa istniejącej bazy przed
  utworzeniem, sprząta własną po zakończeniu), porównuje `alembic_version` i liczby
  wierszy z manifestem. Każdy błąd = exit ≠ 0 z czytelnym komunikatem (pod cron/
  monitoring).
- `infrastructure/scripts/_pgpass.sh` — hasło z `DATABASE_URL` do `PGPASSFILE`
  (0600), nigdy w argv procesów.
- `infrastructure/scripts/README.md`, placeholdery w `.env.example`.
- Retencja: po stronie storage (np. lifecycle rule bucketu usuwająca obiekty
  starsze niż N dni) — działa na cały zestaw jednocześnie, bo wszystkie artefakty
  jednego backupu mają ten sam `STAMP`/czas utworzenia.

## Non-goals

- Zaplanowane uruchamianie na produkcyjnym VPS (cron/systemd) — TASK-15.2.
- Wybór providera off-VPS storage — decyzja biznesowa; skrypty są storage-agnostic.
- Monitoring/alerting nieudanego backupu — TASK-13.2/15.3 (exit code jest gotowy).

## Acceptance Criteria

- [x] `backup.sh` produkuje: zaszyfrowany dump, tar configu, zaszyfrowany tar
      sekretów, manifest.
- [x] Brak `BACKUP_REMOTE` / `AGE_RECIPIENT` / `.env` (bez flagi dev) → czytelny błąd.
- [x] `restore_test.sh` przeciwko lokalnemu katalogowi jako remote odtwarza dump i
      przechodzi weryfikację względem manifestu.
- [x] Negatywne przypadki kończą się błędem z komunikatem: awaria `pg_dump`
      (brak uploadu), uszkodzony dump, config bez wymaganych plików, manifest
      ucięty/bez linii/bez `alembic_version`, backup starszy niż limit, rozbieżne
      liczniki.
- [x] Żaden sekret w repo, w nieszyfrowanym artefakcie ani w argv procesów;
      hasło z `$`/`` ` ``/`:` nie powoduje wstrzyknięcia polecenia.
- [x] README opisuje pełen przepływ i wymagane narzędzia.

## Tests

- `infrastructure/scripts/test_backup_restore.sh` — pełny cykl backup →
  restore_test przeciw dev Postgresowi i lokalnemu katalogowi jako remote
  (uruchamiany ręcznie, wymaga `docker compose` — jak inne testy integracyjne).
- Zweryfikowane na Postgres 16 (scram-sha-256): wszystkie przypadki z Acceptance
  Criteria, w tym symulowana awaria `pg_dump`, insert w trakcie backupu (manifest
  = stan migawki), argv logowane shimami, `PGPASSWORD` ustawione na złą wartość.

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
  backupu jako "sukces". `pg_dump | age` działa w helperze z `set -o pipefail`,
  a sukces sygnalizuje wyłącznie marker tworzony na końcu helpera — sam niepusty
  plik nie wystarcza, bo `age` potrafi zaszyfrować ucięty strumień po błędzie
  `pg_dump` (LucTroosh review [P1], zweryfikowane symulowaną awarią pg_dump).
- `restore_test.sh` sprawdza obecność `docker-compose.yml` i `.env.example` w
  archiwum config, nie tylko poprawność kontenera tar.gz.
- Hasło bazy nigdy nie trafia do argv (`ps`/`/proc/*/cmdline` są czytelne dla
  wszystkich użytkowników hosta): `_pgpass.sh` przenosi je z `DATABASE_URL`
  (userinfo albo `?password=`) do pliku `PGPASSFILE` z uprawnieniami 600 w
  prywatnym katalogu tymczasowym, a `psql`/`pg_dump`/`pg_restore` dostają URL bez
  hasła (LucTroosh review [P2]; zweryfikowane shimami logującymi argv każdego
  wywołania przy auth scram-sha-256). `PGPASSWORD` jest wtedy czyszczone (libpq
  preferuje je przed passfile).
- `restore_test.sh` odszyfrowuje dump strumieniowo do `pg_restore` — plaintext nie
  trafia na dysk także na hoście weryfikacyjnym.
- Manifest musi być kompletny: brakujący/pusty licznik lub `alembic_version` to
  błąd, nie domyślne 0 (tabela legalnie pusta przeszłaby inaczej porównanie).
- Najnowszy backup starszy niż `BACKUP_MAX_AGE_HOURS` to błąd — test odtworzenia
  nie może świecić na zielono, gdy backupy przestały się wykonywać.

## Architecture Impact

Brak — rule #12 nie dotyczy (skrypty operacyjne, nie zmiana stacku/schematu/kontraktu).
