#!/usr/bin/env bash
# TASK-1.1 (§68 Master Planu): PostgreSQL + config + sekrety, off-VPS.
#
# Wymaga: pg_dump, tar, age, rclone (skonfigurowany remote — patrz README.md w tym
# katalogu). Zmienne środowiskowe: DATABASE_URL (albo PGHOST/PGUSER/... standardowe
# dla pg_dump), BACKUP_REMOTE (rclone remote:path, np. "s3:za-oknem-backups"),
# AGE_RECIPIENT (klucz publiczny age do szyfrowania sekretów), REPO_ROOT (domyślnie
# katalog repo wyliczony z lokalizacji skryptu).
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

: "${DATABASE_URL:?DATABASE_URL musi być ustawione (rule: nie zgadywać połączenia do bazy)}"
: "${BACKUP_REMOTE:?BACKUP_REMOTE musi być ustawione (rclone remote:path) — §68: backup MUSI być poza VPS, brak wartości to jawny błąd, nie ciche pominięcie uploadu}"
: "${AGE_RECIPIENT:?AGE_RECIPIENT musi być ustawiony (klucz publiczny age) — sekrety nie mogą trafić na storage niezaszyfrowane}"

# libpq (pg_dump/psql/pg_restore) rozumie tylko postgresql:// / postgres://, nie
# sufiks sterownika SQLAlchemy (postgresql+psycopg://) używany w .env.example —
# bez tego pg_dump odrzuca DATABASE_URL w udokumentowanym formacie (Codex review).
PG_DATABASE_URL="$(echo "$DATABASE_URL" | sed -E 's#^postgresql\+[A-Za-z0-9_]+://#postgresql://#')"

echo "[backup] pg_dump..."
DB_DUMP="$WORKDIR/db-${STAMP}.dump"
pg_dump --dbname="$PG_DATABASE_URL" --format=custom --file="$DB_DUMP"

echo "[backup] config (bez sekretów)..."
CONFIG_TAR="$WORKDIR/config-${STAMP}.tar.gz"
CONFIG_FILES=(docker-compose.yml .env.example)
[ -f "$REPO_ROOT/infrastructure/caddy/Caddyfile" ] && CONFIG_FILES+=(infrastructure/caddy/Caddyfile)
tar -czf "$CONFIG_TAR" -C "$REPO_ROOT" "${CONFIG_FILES[@]}"

echo "[backup] sekrety (.env), szyfrowanie age..."
SECRETS_ENC="$WORKDIR/secrets-${STAMP}.tar.gz.age"
if [ -f "$REPO_ROOT/.env" ]; then
  tar -czf - -C "$REPO_ROOT" .env | age -r "$AGE_RECIPIENT" -o "$SECRETS_ENC"
else
  echo "[backup] UWAGA: brak $REPO_ROOT/.env — pomijam artefakt sekretów (nic do zaszyfrowania)." >&2
  SECRETS_ENC=""
fi

echo "[backup] upload do $BACKUP_REMOTE..."
rclone copy "$DB_DUMP" "$BACKUP_REMOTE/"
rclone copy "$CONFIG_TAR" "$BACKUP_REMOTE/"
[ -n "$SECRETS_ENC" ] && rclone copy "$SECRETS_ENC" "$BACKUP_REMOTE/"

echo "[backup] OK: db-${STAMP}.dump, config-${STAMP}.tar.gz$( [ -n "$SECRETS_ENC" ] && echo ", secrets-${STAMP}.tar.gz.age" ) -> $BACKUP_REMOTE"
