#!/usr/bin/env bash
# TASK-1.1 (§68 Master Planu): "sam backup bez testu odtworzenia nie jest wystarczający".
# Pobiera NAJNOWSZY dump z BACKUP_REMOTE, odtwarza do jednorazowej bazy i sprawdza,
# że faktycznie da się z niego coś odczytać. Nigdy nie dotyka bazy produkcyjnej —
# zawsze osobna baza z sufiksem _restore_test.
#
# Wymaga: rclone, pg_restore, psql. Zmienne środowiskowe: DATABASE_URL (bazowy connection
# string — nazwa bazy w nim jest ignorowana, używana tylko do wyciągnięcia hosta/usera),
# BACKUP_REMOTE, RESTORE_TEST_DB (domyślnie za_oknem_restore_test).
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL musi być ustawione}"
: "${BACKUP_REMOTE:?BACKUP_REMOTE musi być ustawione}"
RESTORE_TEST_DB="${RESTORE_TEST_DB:-za_oknem_restore_test}"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "[restore_test] szukam najnowszego dumpa w $BACKUP_REMOTE..."
LATEST_DUMP="$(rclone lsf "$BACKUP_REMOTE" --include "db-*.dump" | sort | tail -n1)"
if [ -z "$LATEST_DUMP" ]; then
  echo "[restore_test] BŁĄD: brak dumpów w $BACKUP_REMOTE — nie ma czego odtwarzać." >&2
  exit 1
fi
rclone copy "$BACKUP_REMOTE/$LATEST_DUMP" "$WORKDIR/"

# Baza testowa: te same host/user/hasło co DATABASE_URL, inna nazwa bazy —
# nigdy nie nadpisujemy bazy produkcyjnej (Security w TASK-1.1.md).
BASE_URL="${DATABASE_URL%/*}"
TEST_URL="${BASE_URL}/${RESTORE_TEST_DB}"

echo "[restore_test] (re)tworzę bazę $RESTORE_TEST_DB..."
psql --dbname="$BASE_URL/postgres" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${RESTORE_TEST_DB};"
psql --dbname="$BASE_URL/postgres" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${RESTORE_TEST_DB};"

echo "[restore_test] pg_restore $LATEST_DUMP -> $RESTORE_TEST_DB..."
pg_restore --dbname="$TEST_URL" --no-owner --no-privileges "$WORKDIR/$LATEST_DUMP"

echo "[restore_test] smoke-check..."
TABLE_COUNT="$(psql --dbname="$TEST_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d '[:space:]')"
if [ "${TABLE_COUNT:-0}" -lt 1 ]; then
  echo "[restore_test] BŁĄD: odtworzona baza nie ma żadnych tabel w schemacie public." >&2
  exit 1
fi

echo "[restore_test] OK: $LATEST_DUMP odtworzony do $RESTORE_TEST_DB, $TABLE_COUNT tabel(a)."
