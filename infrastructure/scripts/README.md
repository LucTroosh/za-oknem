# scripts

## Backup / Restore Test (TASK-1.1, §68 Master Planu)

PostgreSQL + konfiguracja + sekrety, przechowywane POZA VPS, z automatycznym testem
odtworzenia. Szczegóły zakresu: `docs/tasks/TASK-1.1-backup.md`.

### Wymagane narzędzia

- `postgresql-client` (`pg_dump`, `pg_restore`, `psql`)
- [`rclone`](https://rclone.org/) — storage-agnostic upload (S3, B2, SFTP, lokalny
  katalog do testów...); realny remote konfigurowany przez `rclone config` na VPS,
  nazwa/provider to decyzja biznesowa użytkownika, nie tego skryptu.
- [`age`](https://github.com/FiloSottile/age) — szyfrowanie sekretów przed uploadem.

### Zmienne środowiskowe

| Zmienna | Opis |
|---|---|
| `DATABASE_URL` | Connection string do produkcyjnej bazy (backup.sh) / do instancji Postgres, na której robimy restore test (restore_test.sh) — nazwa bazy w nim jest ignorowana przy tworzeniu bazy testowej. |
| `BACKUP_REMOTE` | Cel `rclone` (np. `s3:za-oknem-backups`, albo zwykła ścieżka na dysku do testów lokalnych). |
| `AGE_RECIPIENT` | Publiczny klucz `age` do szyfrowania sekretów (`age-keygen` generuje parę; prywatny klucz trzymamy OSOBNO od backupu — nie musi istnieć na VPS, który go robi). |
| `RESTORE_TEST_DB` | (opcjonalnie) nazwa jednorazowej bazy do testu odtworzenia, domyślnie `za_oknem_restore_test`. |

### Użycie

```bash
# Backup (produkcja lub ręcznie):
DATABASE_URL=... BACKUP_REMOTE=s3:za-oknem-backups AGE_RECIPIENT=age1... \
  bash infrastructure/scripts/backup.sh

# Test odtworzenia (regularnie, np. cron — realne wpięcie w TASK-15.2/15.3):
DATABASE_URL=... BACKUP_REMOTE=s3:za-oknem-backups \
  bash infrastructure/scripts/restore_test.sh

# Self-check lokalny (dev docker-compose + lokalny katalog jako "off-VPS"):
docker compose up -d postgres
bash infrastructure/scripts/test_backup_restore.sh
```

**BLOKADA (produkcja):** realny off-VPS storage (bucket/provider) i para kluczy `age`
to decyzja/zasoby od Ciebie — skrypty są gotowe i przetestowane lokalnie, ale
zaplanowane uruchamianie na produkcyjnym VPS (TASK-15.2) wymaga tych danych.
