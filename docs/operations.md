# Running UniOps internally

This is the operator's guide: accounts, the PostgreSQL deployment, and backups. It assumes UniOps runs on one internal machine that the office and
the factory floor can reach, and that nothing about it is published.

## System Boundaries & Authority

### What EasyBooks owns
- **Official accounting books & ledgers**: EasyBooks is the authoritative system of record for accounting.
- **Invoices, taxes, and accounting documents**: All sales invoices, purchase reports, and VAT amounts originate from EasyBooks.
- **Official partner records**: Customers and vendors defined in accounting.
- **Financial truth**: UniOps never creates, edits, or deletes records in EasyBooks.

### What UniOps owns
- **Operational orders & lifecycle**: Customer order intake, order lines, and status transitions through factory floor to delivery.
- **Order-to-invoice reconciliation metadata**: Scored candidate matching, linkage records, and link provenance.
- **Read-only replicas & data lineage**: Immutable raw payload audit trail (`easybooks_raw_records`) and staging tables.
- **Operational analytics & dashboards**: Read models computed on-demand for operational oversight.

See also:
- [Internal Pilot Testing Checklist](human-pilot-checklist.md)
- [Finance & Accounting Policy Questions](finance-validation-questions.md)

## Development and Deployment Baseline

PostgreSQL 17 is the normal integrated development target and the production baseline. SQLite remains supported for fast unit tests and isolated local checks.

## Local development on PostgreSQL

The integrated local development workflow runs against PostgreSQL:

```bash
docker compose up -d db
export UNIOPS_DATABASE_URL="postgresql+psycopg://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
cd frontend && npm run dev
```

*Prerequisites*:
- Docker running on the host machine.
- `UNIOPS_DB_PASSWORD` can be sourced from `.env`: `export UNIOPS_DB_PASSWORD="$(grep '^UNIOPS_DB_PASSWORD=' .env | cut -d= -f2-)"`.
- Working directory is repository root for the first four commands; `frontend` directory for `npm run dev`.
- `app.main:app` is resolved because `uv sync` installs `backend/app` as an editable package.

## Test database safety

- **SQLite is the default** for `uv run pytest`, providing fast and isolated local unit testing without touching PostgreSQL.
- **PostgreSQL tests** execute when `UNIOPS_TEST_DATABASE_URL` is set, pointing at a dedicated test database (e.g., `uniops_test`):
  ```bash
  make db-test-init
  make test-pg
  ```
- **Why the guard exists**: Test execution invokes `Base.metadata.drop_all(engine)` during session setup. Running tests against a database holding real or operational data would destroy all tables and records.
- **Automated guard behavior**: The function `validate_test_database_url` in `backend/tests/conftest.py` inspects the configured URLs before any tests run. It strictly refuses:
  1. `UNIOPS_TEST_DATABASE_URL` pointing to the same host, port, and database name as `UNIOPS_DATABASE_URL`.
  2. Any database named `uniops`, `postgres`, `production`, or `prod`.
  3. Any PostgreSQL database name that does not contain `test` (case-insensitive).
- **Managing `uniops_test`**:
  - `make db-test-init`: Creates `uniops_test` inside the Postgres container if not already present. It fails loudly if the database container is down. Run this before running `make test-pg`.
  - `make db-test-reset`: Drops and recreates `uniops_test` to recover from corrupt schema states.

## Accounts and roles

There are three roles and no self-registration. Accounts exist only where an
administrator creates them from the shell.

| Role | May do |
| --- | --- |
| `admin` | everything, plus `GET /api/users` |
| `office` | read and write orders and catalog |
| `factory-read` | read only: the board, catalog, and sync history |

```bash
uv run uniops user create --username secretary --role office --full-name "Front desk"
uv run uniops user create --username floor --role factory-read
uv run uniops user create --username director --role admin
uv run uniops user list
```

The password is asked for on the terminal and confirmed. It is never taken as a
command-line argument, which would put it in shell history and in the process
list. To script account creation, pipe it instead:

```bash
printf '%s' "$PASSWORD" | uv run uniops user passwd --username secretary --password-stdin
```

Passwords are stored as Argon2id hashes and must be at least 12 characters.
Changing a password signs that account out of every browser, and so does
disabling it:

```bash
uv run uniops user disable --username floor
uv run uniops user enable  --username floor
```

A signed-in person can change their own password from the UniOps header without
an administrator, which keeps that from becoming a shell task.

### Sessions

Signing in sets an `HttpOnly`, `SameSite=Lax` cookie holding a 256-bit random
token. Only the SHA-256 of that token is stored, so a copy of the database
cannot be replayed as a live session. Sessions expire after
`UNIOPS_SESSION_LIFETIME_HOURS` (12 by default).

Expired and revoked rows stay until they are cleared. Clear them on a schedule:

```cron
15 3 * * *  cd /srv/uniops && /usr/local/bin/uv run uniops purge-sessions
```

### What authentication does not cover

- **Brute force is slowed, not blocked.** Argon2id makes each guess cost real
  time and an unknown username costs the same as a known one, but there is no
  lockout and no rate limit. Three accounts on an internal network is the
  reason that is acceptable; it stops being acceptable on a public address.
- **The static frontend bundle is readable without signing in.** It has to be,
  because the sign-in screen is part of it. It contains no customer data, and
  every route it calls is guarded.
- **`GET /api/health` is deliberately public** so a monitor can reach it. It
  reports a status and a version and nothing else.
- **There is no audit trail yet.** The database records who exists and when
  they last signed in, not who changed which order.

## PostgreSQL deployment

```bash
export UNIOPS_DB_PASSWORD='choose-a-long-one'
docker compose up -d db
```

Point the application at it and migrate:

```bash
export UNIOPS_DATABASE_URL="postgresql+psycopg://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops"
uv run alembic upgrade head
```

The compose file binds PostgreSQL to `127.0.0.1` only. The database is reached
by the application on the same host, never across the network.

To serve the UI and the API as one address behind one sign-in:

```bash
cd frontend && npm run build && cd ..
UNIOPS_SERVE_FRONTEND=true uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If UniOps is ever put behind TLS, set `UNIOPS_SESSION_COOKIE_SECURE=true` at the
same time. Do not set it before TLS exists: a `Secure` cookie is never sent over
plain HTTP, so the sign-in would appear to succeed and every next request would
be rejected.

### Moving the existing SQLite database

Bring both databases to the same schema revision, then copy:

```bash
UNIOPS_DATABASE_URL=sqlite:///./uniops.db uv run alembic upgrade head
UNIOPS_DATABASE_URL="$UNIOPS_DATABASE_URL" uv run alembic upgrade head

uv run uniops migrate-db \
  --source sqlite:///./uniops.db \
  --target "postgresql+psycopg://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops"
```

The command fills an empty database and refuses everything else: a target that
already holds rows, a target that has not been migrated, or a schema revision
that does not match the source. It copies and counts inside one transaction, so
a count that does not reconcile leaves the target empty rather than half full.

It also re-attaches UTC to every timestamp on the way through. SQLite has no
timezone type and hands back a naive value for a column the application wrote as
aware UTC; inserted unchanged, PostgreSQL would read those in the server's own
timezone and shift every timestamp in the database.

Keep the SQLite file after the move. It is the only rollback until the first
PostgreSQL backup has been taken and restored once.

## Releases and deployment

Every pull request and every push to `main` runs the full suite on GitHub:
`ruff` and `pytest` against SQLite, the same `pytest` against PostgreSQL 17,
`eslint` and `tsc -b` and the unit tests, and the Playwright browser suite. The
same four jobs run again before any tag is cut, so a released version is never
one that only passed on somebody's laptop. `make ci` runs the same checks here.

A release happens when the `version` in `pyproject.toml` changes on `main`. The
workflow reads it, and if `v<version>` does not already exist it tags that commit
and publishes a GitHub release. Bumping the version is therefore the whole act of
releasing; merging anything else changes nothing.

### Deploying

Nothing pushes a deployment to this machine. The repository is public, so a
GitHub Actions runner here would let a fork's pull request run code on the
internal network, and a deployment credential stored on GitHub's side would be a
credential to an internal system held somewhere it is not needed. Deployment
pulls instead:

```bash
export UNIOPS_DATABASE_URL="postgresql+psycopg://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops"
scripts/deploy.sh              # the newest released tag
scripts/deploy.sh v0.1.4       # a named one
```

The script backs the database up, checks out the tag, syncs dependencies,
migrates, rebuilds the frontend, restarts the service, and then waits for
`/api/health` to answer with the version it just deployed. It refuses to start if
the checkout has uncommitted changes, if `UNIOPS_DATABASE_URL` is unset, or if the
tag does not exist, since none of those can be rolled back from cleanly.

It expects a systemd unit named `uniops` (override with `UNIOPS_SERVICE`) that
starts uvicorn from this directory, and it expects to be able to `sudo systemctl
restart` it.

### Rolling back

```bash
scripts/deploy.sh v0.1.3
```

That returns the code, the dependencies and the bundle. It does **not** undo a
migration: an older schema revision is restored from the backup the deploy took
first, per the recovery steps below. This is why the version bump and the
migration should land in the same release — so that one tag describes one schema.

## Backups

The database holds real customer, supplier, and financial data after any live
sync. Treat it accordingly: the backup directory needs the same protection as
the database itself.

```bash
scripts/backup.sh "postgresql://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops" /var/backups/uniops
```

Each run writes `uniops-<UTC timestamp>.dump` in PostgreSQL's custom format,
checks that `pg_restore` can read it, writes a `.sha256` beside it, and deletes
dumps older than `UNIOPS_BACKUP_KEEP_DAYS` (30 by default).

Nightly, before the working day:

```cron
30 2 * * *  UNIOPS_BACKUP_URL='postgresql://uniops:...@127.0.0.1:5432/uniops' \
            UNIOPS_BACKUP_DIR=/var/backups/uniops \
            /srv/uniops/scripts/backup.sh >> /var/log/uniops-backup.log 2>&1
```

Also back up, separately and by hand, because no script here covers them:

- `.env` — it holds the database password and the EasyBooks credential;
- the backup directory itself, onto something that is not this machine. A backup
  that only exists on the server it protects is not a backup.

### The restore drill

A backup nobody has restored is a guess. Once a month, restore the newest dump
into a scratch database and check that it holds what it should.

**Prerequisites:**
- PostgreSQL service running (e.g. `docker compose up -d db`).
- `UNIOPS_DB_PASSWORD` set in environment or loaded from `.env`.

**Option A — Using native host client tools (`createdb`, `psql`, `dropdb`):**

```bash
createdb -h 127.0.0.1 -U uniops uniops_restore_test
scripts/restore.sh /var/backups/uniops/uniops-20260909T023000Z.dump \
  "postgresql://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops_restore_test"

psql "postgresql://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops_restore_test" \
  -c 'SELECT count(*), max(document_date) FROM sales_documents'
dropdb -h 127.0.0.1 -U uniops uniops_restore_test
```

**Option B — Using Docker Compose (no host Postgres client tools required):**

```bash
docker compose exec -T db psql -U uniops -d postgres -c "CREATE DATABASE uniops_restore_test;"

scripts/restore.sh backups/uniops-20260910T090225Z.dump \
  "postgresql://uniops:$UNIOPS_DB_PASSWORD@127.0.0.1:5432/uniops_restore_test"

docker compose exec -T db psql -U uniops -d uniops_restore_test \
  -c "SELECT count(*), max(document_date) FROM sales_documents;"

docker compose exec -T db psql -U uniops -d postgres -c "DROP DATABASE uniops_restore_test;"
```

`restore.sh` verifies the checksum and refuses a target that already holds
tables, so it can never be pointed at production by accident.

### Recovering for real

1. Stop the application.
2. Create a new empty database. Do not restore over the damaged one; keep it,
   it is evidence.
3. `scripts/restore.sh <dump> <new-database-url>`.
4. Check the row counts against what the business expects.
5. Point `UNIOPS_DATABASE_URL` at the new database and start the application.
6. Re-run the EasyBooks sync for the window since the dump was taken. Ingestion
   is idempotent, so re-reading a period that is already present changes
   nothing.

Recovery loses UniOps orders entered since the last dump, because those exist
nowhere else. Sales and purchase data can always be re-read from EasyBooks.

## Known Operational Limitations & Observability

- **Operational `INVOICED` Status Independence**: Operators can manually advance an order to `INVOICED` on the Order Board even if no EasyBooks invoice is linked. This is an operational workflow flag, not a confirmed accounting fact. Linking/unlinking invoices operates independently via the accounting drawer.
- **Reconciliation Warnings Observability**: Sync-run reconciliation warnings and normalization discrepancies appear as aggregate counts on the Data page ("Warnings" column). Full per-record warning details are logged to server logs. The Overview page displays operational exceptions (unlinked invoices, ambiguous candidates, customer mismatches).
- **Data Page is Read-Only**: The Data page displays synchronization run history (`GET /api/sync-runs`). There is no web-based manual sync trigger button; sync runs are executed via scheduled cron, background processes, or CLI (`uv run uniops sync-easybooks`).
- **No User Management API**: User accounts are administered strictly from the CLI (`uv run uniops user`). The API exposes only `GET /api/users` (for `ADMIN` role) to list account statuses.

## Operational Configuration: Order Tracking Start Date

- **Setting**: `UNIOPS_ORDER_TRACKING_SINCE` (ISO date `YYYY-MM-DD`, optional in `.env`).
- **Purpose**: When an organization transitions to UniOps, historical invoices synced from EasyBooks that predate UniOps adoption would otherwise all appear as `INVOICE_WITHOUT_ORDER` ("Needs attention"), cluttering the operational view.
- **Behavior**:
  - When **set** (e.g. `UNIOPS_ORDER_TRACKING_SINCE=2026-06-01`), only sales documents with `document_date >= that date` appear in the unlinked invoice exception list. Documents with no date (`None`) are always reported to avoid silent omission.
  - When **unset**, all unlinked sales documents are reported (useful for full historical back-audit).
- **Owner decision**: The business owner decides the official operational cutover date from which unlinked invoices represent actionable exceptions.
