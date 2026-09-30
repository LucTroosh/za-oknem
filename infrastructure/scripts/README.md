# scripts

## Backup / Restore Test (TASK-1.1, §68 Master Planu)

PostgreSQL + konfiguracja + sekrety, przechowywane POZA VPS, z automatycznym testem
odtworzenia. Szczegóły zakresu: `docs/tasks/TASK-1.1-backup.md`.

### Wymagane narzędzia

- `postgresql-client` (`pg_dump`, `pg_restore`, `psql`)
- [`rclone`](https://rclone.org/) — storage-agnostic upload (S3, B2, SFTP, lokalny
  katalog do testów...); realny remote konfigurowany przez `rclone config` na VPS,
  nazwa/provider to decyzja biznesowa użytkownika, nie tego skryptu.
- [`age`](https://github.com/FiloSottile/age) — szyfrowanie dumpa bazy i sekretów
  przed uploadem.

### Zmienne środowiskowe

| Zmienna | Opis |
|---|---|
| `DATABASE_URL` | Connection string do produkcyjnej bazy (backup.sh) / do instancji Postgres, na której robimy restore test (restore_test.sh) — nazwa bazy w nim jest ignorowana przy tworzeniu bazy testowej. |
| `BACKUP_REMOTE` | Cel `rclone` (np. `s3:za-oknem-backups`, albo zwykła ścieżka na dysku do testów lokalnych). |
| `AGE_RECIPIENT` | Publiczny klucz `age` — szyfruje **dump bazy i sekrety** przed uploadem (`backup.sh`). `age-keygen` generuje parę; prywatny klucz NIE musi istnieć na VPS, który robi backup. |
| `AGE_IDENTITY` | (`restore_test.sh`) Ścieżka do prywatnego klucza `age` — wymagany, bo dump i sekrety są szyfrowane. **Uruchamiaj `restore_test.sh` na izolowanym hoście weryfikacyjnym, który ten klucz przechowuje — nigdy na backupującym VPS.** |
| `BACKUP_ALLOW_NO_SECRETS` | (opcjonalnie, `backup.sh`) `1` pozwala pominąć artefakt sekretów, gdy `.env` naprawdę nie istnieje — tylko dev/self-check. Na produkcji brak `.env` jest twardym błędem. |
| `BACKUP_MAX_AGE_HOURS` | (opcjonalnie, `restore_test.sh`) maksymalny wiek najnowszego backupu, domyślnie `48` — starszy = błąd (backupy przestały się wykonywać). |
| `RESTORE_TEST_DB` | (opcjonalnie) nazwa jednorazowej bazy do testu odtworzenia, domyślnie losowa (`za_oknem_<losowy_hex>_restore_test`) — skrypt jej NIE usuwa przed utworzeniem, tylko po zakończeniu testu. |

### Użycie

```bash
# Backup (produkcja lub ręcznie):
DATABASE_URL=... BACKUP_REMOTE=s3:za-oknem-backups AGE_RECIPIENT=age1... \
  bash infrastructure/scripts/backup.sh

# Test odtworzenia — na IZOLOWANYM hoście weryfikacyjnym z prywatnym kluczem age,
# nigdy na tym samym VPS co backup.sh (regularnie, np. cron — realne wpięcie w
# TASK-15.2/15.3):
DATABASE_URL=... BACKUP_REMOTE=s3:za-oknem-backups AGE_IDENTITY=/sciezka/do/key.txt \
  bash infrastructure/scripts/restore_test.sh

# Self-check lokalny (dev docker-compose + lokalny katalog jako "off-VPS"):
docker compose up -d postgres
bash infrastructure/scripts/test_backup_restore.sh
```

### Model bezpieczeństwa (po LucTroosh review)

- Hasło z `DATABASE_URL` nigdy nie jest argumentem procesu — `_pgpass.sh` zapisuje je
  do `PGPASSFILE` (chmod 600, katalog tymczasowy usuwany na końcu), polecenia
  dostają URL bez hasła.

- Dump bazy **i** sekrety trafiają na `BACKUP_REMOTE` wyłącznie zaszyfrowane `age`
  (ten sam klucz publiczny) — nigdy plaintextem, nawet tymczasowo na dysku (pipe
  prosto z `pg_dump`/`tar` do `age`).
- `manifest-<STAMP>.txt` (jawny tekst, bez danych — tylko liczby wierszy per tabela i
  wersja migracji) pozwala `restore_test.sh` wykryć realną rozbieżność po odtworzeniu,
  nie tylko brak tabel.
- `restore_test.sh` odszyfrowuje dump strumieniowo do `pg_restore` (bez plaintextu na
  dysku), odrzuca niekompletny manifest i backup starszy niż `BACKUP_MAX_AGE_HOURS`.
- `restore_test.sh` wymaga prywatnego klucza (`AGE_IDENTITY`) i musi działać na
  osobnym, izolowanym hoście weryfikacyjnym — backup VPS nigdy nie ma możliwości
  odszyfrowania własnych backupów.

### Retencja

Po stronie storage, nie w skryptach — np. lifecycle rule bucketu usuwająca obiekty
starsze niż 30 dni. Wszystkie artefakty jednego backupu powstają w tym samym
przebiegu, więc reguła wiekowa usuwa zestaw w całości.

**BLOKADA (produkcja):** realny off-VPS storage (bucket/provider), para kluczy `age`
i wydzielony host weryfikacyjny (z prywatnym kluczem) to decyzja/zasoby od Ciebie —
skrypty są gotowe i przetestowane lokalnie, ale zaplanowane uruchamianie na
produkcyjnym VPS (TASK-15.2) wymaga tych danych.
