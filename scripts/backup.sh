#!/usr/bin/env bash
# Write one verified PostgreSQL backup and drop the ones past the retention age.
#
#   scripts/backup.sh 'postgresql://uniops:...@127.0.0.1:5432/uniops' /var/backups/uniops
#
# Environment: UNIOPS_BACKUP_URL, UNIOPS_BACKUP_DIR, UNIOPS_BACKUP_KEEP_DAYS.
set -euo pipefail

url="${1:-${UNIOPS_BACKUP_URL:-${UNIOPS_DATABASE_URL:-}}}"
directory="${2:-${UNIOPS_BACKUP_DIR:-/var/backups/uniops}}"
keep_days="${UNIOPS_BACKUP_KEEP_DAYS:-30}"

if [[ -z "$url" ]]; then
  echo "usage: $0 <postgres-url> [backup-dir]" >&2
  exit 2
fi

# SQLAlchemy driver prefixes (e.g. postgresql+psycopg://) are invalid for pg_dump.
url="$(echo "$url" | sed -E 's/^postgresql\+[a-zA-Z0-9_-]+:/postgresql:/')"

if ! mkdir -p "$directory" 2>/dev/null; then
  if [[ -z "${2:-}" && -z "${UNIOPS_BACKUP_DIR:-}" ]]; then
    directory="./backups"
    mkdir -p "$directory"
  else
    echo "error: cannot create backup directory $directory" >&2
    exit 1
  fi
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$directory/uniops-$stamp.dump"

# Custom format, so a single table can be restored without replaying the rest.
if command -v pg_dump >/dev/null 2>&1; then
  pg_dump --format=custom --no-owner --no-privileges --file="$dump" "$url"
  # A dump that pg_restore cannot read is not a backup. Catch that now, while
  # somebody is watching, rather than during a restore.
  pg_restore --list "$dump" > /dev/null
elif command -v docker >/dev/null 2>&1 && docker compose ps --services 2>/dev/null | grep -q "^db$"; then
  docker compose exec -T db pg_dump --format=custom --no-owner --no-privileges "$url" > "$dump"
  docker compose exec -T db pg_restore --list < "$dump" > /dev/null
else
  echo "error: neither pg_dump nor a running docker compose db service was found" >&2
  exit 1
fi

# Store relative filename so checksum verification works when the dump is moved
(cd "$directory" && sha256sum "$(basename "$dump")" > "$(basename "$dump").sha256")

find "$directory" -maxdepth 1 -name 'uniops-*.dump' -mtime "+$keep_days" -print -delete
find "$directory" -maxdepth 1 -name 'uniops-*.dump.sha256' -mtime "+$keep_days" -delete

echo "wrote $dump ($(du -h "$dump" | cut -f1)), keeping $keep_days days"
