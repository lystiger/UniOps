#!/usr/bin/env bash
# Write one verified PostgreSQL backup and drop the ones past the retention age.
#
#   scripts/backup.sh 'postgresql://uniops:...@127.0.0.1:5432/uniops' /var/backups/uniops
#
# Environment: UNIOPS_BACKUP_URL, UNIOPS_BACKUP_DIR, UNIOPS_BACKUP_KEEP_DAYS.
set -euo pipefail

url="${1:-${UNIOPS_BACKUP_URL:-}}"
directory="${2:-${UNIOPS_BACKUP_DIR:-/var/backups/uniops}}"
keep_days="${UNIOPS_BACKUP_KEEP_DAYS:-30}"

if [[ -z "$url" ]]; then
  echo "usage: $0 <postgres-url> [backup-dir]" >&2
  exit 2
fi

mkdir -p "$directory"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$directory/uniops-$stamp.dump"

# Custom format, so a single table can be restored without replaying the rest.
pg_dump --format=custom --no-owner --no-privileges --file="$dump" "$url"

# A dump that pg_restore cannot read is not a backup. Catch that now, while
# somebody is watching, rather than during a restore.
pg_restore --list "$dump" > /dev/null
sha256sum "$dump" > "$dump.sha256"

find "$directory" -maxdepth 1 -name 'uniops-*.dump' -mtime "+$keep_days" -print -delete
find "$directory" -maxdepth 1 -name 'uniops-*.dump.sha256' -mtime "+$keep_days" -delete

echo "wrote $dump ($(du -h "$dump" | cut -f1)), keeping $keep_days days"
