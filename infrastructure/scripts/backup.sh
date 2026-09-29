#!/usr/bin/env bash
# TASK-1.1 (§68 Master Planu): PostgreSQL + config + sekrety, off-VPS.
#
# Wymaga: pg_dump, psql, tar, age, rclone (skonfigurowany remote — patrz README.md w tym
# katalogu). Zmienne środowiskowe: DATABASE_URL (albo PGHOST/PGUSER/... standardowe
# dla pg_dump), BACKUP_REMOTE (rclone remote:path, np. "s3:za-oknem-backups"),
# AGE_RECIPIENT (klucz publiczny age do szyfrowania), REPO_ROOT (domyślnie katalog
# repo wyliczony z lokalizacji skryptu). Opcjonalnie: BACKUP_ALLOW_NO_SECRETS=1 —
# pozwala pominąć artefakt sekretów, gdy `.env` naprawdę nie istnieje (tylko dev/
# self-check; na produkcji brak `.env` to błąd konfiguracji, nie stan prawidłowy).
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# Losowy komponent zamiast PID: PID jest unikalny tylko wśród współbieżnych procesów
# NA TYM SAMYM HOŚCIE — dwa kontenery/hosty robiące backup w tej samej sekundzie UTC
# mogą wylosować ten sam PID i nadpisać sobie artefakty na wspólnym remote (LucTroosh
# review). 4 losowe bajty (~4 mld kombinacji) są unikalne globalnie z praktycznym
# prawdopodobieństwem kolizji bliskim zeru, niezależnie od hosta/kontenera.
STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$(od -An -tx1 -N4 /dev/urandom | tr -d ' \n')"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

: "${DATABASE_URL:?DATABASE_URL musi być ustawione (rule: nie zgadywać połączenia do bazy)}"
: "${BACKUP_REMOTE:?BACKUP_REMOTE musi być ustawione (rclone remote:path) — §68: backup MUSI być poza VPS, brak wartości to jawny błąd, nie ciche pominięcie uploadu}"
: "${AGE_RECIPIENT:?AGE_RECIPIENT musi być ustawiony (klucz publiczny age) — dump i sekrety nie mogą trafić na storage niezaszyfrowane}"

# libpq (pg_dump/psql/pg_restore) rozumie tylko postgresql:// / postgres://, nie
# sufiks sterownika SQLAlchemy (postgresql+psycopg://) używany w .env.example —
# bez tego pg_dump odrzuca DATABASE_URL w udokumentowanym formacie (Codex review).
PG_DATABASE_URL="$(echo "$DATABASE_URL" | sed -E 's#^postgresql\+[A-Za-z0-9_]+://#postgresql://#')"

echo "[backup] pg_dump ze spójnym snapshotem (dump + liczniki manifestu z tej samej migawki)..."
# LucTroosh review [P2]: dump i liczniki manifestu były dwiema OSOBNYMI migawkami bazy
# (pg_dump, potem osobne zapytania psql chwilę później) — insert/delete między nimi
# (normalne przy współbieżnym ingest) dawał manifest niezgodny z tym, co faktycznie jest
# w dumpie, mimo że backup był poprawny. Otwieramy jedną transakcję REPEATABLE READ,
# eksportujemy jej snapshot (pg_export_snapshot) i każemy pg_dump użyć DOKŁADNIE tej
# samej migawki (--snapshot), a liczniki tabel też czytamy w TEJ SAMEJ transakcji —
# więc dump i manifest zawsze opisują identyczny stan bazy. `\!`/`\o` nie zamykają
# połączenia/transakcji psql, więc dump i SELECT-y działają pod jedną migawką mimo że
# pg_dump to osobny proces.
SNAPSHOT_FILE="$WORKDIR/.snapshot_id"
DB_DUMP_PLAIN="$WORKDIR/db-${STAMP}.dump"
DB_DUMP_ENC="$WORKDIR/db-${STAMP}.dump.age"
COUNTS_DIR="$WORKDIR/.counts"
mkdir -p "$COUNTS_DIR"
TABLES=(measurements geo_areas weather_snapshots alerts forecasts)

{
  echo "BEGIN ISOLATION LEVEL REPEATABLE READ;"
  echo "\\o $SNAPSHOT_FILE"
  echo "SELECT pg_export_snapshot();"
  echo "\\o"
  # $(...) wewnątrz \! jest escapowane jako \$(...) w tym heredocu, żeby bash NIE
  # rozwinął go teraz — ma zostać dosłownym $(...) wykonanym przez powłokę dopiero
  # gdy psql faktycznie uruchomi to polecenie przez \!, po zapisaniu SNAPSHOT_FILE.
  echo "\\! pg_dump --dbname=\"$PG_DATABASE_URL\" --format=custom --snapshot=\"\$(tr -d ' \\n' < $SNAPSHOT_FILE)\" -f \"$DB_DUMP_PLAIN\""
  for t in "${TABLES[@]}"; do
    echo "\\o $COUNTS_DIR/$t"
    echo "SELECT count(*) FROM ${t};"
    echo "\\o"
  done
  echo "COMMIT;"
} | psql --dbname="$PG_DATABASE_URL" -v ON_ERROR_STOP=1 -q -t -A

age -r "$AGE_RECIPIENT" -o "$DB_DUMP_ENC" "$DB_DUMP_PLAIN"
rm -f "$DB_DUMP_PLAIN"

echo "[backup] config (bez sekretów)..."
CONFIG_TAR="$WORKDIR/config-${STAMP}.tar.gz"
CONFIG_FILES=(docker-compose.yml .env.example)
[ -f "$REPO_ROOT/infrastructure/caddy/Caddyfile" ] && CONFIG_FILES+=(infrastructure/caddy/Caddyfile)
tar -czf "$CONFIG_TAR" -C "$REPO_ROOT" "${CONFIG_FILES[@]}"

echo "[backup] sekrety (.env), szyfrowanie age..."
SECRETS_ENC="$WORKDIR/secrets-${STAMP}.tar.gz.age"
SECRETS_MANIFEST_LINE="secrets=secrets-${STAMP}.tar.gz.age"
if [ -f "$REPO_ROOT/.env" ]; then
  tar -czf - -C "$REPO_ROOT" .env | age -r "$AGE_RECIPIENT" -o "$SECRETS_ENC"
elif [ "${BACKUP_ALLOW_NO_SECRETS:-}" = "1" ]; then
  echo "[backup] UWAGA: brak $REPO_ROOT/.env, BACKUP_ALLOW_NO_SECRETS=1 — pomijam artefakt sekretów (dev/self-check)." >&2
  SECRETS_ENC=""
  SECRETS_MANIFEST_LINE="secrets=NONE:BACKUP_ALLOW_NO_SECRETS"
else
  # LucTroosh review [P1]: brak sekretów był dotąd tylko ostrzeżeniem, a produkcyjny
  # backup bez .env "udawał" komplet — po utracie VPS nie dałoby się odtworzyć
  # konfiguracji. Na produkcji `.env` zawsze istnieje; brak to błąd konfiguracji.
  echo "[backup] BŁĄD: brak $REPO_ROOT/.env — backup byłby niekompletny (brak sekretów). Ustaw BACKUP_ALLOW_NO_SECRETS=1 tylko dla dev/self-check bez realnych sekretów." >&2
  exit 1
fi

echo "[backup] manifest (metadane do weryfikacji odtworzenia)..."
# LucTroosh review [P2]: smoke-check restore_test.sh sprawdzał tylko istnienie tabel,
# co przechodzi nawet dla pustych tabel. Manifest zapisuje wersję migracji + liczbę
# wierszy per tabela z TEJ SAMEJ migawki co dump (patrz komentarz przy pg_dump wyżej),
# żeby restore_test.sh mógł porównać stan po odtworzeniu z rzeczywistą zawartością
# dumpa, nie tylko z listą nazw tabel. Same liczby nie są danymi produkcyjnymi (rule:
# nie logować wartości danych). alembic_version nie musi być ze snapshotu — migracje
# to sekwencyjne DDL, nie zmieniają się pod dumpem trwającym pojedynczą transakcję.
MANIFEST="$WORKDIR/manifest-${STAMP}.txt"
ALEMBIC_VERSION="$(psql --dbname="$PG_DATABASE_URL" -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d '[:space:]')"
{
  echo "config=config-${STAMP}.tar.gz"
  echo "$SECRETS_MANIFEST_LINE"
  echo "alembic_version=${ALEMBIC_VERSION:-NONE}"
  for t in "${TABLES[@]}"; do
    COUNT="$(tr -d '[:space:]' < "$COUNTS_DIR/$t")"
    echo "table_count.${t}=${COUNT:-0}"
  done
} > "$MANIFEST"

echo "[backup] upload do $BACKUP_REMOTE..."
# Kolejność ma znaczenie: restore_test.sh wybiera "najnowszy backup" wyłącznie po
# obecności db-*.dump.age (rclone lsf --include "db-*.dump.age"). Gdyby dump pojawił
# się na remote PIERWSZY, równoległy restore_test.sh (np. z crona, TASK-15.2) mógłby
# go złapać, zanim config/sekrety/manifest zdążą się wgrać, i zgłosić "niekompletny
# backup" mimo że backup faktycznie kończy się sukcesem chwilę później (Codex review).
# Wgrywamy dump jako OSTATNI, żeby jego pojawienie się na remote było sygnałem
# "cały zestaw już tam jest".
rclone copy "$CONFIG_TAR" "$BACKUP_REMOTE/"
[ -n "$SECRETS_ENC" ] && rclone copy "$SECRETS_ENC" "$BACKUP_REMOTE/"
rclone copy "$MANIFEST" "$BACKUP_REMOTE/"
rclone copy "$DB_DUMP_ENC" "$BACKUP_REMOTE/"

echo "[backup] OK: db-${STAMP}.dump.age, config-${STAMP}.tar.gz, manifest-${STAMP}.txt$( [ -n "$SECRETS_ENC" ] && echo ", secrets-${STAMP}.tar.gz.age" ) -> $BACKUP_REMOTE"
