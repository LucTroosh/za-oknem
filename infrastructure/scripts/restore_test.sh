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

# libpq (psql/pg_restore) rozumie tylko postgresql:// / postgres://, nie sufiks
# sterownika SQLAlchemy (postgresql+psycopg://) używany w .env.example (Codex review).
PG_DATABASE_URL="$(echo "$DATABASE_URL" | sed -E 's#^postgresql\+[A-Za-z0-9_]+://#postgresql://#')"

# Query string (np. ?sslmode=verify-full) musi przetrwać zamianę nazwy bazy —
# inaczej test odtworzenia łączy się bez wymaganych parametrów (np. bez
# weryfikacji certyfikatu), a naiwne "##*/" zostawiłoby ją przyklejoną do nazwy
# bazy z DATABASE_URL, psując poniższy guard (Codex review).
QUERY=""
PG_DATABASE_URL_NO_QUERY="$PG_DATABASE_URL"
case "$PG_DATABASE_URL" in
  *\?*)
    QUERY="?${PG_DATABASE_URL#*\?}"
    PG_DATABASE_URL_NO_QUERY="${PG_DATABASE_URL%%\?*}"
    ;;
esac

# Baza testowa: te same host/user/hasło co DATABASE_URL, inna nazwa bazy —
# nigdy nie nadpisujemy bazy produkcyjnej (Security w TASK-1.1.md).
BASE_URL="${PG_DATABASE_URL_NO_QUERY%/*}"
PROD_DB_NAME="${PG_DATABASE_URL_NO_QUERY##*/}"
TEST_URL="${BASE_URL}/${RESTORE_TEST_DB}${QUERY}"

# Guard przed DROP DATABASE na czymś realnym: wymuszamy sufiks _restore_test i
# odrzucamy, gdyby RESTORE_TEST_DB przez pomyłkę wskazywało bazę z DATABASE_URL
# (Codex review — inaczej błędna konfiguracja może skasować produkcję).
case "$RESTORE_TEST_DB" in
  *_restore_test) ;;
  *)
    echo "[restore_test] BŁĄD: RESTORE_TEST_DB musi kończyć się na _restore_test (jest: ${RESTORE_TEST_DB})." >&2
    exit 1
    ;;
esac
if [ "$RESTORE_TEST_DB" = "$PROD_DB_NAME" ]; then
  echo "[restore_test] BŁĄD: RESTORE_TEST_DB (${RESTORE_TEST_DB}) to ta sama baza co w DATABASE_URL — odmawiam DROP." >&2
  exit 1
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "[restore_test] szukam najnowszego dumpa w $BACKUP_REMOTE..."
LATEST_DUMP="$(rclone lsf "$BACKUP_REMOTE" --include "db-*.dump" | sort | tail -n1)"
if [ -z "$LATEST_DUMP" ]; then
  echo "[restore_test] BŁĄD: brak dumpów w $BACKUP_REMOTE — nie ma czego odtwarzać." >&2
  exit 1
fi
rclone copy "$BACKUP_REMOTE/$LATEST_DUMP" "$WORKDIR/"

# Ten sam zestaw artefaktów co przy backupie (ten sam STAMP) — sprawdzamy config i
# sekrety, nie tylko dump. Sam poprawny dump przy zepsutym/brakującym config nadal
# oznacza nieudany backup jako całość (Codex review).
STAMP="${LATEST_DUMP#db-}"
STAMP="${STAMP%.dump}"
CONFIG_ARCHIVE="config-${STAMP}.tar.gz"
SECRETS_ARCHIVE="secrets-${STAMP}.tar.gz.age"

echo "[restore_test] weryfikuję $CONFIG_ARCHIVE..."
if ! rclone copy "$BACKUP_REMOTE/$CONFIG_ARCHIVE" "$WORKDIR/" 2>/dev/null || [ ! -f "$WORKDIR/$CONFIG_ARCHIVE" ]; then
  echo "[restore_test] BŁĄD: brak $CONFIG_ARCHIVE dla tego samego backupu (${STAMP}) — zestaw artefaktów niekompletny." >&2
  exit 1
fi
tar -tzf "$WORKDIR/$CONFIG_ARCHIVE" >/dev/null  # rzuca błąd głośno, jeśli archiwum jest uszkodzone

echo "[restore_test] sprawdzam obecność $SECRETS_ARCHIVE..."
# ponytail: nie odszyfrowujemy — klucz prywatny age celowo NIE istnieje na VPS
# (Security w TASK-1.1-backup.md), więc to tylko sprawdza, że plik dotarł i nie
# jest pusty. Pełna weryfikacja odszyfrowania wymaga uruchomienia tego kroku na
# maszynie, która ma klucz prywatny.
if rclone copy "$BACKUP_REMOTE/$SECRETS_ARCHIVE" "$WORKDIR/" 2>/dev/null && [ -s "$WORKDIR/$SECRETS_ARCHIVE" ]; then
  echo "[restore_test] sekrety: obecne ($(wc -c <"$WORKDIR/$SECRETS_ARCHIVE") B, odszyfrowanie nie jest tu weryfikowane)."
else
  echo "[restore_test] sekrety: brak artefaktu dla tego backupu (OK, jeśli .env nie istniało przy tworzeniu backupu)."
fi

# Baza testowa: te same host/user/hasło co DATABASE_URL, inna nazwa bazy —
# nigdy nie nadpisujemy bazy produkcyjnej (Security w TASK-1.1.md).
echo "[restore_test] (re)tworzę bazę $RESTORE_TEST_DB..."
psql --dbname="${BASE_URL}/postgres${QUERY}" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${RESTORE_TEST_DB};"
psql --dbname="${BASE_URL}/postgres${QUERY}" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${RESTORE_TEST_DB};"

echo "[restore_test] pg_restore $LATEST_DUMP -> $RESTORE_TEST_DB..."
pg_restore --dbname="$TEST_URL" --no-owner --no-privileges "$WORKDIR/$LATEST_DUMP"

echo "[restore_test] smoke-check..."
TABLE_COUNT="$(psql --dbname="$TEST_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d '[:space:]')"
if [ "${TABLE_COUNT:-0}" -lt 1 ]; then
  echo "[restore_test] BŁĄD: odtworzona baza nie ma żadnych tabel w schemacie public." >&2
  exit 1
fi

echo "[restore_test] OK: $LATEST_DUMP odtworzony do $RESTORE_TEST_DB, $TABLE_COUNT tabel(a)."
