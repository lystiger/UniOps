# EasyBooks read-only integration

## Boundary

EasyBooks is the accounting system of record. UniOps v0.1 only reads known endpoints and stores derived copies. The integration contains no create, update, delete, browser automation, endpoint discovery, or company-ID-only authorization assumption.

Live mode is opt-in and currently **not verified**. Fixture ingestion is fully functional without a live account.

## Known endpoints

Base URL: `https://app133.easybooks.vn`

| Purpose | Method | Path | Notes |
|---|---:|---|---|
| Sales list | GET | `/v2/api/sa-invoice-objects-filter` | Uses date window and configured `companyID` |
| Sales count | GET | `/v2/api/sa-invoice-count` | Companion count read |
| Sales report | POST | `/api/dynamic-report/ban-hang` | `typeReport=SO_CHI_TIET_BAN_HANG` |
| Purchase report | POST | `/api/dynamic-report/mua-hang` | Read-only dynamic report request |
| Sales detail | GET | operator-configured | Exact observed path was not provided; UniOps will not invent one |

The HTTP transport rejects methods other than GET and POST. POST is allowed only for the two known report routes. Timeouts and exponential retry/backoff apply to network failures, 408, 429, and 5xx responses. Authentication headers are never logged.

## Configuration

The operator must provide legitimate access obtained through the company's normal EasyBooks account. Do not paste credentials into source, fixtures, tickets, or logs.

```dotenv
UNIOPS_EASYBOOKS_LIVE_ENABLED=true
UNIOPS_EASYBOOKS_BASE_URL=https://app133.easybooks.vn
UNIOPS_EASYBOOKS_COMPANY_ID=operator-supplied-value

# Provide one legitimate mechanism locally. Both are secret values.
UNIOPS_EASYBOOKS_BEARER_TOKEN=
UNIOPS_EASYBOOKS_COOKIE=

# An already-observed GET route; use {document_id} if the ID belongs in the path.
UNIOPS_EASYBOOKS_SALES_DETAIL_PATH=
```

Live mode refuses to start if it is disabled, has no credential, has no company ID, or attempts sales details without an operator-configured path. `companyID` is a request dimension, not proof of authorization.

Example after legitimate configuration:

```bash
uv run uniops sync-easybooks --live \
  --from-date 2026-08-01 --to-date 2026-08-31
```

The default live window overlaps the previous seven days because no trustworthy EasyBooks `updatedAt` field has been identified. Re-running overlapping windows is safe.

## Fixture contract

Fixture mode accepts one JSON object:

```json
{
  "sales_documents": [{ "id": "stable-document-id" }],
  "sales_lines": { "stable-document-id": [] },
  "purchase_rows": [{ "refID": "stable-purchase-document-id" }]
}
```

`backend/tests/fixtures/easybooks_bundle.json` is intentionally synthetic. It includes exponent-form zero (`0E-10`), a sales detail whose `id` and `sAInvoiceID` are null, and a service purchase with zero unit price but non-zero purchase value.

## Normalization and identity

### Sales

Sales headers require the stable source `id`; it becomes `sales_documents.source_id`. Details are associated with the document ID used to request them—never with nullable line `sAInvoiceID`.

Line identity uses:

1. a hash of document ID plus stable line ID when the detail supplies one; otherwise
2. a hash of document ID, a stable non-financial item/account/repository signature, and its occurrence number among identical signatures.

Quantity, unit price, amount, discount, and VAT are excluded from the fallback identity so corrections update the logical line instead of creating duplicates. The occurrence number handles duplicate source rows with the same product signature. A source reordering of otherwise identical duplicate lines cannot be distinguished; this is documented source ambiguity, and raw versions retain the evidence for reprocessing.

Reconciliation warns outside a one-unit tolerance when:

- sales line amounts do not match header subtotal;
- sales line VAT does not match header VAT;
- subtotal minus discount plus VAT does not match the header final total.

Warnings do not discard source data.

### Purchases

Purchase rows group by `refID`. When absent, a deterministic fallback uses document number, date, vendor code, and type. `giaTriMua` is authoritative. UniOps never assumes quantity multiplied by unit price equals purchase amount; service and utility purchases may have a zero `donGia` with populated `giaTriMua`.

### Decimals and dates

Source numeric values are converted through decimal text to Python `Decimal`; binary floating point is not used for persistence or calculations. Exponent-form zero normalizes to `Decimal("0")`. ISO dates/timestamps and `DD/MM/YYYY` report dates are parsed into business dates.

## Raw storage and idempotency

`easybooks_raw_records` stores source system, entity type, source ID, retrieval time, JSON payload, SHA-256 payload hash, and the sync run that first observed that exact version. Its unique key is:

`(source_system, entity_type, source_id, payload_hash)`

Therefore:

- an identical repeat creates no duplicate raw or normalized record;
- a changed payload is retained as a new immutable raw version;
- normalized documents upsert by stable source ID;
- lines missing from a later source representation are removed from the current normalized view while prior raw payloads remain available.

Each run records start/finish time, fixture/live mode, date window, status, documents seen/created/updated/unchanged/failed, reconciliation warning count, and a bounded error summary. `GET /api/sync-runs` exposes that history read-only. Logs are JSON and include sync/source identity but never auth configuration.

## Live verification checklist

Before anyone claims live integration works:

1. confirm the configured account and company are authorized through normal EasyBooks access;
2. confirm the exact previously observed sales-detail GET route and response envelope;
3. run a narrow read-only date window in a non-production UniOps database;
4. compare sales count/list/detail and purchase report row counts with EasyBooks UI;
5. inspect raw payload redaction and normalized Decimal/date fields;
6. review reconciliation warnings;
7. repeat the same window and verify all documents report unchanged;
8. record the executed command and results without credentials.

