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

if [[ -f "$dump.sha256" ]]; then
  (cd "$(dirname "$dump")" && sha256sum --check --status "$(basename "$dump").sha256")
  echo "checksum verified"
else
  echo "warning: no $dump.sha256 beside the dump; contents were not verified" >&2
fi

tables="$(psql "$url" -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")"
if [[ "$tables" != "0" ]]; then
  echo "refusing: the target already holds $tables tables. Restore into an empty database." >&2
  exit 3
fi

pg_restore --dbname="$url" --no-owner --no-privileges --exit-on-error "$dump"

echo "restored $dump"
echo "now check it: psql \"$url\" -c 'SELECT count(*) FROM sales_documents'"
