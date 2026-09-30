#!/usr/bin/env bash
# Ponytail-style self-check for TASK-1.1: pełny cykl backup -> restore_test przeciwko
# dev `docker compose` Postgresem, z lokalnym katalogiem jako BACKUP_REMOTE (rclone
# obsługuje zwykłą ścieżkę na dysku bez konfiguracji remote — symulacja "off-VPS" do
# testów; prawdziwy provider to decyzja produkcyjna, TASK-15.2).
#
# Wymaga: docker compose (Postgres z tego repo już wystawiony na localhost:5432),
# pg_dump/pg_restore/psql (klient PostgreSQL), rclone, age.
#
# Uruchomienie: bash infrastructure/scripts/test_backup_restore.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

for tool in pg_dump pg_restore psql rclone age; do
  command -v "$tool" >/dev/null || { echo "SKIP: '$tool' nie jest zainstalowane, pomijam self-check." >&2; exit 0; }
done

REMOTE_DIR="$(mktemp -d)"
AGE_DIR="$(mktemp -d)"
trap 'rm -rf "$REMOTE_DIR" "$AGE_DIR"' EXIT

echo "[test] generuję efemeryczny klucz age..."
age-keygen -o "$AGE_DIR/key.txt" 2>"$AGE_DIR/keygen.log"
AGE_RECIPIENT="$(grep -o 'age1[a-z0-9]*' "$AGE_DIR/key.txt" | head -n1)"

export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/za_oknem}"
export BACKUP_REMOTE="$REMOTE_DIR"
export AGE_RECIPIENT
export AGE_IDENTITY="$AGE_DIR/key.txt"
# Self-check nie ma prawdziwego .env w REPO_ROOT — to nie jest produkcyjny przebieg,
# więc świadomie pomijamy artefakt sekretów (LucTroosh review: brak .env poza tym
# trybem jest teraz twardym błędem backup.sh).
export BACKUP_ALLOW_NO_SECRETS=1

# libpq (psql) rozumie tylko postgresql:// / postgres://, nie sufiks sterownika
# SQLAlchemy (postgresql+psycopg://) — ten sam fix co w backup.sh/restore_test.sh
# (Codex review: ten skrypt miał własne psql wywołania, które o tym zapomniały).
PG_DATABASE_URL="$(echo "$DATABASE_URL" | sed -E 's#^postgresql\+[A-Za-z0-9_]+://#postgresql://#')"
# shellcheck source=_pgpass.sh
. "$(dirname "${BASH_SOURCE[0]}")/_pgpass.sh"
pg_secure_url "$PG_DATABASE_URL" "$AGE_DIR"
PG_DATABASE_URL="$PG_SAFE_URL"

echo "[test] czekam na Postgres..."
for _ in $(seq 1 20); do
  psql --dbname="$PG_DATABASE_URL" -c "SELECT 1" >/dev/null 2>&1 && break
  sleep 1
done

echo "[test] uruchamiam backup.sh..."
bash infrastructure/scripts/backup.sh

echo "[test] weryfikuję artefakty w $REMOTE_DIR..."
[ -n "$(find "$REMOTE_DIR" -name 'db-*.dump.age')" ] || { echo "FAIL: brak zaszyfrowanego dumpa bazy" >&2; exit 1; }
[ -n "$(find "$REMOTE_DIR" -name 'config-*.tar.gz')" ] || { echo "FAIL: brak configu" >&2; exit 1; }
[ -n "$(find "$REMOTE_DIR" -name 'manifest-*.txt')" ] || { echo "FAIL: brak manifestu" >&2; exit 1; }

echo "[test] uruchamiam restore_test.sh..."
# Stała nazwa tu jest bezpieczna (jeden deweloper, jeden przebieg na raz) — ale
# restore_test.sh już NIE usuwa istniejącej bazy przed utworzeniem (LucTroosh review),
# więc pozostałość po przerwanym wcześniejszym self-checku wymaga ręcznego
# `DROP DATABASE za_oknem_selfcheck_restore_test` przed ponownym uruchomieniem.
export RESTORE_TEST_DB="za_oknem_selfcheck_restore_test"
bash infrastructure/scripts/restore_test.sh
# restore_test.sh sprząta teraz swoją bazę samo (trap na EXIT, Codex review) —
# nic więcej tu nie zostaje do posprzątania.

echo "[test] PASS: pełny cykl backup -> restore_test przeszedł."
