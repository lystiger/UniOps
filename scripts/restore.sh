#!/usr/bin/env bash
# Restore a backup into an EMPTY database.
#
#   scripts/restore.sh /var/backups/uniops/uniops-20260909T020000Z.dump \
#     'postgresql://uniops:...@127.0.0.1:5432/uniops_restore_test'
#
# Restoring over a database that holds data is not supported here on purpose:
# create an empty one, restore into it, then swap. That also makes this script
# the monthly restore drill.
set -euo pipefail

dump="${1:-}"
url="${2:-}"

if [[ -z "$dump" || -z "$url" ]]; then
  echo "usage: $0 <dump-file> <postgres-url-of-empty-database>" >&2
  exit 2
fi

# SQLAlchemy driver prefixes (e.g. postgresql+psycopg://) are invalid for psql/pg_restore.
url="$(echo "$url" | sed -E 's/^postgresql\+[a-zA-Z0-9_-]+:/postgresql:/')"

if [[ -f "$dump.sha256" ]]; then
  if ! (cd "$(dirname "$dump")" && sha256sum --check --status "$(basename "$dump").sha256"); then
    echo "FAILED: checksum verification failed for $dump" >&2
    exit 1
  fi
  echo "checksum verified"
else
  echo "warning: no $dump.sha256 beside the dump; contents were not verified" >&2
fi

run_sql() {
  local query="$1"
  if command -v psql >/dev/null 2>&1; then
    psql "$url" -tAc "$query"
  elif command -v docker >/dev/null 2>&1 && docker compose ps --services 2>/dev/null | grep -q "^db$"; then
    docker compose exec -T db psql "$url" -tAc "$query"
  else
    echo "error: neither psql nor a running docker compose db service was found" >&2
    exit 1
  fi
}

tables="$(run_sql "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")"
if [[ "$tables" != "0" ]]; then
  echo "refusing: the target already holds $tables tables. Restore into an empty database." >&2
  exit 3
fi

if command -v pg_restore >/dev/null 2>&1; then
  pg_restore --dbname="$url" --no-owner --no-privileges --exit-on-error "$dump"
elif command -v docker >/dev/null 2>&1 && docker compose ps --services 2>/dev/null | grep -q "^db$"; then
  docker compose exec -T db pg_restore --dbname="$url" --no-owner --no-privileges --exit-on-error < "$dump"
else
  echo "error: neither pg_restore nor a running docker compose db service was found" >&2
  exit 1
fi

echo "restored $dump"
