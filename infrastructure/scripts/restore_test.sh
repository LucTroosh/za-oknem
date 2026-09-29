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
# Dekodujemy procentowo zakodowane znaki (np. "foo%5Frestore%5Ftest" -> realna
# nazwa bazy, którą libpq faktycznie łączy) — bez tego porównanie niżej widzi
# literalny, zakodowany fragment URI zamiast prawdziwej nazwy bazy, którą
# libpq rozkoduje, więc RESTORE_TEST_DB ustawione na tę prawdziwą nazwę myli
# guard, a DROP DATABASE i tak trafia w źródłową bazę (Codex review, runda 3).
_urldecode() { printf '%b' "${1//%/\\x}"; }
PROD_DB_NAME="$(_urldecode "${PG_DATABASE_URL_NO_QUERY##*/}")"

# libpq akceptuje `dbname` jako parametr zapytania w URI postgresql:// i ten
# parametr NADPISUJE segment ścieżki — potwierdzone na realnym Postgresie 16:
# `postgresql://user@host/postgres?dbname=za_oknem` faktycznie łączy się z
# `za_oknem`, nie `postgres`. Bez tej poprawki DATABASE_URL z `?dbname=...`
# sprawiłby, że PROD_DB_NAME powyżej (wzięte z samej ścieżki) byłoby błędne, a
# poniższy QUERY doklejony do TEST_URL/adminowych URL-i nadpisywałby z
# powrotem RESTORE_TEST_DB realną bazą z `dbname=`, więc i test odtworzenia, i
# DROP DATABASE trafiałyby w bazę źródłową niezależnie od segmentu ścieżki
# (Codex review, runda 7).
if [[ "$QUERY" == *dbname=* ]]; then
  DBNAME_PARAM="$(echo "$QUERY" | grep -oE 'dbname=[^&]*' | head -n1 | cut -d= -f2-)"
  PROD_DB_NAME="$(_urldecode "$DBNAME_PARAM")"
  QUERY="$(echo "$QUERY" | sed -E 's/[?&]dbname=[^&]*//; s/^&/?/')"
  [ "$QUERY" = "?" ] && QUERY=""
fi
TEST_URL="${BASE_URL}/${RESTORE_TEST_DB}${QUERY}"

# Guard przed DROP DATABASE na czymś realnym: RESTORE_TEST_DB musi być bezpiecznym
# identyfikatorem (tylko małe litery/cyfry/_) kończącym się na _restore_test, i
# różnym od bazy z DATABASE_URL. Sam glob "*_restore_test" (poprzednia wersja)
# przepuszczał np. "za_oknem -- _restore_test", co po interpolacji do surowego SQL
# zamienia resztę polecenia w komentarz i wykonuje DROP DATABASE na PROD_DB_NAME
# zamiast na bazie testowej (Codex review — SQL injection przez nazwę bazy).
# Tylko małe litery, nie [A-Za-z] — Postgres fałduje niecudzysłowiony identyfikator
# w DROP DATABASE do lowercase, więc RESTORE_TEST_DB="FOO_restore_test" przy bazie
# "foo_restore_test" ominąłby poniższe porównanie case-sensitive, a faktycznie
# wykonane polecenie i tak trafiłoby w tę drugą (Codex review, runda 2).
if ! [[ "$RESTORE_TEST_DB" =~ ^[a-z_][a-z0-9_]*_restore_test$ ]]; then
  echo "[restore_test] BŁĄD: RESTORE_TEST_DB musi być z samych małych liter/cyfr/_ (kończąc na _restore_test), jest: ${RESTORE_TEST_DB}." >&2
  exit 1
fi
# Postgres ucina niecudzysłowiony identyfikator do 63 bajtów (NAMEDATALEN-1) —
# potwierdzone na realnym Postgresie 16: CREATE DATABASE z 84-znakową nazwą
# tworzy bazę pod obciętą, 63-znakową nazwą, z samym tylko NOTICE, nie błędem.
# RESTORE_TEST_DB dłuższe niż 63 znaki przechodziłoby więc powyższy regex i
# porównanie niżej jako "inna nazwa", a faktycznie wykonany DROP DATABASE
# trafiałby w obciętą nazwę, która może pokrywać się z realną bazą (Codex
# review, runda 5).
if [ "${#RESTORE_TEST_DB}" -gt 63 ]; then
  echo "[restore_test] BŁĄD: RESTORE_TEST_DB dłuższe niż 63 znaki (limit identyfikatora Postgresa), jest: ${#RESTORE_TEST_DB} znaków." >&2
  exit 1
fi
if [ "$RESTORE_TEST_DB" = "$(echo "$PROD_DB_NAME" | tr 'A-Z' 'a-z')" ]; then
  echo "[restore_test] BŁĄD: RESTORE_TEST_DB (${RESTORE_TEST_DB}) to ta sama baza co w DATABASE_URL — odmawiam DROP." >&2
  exit 1
fi

WORKDIR="$(mktemp -d)"
DB_CREATED=""
cleanup() {
  rm -rf "$WORKDIR"
  # "jednorazowa baza" ma taką pozostać — bez tego każdy przebieg (np. z crona,
  # TASK-15.2) trwale zostawia pełną kopię danych produkcyjnych na instancji
  # Postgresa (Codex review). Sprzątamy przy każdym wyjściu, sukces czy błąd.
  if [ -n "$DB_CREATED" ]; then
    psql --dbname="${BASE_URL}/postgres${QUERY}" -v ON_ERROR_STOP=1 \
      -c "DROP DATABASE IF EXISTS ${RESTORE_TEST_DB};" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

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
DB_CREATED=1

echo "[restore_test] pg_restore $LATEST_DUMP -> $RESTORE_TEST_DB..."
pg_restore --dbname="$TEST_URL" --no-owner --no-privileges "$WORKDIR/$LATEST_DUMP"

echo "[restore_test] smoke-check..."
# Sprawdzamy konkretne tabele modelu (app/models.py), nie tylko "cokolwiek istnieje"
# — sam count(*) > 0 przechodzi nawet, gdy odtworzyła się tylko alembic_version, a
# żadna tabela aplikacji (Codex review).
EXPECTED_TABLES="measurements geo_areas weather_snapshots alerts forecasts"
MISSING=""
for t in $EXPECTED_TABLES; do
  EXISTS="$(psql --dbname="$TEST_URL" -t -c "SELECT to_regclass('public.${t}') IS NOT NULL;" | tr -d '[:space:]')"
  [ "$EXISTS" = "t" ] || MISSING="$MISSING $t"
done
if [ -n "$MISSING" ]; then
  echo "[restore_test] BŁĄD: brak oczekiwanych tabel po odtworzeniu:$MISSING" >&2
  exit 1
fi

echo "[restore_test] OK: $LATEST_DUMP odtworzony do $RESTORE_TEST_DB, wszystkie oczekiwane tabele obecne."
