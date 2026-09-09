# UniOps v0.1.2

UniOps is the lightweight operational system of record for UniGreen's make-to-order paper converting workflow. It captures customer orders before accounting, shows their movement through production and delivery, and preserves read-only EasyBooks source data for audit and normalization.

EasyBooks remains the accounting system of record. UniOps never creates, changes, or deletes EasyBooks data.

## Scope

Included in v0.1.2:

- a layered data platform - raw, accounting, domain, mart - with source lineage
  from every normalized row back to the exact EasyBooks payload behind it;
- typed connector contracts, so EasyBooks field names stop at normalization;
- read-only analytics endpoints over sales and purchases;
- session authentication with three roles (`admin`, `office`, `factory-read`)
  guarding every API route;
- PostgreSQL as the deployment target, with a verified copy from the v0.1
  SQLite file;
- canonical customers and products linked by stable EasyBooks codes or IDs;
- operational orders and order lines with a small forward-only lifecycle;
- New Order intake and an internal Order Board;
- read-only, live-opt-in EasyBooks transport;
- sanitized fixture ingestion for sales headers, sales lines, and purchase report rows;
- immutable raw payload versions, normalized accounting tables, sync metrics, and reconciliation warnings;
- Alembic migrations exercised on both SQLite and PostgreSQL, backend/API
  tests, and frontend tests/lint/typecheck/build.

Not included: production scheduling optimization, warehouse management, truck routing, EasyBooks write-back, AI decision-making, complex permissions, receivables workflows, or a generic ERP.

## Architecture

UniOps is an operational system with a small data platform underneath it. Data
moves in one direction through named layers:

```text
EasyBooks
   │
   ▼
SOURCE CONNECTOR          known endpoints only, read-only
   │
   ▼
RAW                       immutable source versions
   │
   ▼
STAGING / ACCOUNTING      normalized EasyBooks data
   │
   ▼
CORE / DOMAIN             canonical UniOps business entities
   │
   ▼
MARTS                     analytics / read models
   │
   ├── Operational UI
   ├── Finance reporting
   └── Future AI
```

| Layer | Tables |
| --- | --- |
| Raw | `easybooks_raw_records` |
| Staging / accounting | `sales_documents`, `sales_lines`, `purchase_documents`, `purchase_lines` |
| Core / domain | `customers`, `products`, `orders`, `order_lines` |
| Mart | none - computed on request by `app/services/analytics.py` |
| Operational | `easybooks_sync_runs`, `users`, `user_sessions` |

The governing rule is that **raw source data must survive changes in our
interpretation of the source schema**. [Data architecture](docs/data-architecture.md)
explains each layer, the connector boundary, lineage, and the pipeline stages.

```mermaid
flowchart LR
    EB["EasyBooks<br/>accounting system of record"] -->|known GET/report POST only| CLI[EasyBooks sync CLI]
    FX[Sanitized fixture bundle] --> CLI
    CLI --> RAW[(Immutable raw payload versions)]
    RAW --> ACCT[(Normalized sales and purchases)]
    ACCT --> CAT[(Canonical customers/products)]
    ACCT --> MART[Analytics read models]
    UI[React order desk] -->|REST /api| API[FastAPI application]
    API --> ORD[(Operational orders/order lines)]
    API --> CAT
    API --> MART
```

## System of record responsibilities

**EasyBooks** is the official accounting source. It owns the books. UniOps never
creates, changes, or deletes anything in it.

**UniOps** is:

- the operational system of record for internal workflow - orders and their
  movement through production and delivery, which exist before accounting does
  and have no EasyBooks counterpart;
- a read-only replica and normalization of EasyBooks accounting data;
- an analytics and future decision-support layer over both.

UniOps is **not** the accounting system of record. It posts no entries, computes
no balances, and any figure it reports about accounting is derived from a stored
EasyBooks payload that can be produced on demand.

The repository is a small monorepo:

- `backend/app/api`: thin HTTP routes;
- `backend/app/services`: order and catalog business rules, plus the analytics mart;
- `backend/app/integrations/easybooks`: constrained transport, typed contracts, normalization, reconciliation, and idempotent sync;
- `backend/migrations`: Alembic schema history;
- `backend/tests`: sanitized fixtures and backend/integration/API tests;
- `frontend/src`: React/TypeScript intake and board UI;
- `scripts/`: backup and restore;
- `docs/data-architecture.md`: the layers, the connector boundary, and lineage;
- `docs/operations.md`: accounts, PostgreSQL deployment, and backups;
- `docs/easybooks-integration.md`: source-specific contract and live setup boundary.

PostgreSQL is the deployment target. SQLite remains the default for local development and for the test suite, and the same suite runs against PostgreSQL with `make test-pg`, so portability is a checked claim rather than an assumption. API handlers are async entry points around short synchronous database operations; this is intentionally simple for current load and should be revisited before high concurrency.

## Local development

Requirements:

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 22+ and npm

Install and migrate from the repository root:

```bash
uv sync --all-groups
uv run alembic upgrade head
cd frontend && npm install
```

`uv sync` installs `backend/app` as the editable `uniops` package, so `app.*` imports and the
`uniops` console script work from the repository root without extra `PYTHONPATH` handling.

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Create an account before the first sign-in, because there is no default one:

```bash
uv run uniops user create --username you --role admin
```

Open `http://localhost:5173`. The Vite development server proxies `/api` to `http://127.0.0.1:8000`, so the session cookie is same-origin in development too. API documentation is available at `http://127.0.0.1:8000/docs`.

## Database and configuration

Copy `.env.example` to `.env` and change only values needed locally. `.env` is ignored by Git.

The default database is `sqlite:///./uniops.db`, which is the development and test default. The deployment target is PostgreSQL:

```bash
UNIOPS_DATABASE_URL=postgresql+psycopg://uniops:PASSWORD@127.0.0.1:5432/uniops
```

`docker compose up -d db` starts one bound to loopback. Moving an existing SQLite database across, backups, and accounts are all in [Operations](docs/operations.md).

Build the schema or bring it to the current revision with:

```bash
uv run alembic upgrade head
```

Validate a migration from a clean temporary database:

```bash
UNIOPS_DATABASE_URL=sqlite:////tmp/uniops-clean.db uv run alembic upgrade head
```

All timestamps are stored using timezone-capable columns and application timestamps are UTC. Dates represent business calendar dates. Money uses fixed-scale `NUMERIC(18,2)` and Python `Decimal`; quantities use `NUMERIC(18,4)`. The API rejects JSON floating-point values for financial and quantity inputs—send decimal strings.

## EasyBooks fixture sync

The checked-in fixture is synthetic and contains no real customer, bank, credential, or company data.

```bash
uv run alembic upgrade head
uv run uniops sync-easybooks \
  --fixture backend/tests/fixtures/easybooks_bundle.json
```

Running the same command again is safe. The second run reports unchanged documents and does not duplicate raw or normalized rows. A changed source payload creates a new raw version and updates the normalized record.

Live mode is disabled by default and has not been authenticated or exercised in this repository. See [EasyBooks integration](docs/easybooks-integration.md) before enabling it.

A live run reads the observed contracts end to end: the sales list, the sales count, one sales detail per document, then raw preservation, normalization, and reconciliation. Every EasyBooks path is a connector constant, and the sales list is fetched in a single request because EasyBooks returns the whole matching array and paginates it client-side.

```bash
uv run uniops sync-easybooks --live \
  --from-date 2026-08-01 --to-date 2026-08-31
```

`--headers-only` remains as a diagnostic that runs the list, count, and purchase reads without the sales-detail route:

```bash
uv run uniops sync-easybooks --live --headers-only \
  --from-date 2026-08-01 --to-date 2026-08-31
```

## Excel export

Write everything already ingested to a workbook. This reads only the UniOps database, so it needs no EasyBooks credential and makes no HTTP request:

```bash
uv run uniops export --out uniops.xlsx \
  --from-date 2026-05-01 --to-date 2026-09-08
```

Exported workbooks contain real customer and financial data once a live sync has run. `*.xlsx` is gitignored; keep exports out of shared locations.

Six sheets: sales documents, sales lines, purchase documents, purchase lines, customers, and products. Each has a frozen header row and an autofilter. Money and quantity cells keep their `Decimal` values with the source scale rather than being written as text.

The date window bounds the four transactional sheets; the catalog sheets are always complete. Documents with no date are always included, since an undated document cannot be shown to fall outside the window and silently dropping one would lose a real record.

Omit the dates to export everything.

## Order API

Core endpoints:

- `GET/POST /api/customers`
- `GET/POST /api/products`
- `GET/POST /api/orders`
- `GET/PATCH /api/orders/{order_id}`
- `POST /api/orders/{order_id}/status`
- `POST /api/orders/{order_id}/lines`
- `PATCH/DELETE /api/orders/{order_id}/lines/{line_id}`
- `GET /api/sync-runs` (read-only EasyBooks ingestion history and metrics)

Authentication:

- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/auth/change-password`
- `GET /api/users` (admin only)
- `GET /api/health` is the only unauthenticated route, so a monitor can reach it

Every other route requires a session. `GET` needs any signed-in account; anything that changes data needs `admin` or `office`; `factory-read` is refused with 403.

Orders begin as `DRAFT` (shown as Waiting). The lifecycle is:

`DRAFT → CONFIRMED → SCHEDULED → IN_PRODUCTION → READY → DELIVERY_PENDING → DELIVERED → INVOICED → CLOSED`

Cancellation is allowed through the ready/delivery-pending stages. The service layer validates transitions, required dates, catalog references, positive quantities, and fixed-point monetary input.

## Analytics API

Read-only. There is no write route and there should not be. Any signed-in role may read.

- `GET /api/analytics/overview`
- `GET /api/analytics/sales`
- `GET /api/analytics/purchases`

All three take optional `from_date` and `to_date`, inclusive, and refuse an inverted window with 422 before running a query.

```json
{
  "from_date": "2026-01-01",
  "to_date": "2026-12-31",
  "sales": {
    "document_count": 111,
    "customer_count": 20,
    "total": "4329501592.00",
    "vat_amount": "268526046.00",
    "undated_document_count": 0,
    "by_month": [{ "month": "2026-01", "amount": "1069969556.00", "document_count": 25 }]
  },
  "purchases": {
    "document_count": 54,
    "supplier_count": 10,
    "total": "3434358898.00",
    "vat_amount": "274791257.00",
    "undated_document_count": 0,
    "by_month": [{ "month": "2026-01", "amount": "698844351.00", "document_count": 8 }]
  },
  "sales_minus_purchases": "895142694.00"
}
```

Money crosses the wire as a decimal string, never as a JSON float.

`sales_minus_purchases` is **gross commercial flow, not profit**. Purchases in a period are not the cost of the goods sold in that period, no period matching has been done, and nothing here is a margin. It is named for exactly what it computes.

Documents EasyBooks gave no date are excluded from a windowed total, because a row with no date cannot be shown to belong to the window or placed in a month. They are reported as `undated_document_count` rather than folded in silently.

## Tests and quality gates

```bash
uv run pytest
uv run ruff check backend
cd frontend
npm test
npm run lint
npm run build
```

Run the backend suite against the deployment database as well. It catches what SQLite hides, such as a numeric column too narrow for the values it holds:

```bash
docker compose up -d db
make test-pg
```

## Known limitations

- EasyBooks live reads need the account's `group` plus either a bearer token or a username and password; no credentials are stored in the repository.
- Credential login is **implemented and verified end to end**. UniOps performs the two-step sign-in the web client performs - `login-by-user` to discover the organisation, then `authenticate` with it - and renews a rejected token once before retrying. A token obtained without an organisation is refused by the data API, which is why the organisation step exists. An account requiring an OTP cannot sign in unattended and is refused up front. A rejected credential is reported clearly and never retried, and `GET /api/sync-runs` exposes run status for alerting.
- The sales list, count, and detail contracts and the purchase report body all come from direct observation of the company account and have been verified live. The sales dynamic report was exercised and deliberately removed as redundant and unsafe to call.
- EasyBooks returns an empty result rather than an error for several misconfigurations - a missing `group`, an inverted date window, an empty `listMaterialGoods`. Where UniOps can detect these it refuses instead of reporting zero rows.
- Live ingestion has been run against the company account and is verified across full years 2024-2026 and a year boundary, with counts reconciling exactly. Only sales and purchases are ingested; no other EasyBooks entity is read.
- The purchase report ends with a grand-total footer row that carries no document identity. It was previously ingested as a purchase document and doubled all-time purchase totals; it is now recognised, skipped, and counted as a reconciliation warning.
- Purchase VAT comes from `thueGTGT`, which is a VAT **amount** in dong rather than a rate. Every observed line divides out to 0.08 of its purchase amount, but no VAT rate is inferred or stored from that.
- Synchronous database operations target the present small-team load, not high concurrency.
- **Sign-in has no rate limit or lockout.** Argon2id makes each attempt cost real time and an unknown username costs the same as a known one, but a determined attacker with network access can keep guessing. This is sized for three accounts on an internal network.
- **There is no audit trail.** The database records who exists and when they last signed in, not who created or advanced which order.
- The static frontend bundle loads without a session, because the sign-in screen is part of it. It carries no data; every route it calls is guarded.
- No production scheduling, inventory, delivery optimization, invoicing, receivable, or payment workflow is implemented yet.

## Authentication and roles

v0.1 shipped with the accepted risk that every route was reachable by anyone who could reach the process. v0.1.1 closes it. Signing in is required for all data, and three roles divide what a signed-in account may do:

| Role | May do |
| --- | --- |
| `admin` | everything, plus read the account list |
| `office` | read and write orders and catalog |
| `factory-read` | read only: the board, catalog, and sync history |

There is no default account and no self-registration. Create the first one from the shell:

```bash
uv run uniops user create --username you --role admin
```

Passwords are Argon2id hashes, at least 12 characters, and are never passed as command-line arguments. The session is an `HttpOnly`, `SameSite=Lax` cookie holding a random token whose SHA-256 is what the database stores, so a copy of the database cannot be replayed as a live session. Changing or disabling an account signs it out everywhere.

`SameSite=Lax` is what stands in for a CSRF token: a cross-site form cannot carry the cookie into a state-changing request.

[Operations](docs/operations.md) covers accounts, sessions, the PostgreSQL deployment, and backups in full.

## Deployment conditions

These still hold, and authentication does not replace them:

- deploy on a trusted internal network, not on a public address;
- if UniOps is ever put behind TLS, set `UNIOPS_SESSION_COOKIE_SECURE=true` at the same time — and not before, since a `Secure` cookie is never sent over plain HTTP;
- treat the database as containing real customer, supplier, and financial data, because after a live sync it does;
- exported workbooks carry the same data. They are gitignored, but nothing stops them being copied elsewhere;
- take backups and restore one occasionally. `scripts/backup.sh` writes and verifies them; the restore drill is in [Operations](docs/operations.md).

## Recommended v0.2

Link the operational order to the accounting document it becomes: map receivables and payments onto the already-ingested sales data, and connect a UniOps order to the EasyBooks invoice that settles it. That turns the order board into something that can answer "what is unpaid" without leaving UniOps, and it needs no EasyBooks write-back.

Production scheduling — batches, operating windows constrained to 07:00–18:00, capacity conflicts, actual completion — remains the natural milestone after that.

