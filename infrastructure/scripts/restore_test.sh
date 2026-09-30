#!/usr/bin/env bash
# TASK-1.1 (§68 Master Planu): "sam backup bez testu odtworzenia nie jest wystarczający".
# Pobiera NAJNOWSZY dump z BACKUP_REMOTE, odtwarza do jednorazowej bazy i sprawdza,
# że faktycznie da się z niego coś odczytać. Nigdy nie dotyka bazy produkcyjnej —
# zawsze osobna baza z sufiksem _restore_test.
#
# WAŻNE (LucTroosh review): dump i sekrety są szyfrowane age (backup.sh). Ten skrypt
# musi więc mieć prywatny klucz (AGE_IDENTITY) i dlatego uruchamiać go na IZOLOWANYM
# hoście weryfikacyjnym, NIGDY na VPS robiącym backup (klucz prywatny nie może tam
# istnieć — patrz Security w TASK-1.1-backup.md).
#
# Wymaga: rclone, pg_restore, psql, age. Zmienne środowiskowe: DATABASE_URL (bazowy
# connection string — nazwa bazy w nim jest ignorowana, używana tylko do wyciągnięcia
# hosta/usera), BACKUP_REMOTE, AGE_IDENTITY (ścieżka do prywatnego klucza age),
# RESTORE_TEST_DB (domyślnie losowa nazwa kończąca się na _restore_test).
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL musi być ustawione}"
: "${BACKUP_REMOTE:?BACKUP_REMOTE musi być ustawione}"
: "${AGE_IDENTITY:?AGE_IDENTITY musi być ustawiony (ścieżka do prywatnego klucza age) — dump i sekrety są szyfrowane, test odtworzenia musi je faktycznie odszyfrować, nie tylko sprawdzić obecność}"
[ -f "$AGE_IDENTITY" ] || { echo "[restore_test] BŁĄD: AGE_IDENTITY (${AGE_IDENTITY}) nie jest plikiem." >&2; exit 1; }
# Losowa domyślna nazwa (LucTroosh review [P1], patrz guard przy DROP DATABASE niżej):
# stała domyślna nazwa pozwalała temu skryptowi bezwarunkowo usunąć istniejącą bazę o
# tej nazwie, nawet jeśli powstała z innego powodu (ręczna praca, inny równoległy
# przebieg). Losowy sufiks czyni kolizję praktycznie niemożliwą, więc normalnie nie ma
# czego usuwać przed utworzeniem.
RESTORE_TEST_DB="${RESTORE_TEST_DB:-za_oknem_$(od -An -tx1 -N4 /dev/urandom | tr -d ' \n')_restore_test}"

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

# libpq dopuszcza URI bez ścieżki (baza domyślna = nazwa usera), ale
# ${VAR%/*}/${VAR##*/} niżej zakładają, że ostatni "/" oddziela authority od
# nazwy bazy — dla "postgresql://user@host" (bez ścieżki) to założenie jest
# fałszywe: BASE_URL wychodzi "postgresql:/", a PROD_DB_NAME "user@host"
# zamiast prawdziwej nazwy bazy; admin URL niżej (`${BASE_URL}/postgres`)
# łączyłby się wtedy z hostem "postgres", nie z prawdziwym hostem —
# potwierdzone bezpośrednio na tym wyrażeniu bash (Codex review, runda 10).
# Zamiast zgadywać, wymagamy jawnej nazwy bazy w ścieżce.
if ! [[ "$PG_DATABASE_URL_NO_QUERY" =~ ^[a-zA-Z][a-zA-Z0-9+.-]*://[^/]+/[^/]+$ ]]; then
  echo "[restore_test] BŁĄD: DATABASE_URL musi zawierać jawną nazwę bazy w ścieżce (np. postgresql://user@host/nazwa_bazy) — bez tego nie da się bezpiecznie ustalić hosta/nazwy bazy źródłowej." >&2
  exit 1
fi

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
# (Codex review, runda 7). Klucz parametru też może być procentowo zakodowany
# (np. "db%6eame=" to wciąż "dbname=" po dekodowaniu przez libpq — potwierdzone
# na realnym Postgresie 16) — dopasowanie samego literalnego "dbname=" (jak w
# pierwszej wersji tej poprawki) dałoby się w ten sposób ominąć, więc każdy
# klucz w query dekodujemy PRZED porównaniem, nie po (Codex review, runda 8).
if [ -n "$QUERY" ]; then
  NEW_PARTS=()
  IFS='&' read -ra QPARTS <<< "${QUERY#\?}"
  for part in "${QPARTS[@]}"; do
    key_enc="${part%%=*}"
    val_enc="${part#*=}"
    if [ "$(_urldecode "$key_enc")" = "dbname" ]; then
      PROD_DB_NAME="$(_urldecode "$val_enc")"
      continue
    fi
    NEW_PARTS+=("$part")
  done
  if [ "${#NEW_PARTS[@]}" -gt 0 ]; then
    QUERY="?$(IFS='&'; echo "${NEW_PARTS[*]}")"
  else
    QUERY=""
  fi
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
  # Zachowujemy oryginalny kod wyjścia głównego przebiegu — jeśli test już
  # zawiódł, sprzątanie nie ma zamieniać tego na "sukces" (i odwrotnie).
  local exit_code=$?
  rm -rf "$WORKDIR"
  # "jednorazowa baza" ma taką pozostać — bez tego każdy przebieg (np. z crona,
  # TASK-15.2) trwale zostawia pełną kopię danych produkcyjnych na instancji
  # Postgresa (Codex review). Sprzątamy przy każdym wyjściu, sukces czy błąd.
  # `|| true` (poprzednia wersja) połykało błąd DROP i skrypt kończył się
  # sukcesem nawet gdy baza testowa (pełna kopia danych produkcyjnych)
  # zostawała trwale na instancji — monitoring odnotowałby to jako zdany test
  # odtworzenia mimo porzuconej kopii danych (Codex review, runda 9).
  if [ -n "$DB_CREATED" ]; then
    if ! psql --dbname="${BASE_URL}/postgres${QUERY}" -v ON_ERROR_STOP=1 \
      -c "DROP DATABASE IF EXISTS ${RESTORE_TEST_DB};" >/dev/null 2>&1; then
      echo "[restore_test] BŁĄD: nie udało się usunąć bazy testowej ${RESTORE_TEST_DB} — została na instancji, wymaga ręcznego sprzątnięcia." >&2
      exit_code=1
    fi
  fi
  exit "$exit_code"
}
trap cleanup EXIT

echo "[restore_test] szukam najnowszego dumpa w $BACKUP_REMOTE..."
LATEST_DUMP="$(rclone lsf "$BACKUP_REMOTE" --include "db-*.dump.age" | sort | tail -n1)"
if [ -z "$LATEST_DUMP" ]; then
  echo "[restore_test] BŁĄD: brak dumpów w $BACKUP_REMOTE — nie ma czego odtwarzać." >&2
  exit 1
fi
rclone copy "$BACKUP_REMOTE/$LATEST_DUMP" "$WORKDIR/"

# Ten sam zestaw artefaktów co przy backupie (ten sam STAMP) — sprawdzamy config,
# sekrety i manifest, nie tylko dump. Sam poprawny dump przy zepsutym/brakującym
# config nadal oznacza nieudany backup jako całość (Codex review).
STAMP="${LATEST_DUMP#db-}"
STAMP="${STAMP%.dump.age}"
CONFIG_ARCHIVE="config-${STAMP}.tar.gz"
MANIFEST="manifest-${STAMP}.txt"

echo "[restore_test] weryfikuję $CONFIG_ARCHIVE..."
if ! rclone copy "$BACKUP_REMOTE/$CONFIG_ARCHIVE" "$WORKDIR/" 2>/dev/null || [ ! -f "$WORKDIR/$CONFIG_ARCHIVE" ]; then
  echo "[restore_test] BŁĄD: brak $CONFIG_ARCHIVE dla tego samego backupu (${STAMP}) — zestaw artefaktów niekompletny." >&2
  exit 1
fi
# Sam poprawny kontener tar.gz nie wystarczy — puste archiwum albo bez kluczowych
# plików też by przeszło (LucTroosh review [P2]). Sprawdzamy wymagane pliki.
CONFIG_LISTING="$(tar -tzf "$WORKDIR/$CONFIG_ARCHIVE")"  # rzuca błąd głośno, jeśli archiwum jest uszkodzone
for required in docker-compose.yml .env.example; do
  echo "$CONFIG_LISTING" | grep -qxF "$required" || {
    echo "[restore_test] BŁĄD: $CONFIG_ARCHIVE nie zawiera $required — konfiguracji nie da się odtworzyć." >&2
    exit 1
  }
done

echo "[restore_test] weryfikuję $MANIFEST..."
# LucTroosh review [P2/P1]: manifest niesie autorytatywną informację o tym, co backup
# faktycznie zawiera (w tym jawny wariant "sekrety pominięte celowo") oraz metadane
# (wersja migracji, liczba wierszy per tabela) do realnej weryfikacji po odtworzeniu —
# nie samego istnienia tabel, które przechodzi nawet dla pustych.
if ! rclone copy "$BACKUP_REMOTE/$MANIFEST" "$WORKDIR/" 2>/dev/null || [ ! -f "$WORKDIR/$MANIFEST" ]; then
  echo "[restore_test] BŁĄD: brak $MANIFEST dla tego samego backupu (${STAMP}) — zestaw artefaktów niekompletny." >&2
  exit 1
fi
MANIFEST_SECRETS_LINE="$(grep '^secrets=' "$WORKDIR/$MANIFEST" || true)"
MANIFEST_SECRETS_VALUE="${MANIFEST_SECRETS_LINE#secrets=}"

echo "[restore_test] sekrety..."
if [ "$MANIFEST_SECRETS_VALUE" = "NONE:BACKUP_ALLOW_NO_SECRETS" ]; then
  echo "[restore_test] sekrety: celowo pominięte przy backupie (BACKUP_ALLOW_NO_SECRETS=1, dev/self-check) — OK wg manifestu."
elif [ -n "$MANIFEST_SECRETS_VALUE" ]; then
  # Pełne odszyfrowanie i walidacja zawartości (LucTroosh review [P1]) — sam
  # "plik dotarł i nie jest pusty" (poprzednia wersja) nie dowodzi, że da się go
  # odszyfrować. Nie logujemy zawartości .env, tylko listę plików w archiwum.
  if ! rclone copy "$BACKUP_REMOTE/$MANIFEST_SECRETS_VALUE" "$WORKDIR/" 2>/dev/null || [ ! -f "$WORKDIR/$MANIFEST_SECRETS_VALUE" ]; then
    echo "[restore_test] BŁĄD: manifest wskazuje sekrety ($MANIFEST_SECRETS_VALUE), ale artefaktu brak na remote." >&2
    exit 1
  fi
  SECRETS_LISTING="$(age -d -i "$AGE_IDENTITY" "$WORKDIR/$MANIFEST_SECRETS_VALUE" | tar -tz)"
  echo "$SECRETS_LISTING" | grep -qx '\.env' || {
    echo "[restore_test] BŁĄD: odszyfrowane archiwum sekretów nie zawiera .env (zawiera: $SECRETS_LISTING)." >&2
    exit 1
  }
  echo "[restore_test] sekrety: odszyfrowane i zweryfikowane (zawierają .env)."
else
  echo "[restore_test] BŁĄD: manifest nie ma poprawnej linii 'secrets=' — backup niekompletny lub uszkodzony manifest." >&2
  exit 1
fi

# Baza testowa: te same host/user/hasło co DATABASE_URL, inna nazwa bazy —
# nigdy nie nadpisujemy bazy produkcyjnej (Security w TASK-1.1.md). Losowa domyślna
# nazwa (wyżej) czyni kolizję praktycznie niemożliwą, więc NIE usuwamy niczego przed
# utworzeniem — jeśli CREATE zawiedzie bo nazwa jednak istnieje, to jawny błąd
# (`set -e`), nie ciche DROP cudzej/nieznanej bazy (LucTroosh review [P1]).
echo "[restore_test] tworzę bazę $RESTORE_TEST_DB..."
psql --dbname="${BASE_URL}/postgres${QUERY}" -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${RESTORE_TEST_DB};"
DB_CREATED=1

echo "[restore_test] odszyfrowuję dump..."
DB_DUMP_PLAIN="$WORKDIR/db-${STAMP}.dump"
age -d -i "$AGE_IDENTITY" -o "$DB_DUMP_PLAIN" "$WORKDIR/$LATEST_DUMP"

echo "[restore_test] pg_restore $LATEST_DUMP -> $RESTORE_TEST_DB..."
pg_restore --dbname="$TEST_URL" --no-owner --no-privileges "$DB_DUMP_PLAIN"

echo "[restore_test] smoke-check (porównanie z manifestem)..."
# LucTroosh review [P2]: samo istnienie tabel (poprzednia wersja) przechodzi nawet dla
# pustych tabel, więc nie wykrywa backupu bez istotnych danych. Porównujemy realne
# liczby wierszy i wersję migracji zapisane w manifeście W MOMENCIE backupu z tym, co
# faktycznie odtworzyło się teraz — to wykrywa też np. przycięty/spóźniony dump.
MISMATCH=""
MANIFEST_ALEMBIC="$(grep '^alembic_version=' "$WORKDIR/$MANIFEST" | cut -d= -f2-)"
RESTORED_ALEMBIC="$(psql --dbname="$TEST_URL" -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d '[:space:]')"
if [ "${MANIFEST_ALEMBIC:-NONE}" != "${RESTORED_ALEMBIC:-NONE}" ]; then
  MISMATCH="$MISMATCH alembic_version(manifest=${MANIFEST_ALEMBIC:-NONE},restored=${RESTORED_ALEMBIC:-NONE})"
fi
for t in measurements geo_areas weather_snapshots alerts forecasts; do
  EXPECTED="$(grep "^table_count.${t}=" "$WORKDIR/$MANIFEST" | cut -d= -f2-)"
  EXISTS="$(psql --dbname="$TEST_URL" -t -c "SELECT to_regclass('public.${t}') IS NOT NULL;" | tr -d '[:space:]')"
  if [ "$EXISTS" != "t" ]; then
    MISMATCH="$MISMATCH ${t}(missing_table)"
    continue
  fi
  ACTUAL="$(psql --dbname="$TEST_URL" -t -c "SELECT count(*) FROM ${t};" | tr -d '[:space:]')"
  if [ "${EXPECTED:-0}" != "${ACTUAL:-0}" ]; then
    MISMATCH="$MISMATCH ${t}(manifest=${EXPECTED:-0},restored=${ACTUAL:-0})"
  fi
done
if [ -n "$MISMATCH" ]; then
  echo "[restore_test] BŁĄD: rozbieżności między manifestem a odtworzoną bazą:$MISMATCH" >&2
  exit 1
fi

echo "[restore_test] OK: $LATEST_DUMP odtworzony do $RESTORE_TEST_DB, wszystkie tabele i liczniki zgodne z manifestem."
