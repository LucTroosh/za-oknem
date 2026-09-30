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
# Usage: pg_secure_url "$URL" "$PRIVATE_DIR"   -> sets PG_SAFE_URL, exports PGPASSFILE

_pg_urldecode() { printf '%b' "${1//%/\\x}"; }

pg_secure_url() {
  local url="$1" dir="$2" password="" query="" part
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
      if [ "$(_pg_urldecode "${part%%=*}")" = "password" ]; then
        password="$(_pg_urldecode "${part#*=}")"
        continue
      fi
      kept+=("$part")
    done
    if [ "${#kept[@]}" -gt 0 ]; then
      url="$url?$(IFS='&'; echo "${kept[*]}")"
    fi
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
