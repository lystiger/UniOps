#!/usr/bin/env bash
# Bring this machine to a released version of UniOps.
#
#   scripts/deploy.sh            # the newest v* tag on origin
#   scripts/deploy.sh v0.1.4     # a named one, including an older one to go back to
#
# Nothing pushes a deployment here. The repository is public, so no runner and
# no credential of this machine belongs on GitHub's side; this script pulls a
# tag that CI has already proved green.
#
# Environment: UNIOPS_DATABASE_URL (required), UNIOPS_SERVICE (default uniops),
# UNIOPS_HEALTH_URL (default http://127.0.0.1:8000/api/health),
# UNIOPS_SKIP_BACKUP=1 to deploy without one.
set -euo pipefail

service="${UNIOPS_SERVICE:-uniops}"
health_url="${UNIOPS_HEALTH_URL:-http://127.0.0.1:8000/api/health}"

root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$root" ]]; then
  echo "refusing: run this inside the UniOps checkout." >&2
  exit 2
fi
cd "$root"

if [[ -z "${UNIOPS_DATABASE_URL:-}" ]]; then
  echo "refusing: UNIOPS_DATABASE_URL is not set, so alembic would migrate the" >&2
  echo "wrong database. Export the deployment URL and run again." >&2
  exit 2
fi

# A deploy that carries uncommitted edits cannot be reproduced or rolled back to.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "refusing: this checkout has uncommitted changes." >&2
  git status --short >&2
  exit 2
fi

git fetch --tags --prune origin

tag="${1:-}"
if [[ -z "$tag" ]]; then
  tag="$(git tag --list 'v*' --sort=-version:refname | head -n1)"
  if [[ -z "$tag" ]]; then
    echo "refusing: no v* tag exists yet. Release one first." >&2
    exit 2
  fi
fi
if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
  echo "refusing: $tag is not a tag on origin." >&2
  exit 2
fi

previous="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$previous" == "HEAD" ]]; then
  previous="$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)"
fi
echo "==> deploying $tag (was $previous)"

# The migration is the only step that cannot be undone by checking out the old
# tag again, so the backup is taken before it and verified by backup.sh itself.
if [[ "${UNIOPS_SKIP_BACKUP:-}" != "1" && "$UNIOPS_DATABASE_URL" == postgres* ]]; then
  echo "==> backup"
  # SQLAlchemy's driver suffix means nothing to pg_dump.
  scripts/backup.sh "${UNIOPS_DATABASE_URL/+psycopg/}"
else
  echo "==> backup skipped"
fi

echo "==> checking out $tag"
git checkout --quiet --detach "refs/tags/$tag"

echo "==> python dependencies"
uv sync --all-groups

echo "==> database migration"
uv run alembic upgrade head

echo "==> frontend build"
(cd frontend && npm ci && npm run build)

echo "==> restarting $service"
sudo systemctl restart "$service"

echo "==> health"
expected="${tag#v}"
for attempt in $(seq 1 30); do
  body="$(curl -fsS --max-time 5 "$health_url" 2>/dev/null || true)"
  if [[ "$body" == *'"status":"ok"'* ]]; then
    break
  fi
  if [[ "$attempt" == 30 ]]; then
    echo "FAILED: $service did not answer $health_url after 30 tries." >&2
    echo "Roll back with:  scripts/deploy.sh $previous" >&2
    echo "A migration that already ran is undone from the backup, not by the rollback." >&2
    exit 1
  fi
  sleep 2
done

# A stale process answering on the old bundle looks exactly like a good deploy
# until someone reports a missing feature, so the reported version is checked.
if [[ "$body" != *"\"version\":\"$expected\""* ]]; then
  echo "FAILED: $health_url reports $body, which is not version $expected." >&2
  echo "The service is up but is not running $tag. Check that $service starts from $root." >&2
  exit 1
fi

echo "==> $tag is live and reporting version $expected"
