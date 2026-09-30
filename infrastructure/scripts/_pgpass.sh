# shellcheck shell=bash
# Sourced by backup.sh / restore_test.sh / test_backup_restore.sh.
#
# LucTroosh review [P2]: a password embedded in DATABASE_URL ended up in the argv
# of psql/pg_dump/pg_restore — world-readable via `ps` / /proc/<pid>/cmdline on the
# backup host for the whole run. pg_secure_url moves the password (from the URI
# userinfo or a `password=` query parameter) into a mode-600 PGPASSFILE and leaves
# a password-free URL in PG_SAFE_URL for use in command lines. libpq reads the
# passfile itself, so no child process ever gets the secret as an argument.
#
# libpq has exactly two secret connection parameters: `password` and `sslpassword`
# (private-key passphrase, libpq-connect docs; sslkey/sslcert are paths). Both are
# removed from the URL: `password` goes to PGPASSFILE, `sslpassword` - which pgpass
# can't hold - to a mode-600 PGSERVICEFILE section referenced via `service=`
# (libpq merges service-file parameters with the connection string).
#
# Usage: pg_secure_url "$URL" "$PRIVATE_DIR"
#   -> sets PG_SAFE_URL, exports PGPASSFILE / PGSERVICEFILE when needed

_pg_urldecode() { printf '%b' "${1//%/\\x}"; }

pg_secure_url() {
  local url="$1" dir="$2" password="" sslpassword="" query="" part key
  case "$url" in
    *\?*) query="${url#*\?}"; url="${url%%\?*}" ;;
  esac
  if [[ "$url" =~ ^([a-zA-Z][a-zA-Z0-9+.-]*://)([^:@/]*):([^@/]*)@(.*)$ ]]; then
    password="$(_pg_urldecode "${BASH_REMATCH[3]}")"
    url="${BASH_REMATCH[1]}${BASH_REMATCH[2]}@${BASH_REMATCH[4]}"
  fi
  if [ -n "$query" ]; then
    local kept=() qparts=()
    IFS='&' read -ra qparts <<< "$query"
    for part in "${qparts[@]}"; do
      key="$(_pg_urldecode "${part%%=*}")"
      case "$key" in
        password) password="$(_pg_urldecode "${part#*=}")"; continue ;;
        sslpassword) sslpassword="$(_pg_urldecode "${part#*=}")"; continue ;;
        service)
          # We need `service=` for sslpassword; a user-supplied one would be
          # silently replaced, so refuse instead of guessing.
          echo "[pgpass] BŁĄD: parametr service= w DATABASE_URL nie jest obsługiwany." >&2
          return 1 ;;
      esac
      kept+=("$part")
    done
    if [ "${#kept[@]}" -gt 0 ]; then
      url="$url?$(IFS='&'; echo "${kept[*]}")"
    fi
  fi
  if [ -n "$sslpassword" ]; then
    (umask 077; printf '[za_oknem_backup]\nsslpassword=%s\n' "$sslpassword" > "$dir/.pg_service.conf")
    export PGSERVICEFILE="$dir/.pg_service.conf"
    case "$url" in *\?*) url="$url&service=za_oknem_backup" ;; *) url="$url?service=za_oknem_backup" ;; esac
  fi
  PG_SAFE_URL="$url"
  if [ -n "$password" ]; then
    # pgpass format: host:port:db:user:password — `:` and `\` escaped. printf is a
    # builtin, so the password is not an argv of any external process here either.
    local esc="${password//\\/\\\\}"
    esc="${esc//:/\\:}"
    (umask 077; printf '*:*:*:*:%s\n' "$esc" > "$dir/.pgpass")
    export PGPASSFILE="$dir/.pgpass"
    # libpq uses PGPASSWORD as an explicit password and then never reads the
    # passfile (libpq-pgpass docs) - a stale value in the environment would
    # override the correct password from DATABASE_URL (Codex review).
    unset PGPASSWORD
  fi
}
