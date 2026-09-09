# EasyBooks read-only integration

## Boundary

EasyBooks is the accounting system of record. UniOps v0.1 only reads known endpoints and stores derived copies. The integration contains no create, update, delete, browser automation, endpoint discovery, or company-ID-only authorization assumption.

Live mode is opt-in and has not yet been exercised against a live account from this repository. Fixture ingestion is fully functional without one.

## Observed endpoints

Base URL: `https://app133.easybooks.vn`

| Purpose | Method | Path | Notes |
|---|---:|---|---|
| Sales list | GET | `/v2/api/sa-invoice-objects-filter` | Returns the complete matching array; no server pagination |
| Sales count | GET | `/v2/api/sa-invoice-count` | Bare non-negative JSON integer |
| Sales detail | GET | `/v2/api/sa-invoice-details/by-saInvoiceID` | `sAInvoiceID=<sales document UUID>` |
| Sales report | POST | `/api/dynamic-report/ban-hang` | `typeReport=SO_CHI_TIET_BAN_HANG` |
| Purchase report | POST | `/api/dynamic-report/mua-hang` | **Currently failing**; see below |

All five are connector constants. None of them is operator-configurable, so there is no route for an operator to point UniOps at an unobserved endpoint.

The HTTP transport rejects methods other than GET and POST. POST is allowed only for the two report routes. Timeouts and exponential retry/backoff apply to network failures, 408, 429, and 5xx responses. Authentication headers are never logged.

### Request scoping

Every live read is scoped by two things, neither of them the `companyID` query parameter:

- the **bearer token**, whose `orgGetData`/`org` claims carry the organisation;
- the **`group` request header** (observed value `GROUPDS2`), which selects the data group.

This was established directly. With `group` present the sales list returns all 35 documents whether `companyID` is empty or populated; with `group` absent every filtered read returns an **empty array rather than an error**. A missing group is therefore indistinguishable from an empty accounting period, so live mode refuses to start without `UNIOPS_EASYBOOKS_GROUP`. `companyID` is retained as a request dimension but is no longer required, matching observed requests that send it empty.

### Sales list

Observed query dimensions: `accountingObjectID`, `currencyID`, `fromDate`, `toDate`, `status`, `keySearch`, `typeId`, `companyID`. UniOps sends `companyID`, `fromDate`, and `toDate`.

The response is a plain JSON array containing **all** matching sales documents. EasyBooks paginates that array **client-side**: a filtered result of 35 documents displayed 10 rows per page, and moving from UI page 1 to page 2 added no `page`, `offset`, `limit`, `itemsPerPage`, or any other paging parameter to the request. UniOps therefore issues exactly one sales list request per window and implements no server-side paging. If a future direct observation shows server pagination exists, that is when to add it—not before.

### Sales count

`sa-invoice-count` takes the same filter dimensions and returns a bare non-negative JSON integer (observed: `35`). `_extract_count` reads that integer, tolerates a numeric string because that costs nothing, and declines every other shape rather than guessing a number out of an invented envelope.

The count is a completeness check:

```
retrieved_sales_document_count == reported_count
```

A difference is never silently accepted. It is recorded as a sync-run reconciliation warning naming both numbers, and no documents are discarded. The warning does not attribute the difference to pagination, because the list is not paginated. A count read that fails or returns an unrecognised shape produces its own warning and ingestion continues.

### Sales detail

```
GET /v2/api/sa-invoice-details/by-saInvoiceID?sAInvoiceID=<document.id>
```

The UUID comes from `sa-invoice-objects-filter[].id`. No `companyID` is sent; the endpoint was never observed to require one. The earlier generic `id=<document_id>` form was not the real contract and has been removed.

## Configuration

The operator must provide legitimate access obtained through the company's normal EasyBooks account. Do not paste credentials into source, fixtures, tickets, or logs.

```dotenv
UNIOPS_EASYBOOKS_LIVE_ENABLED=true
UNIOPS_EASYBOOKS_BASE_URL=https://app133.easybooks.vn
UNIOPS_EASYBOOKS_COMPANY_ID=
UNIOPS_EASYBOOKS_GROUP=operator-supplied-value

# Provide one legitimate mechanism locally. Both are secret values.
UNIOPS_EASYBOOKS_BEARER_TOKEN=
UNIOPS_EASYBOOKS_COOKIE=
```

That is the whole EasyBooks configuration surface. There is no endpoint, paging, or page-size setting: every path is an observed constant.

Live mode refuses to start if it is disabled, has no credential, or has no group. `companyID` is a request dimension, not proof of authorization. Blank `.env` entries are treated as absent, so an empty token never becomes an empty `Authorization` header.

### Live run

A normal live run is a complete pipeline: sales list, sales count, one sales detail read per document, raw preservation, normalization, then reconciliation. Nothing in it is operator-configured.

Example after legitimate configuration:

```bash
uv run uniops sync-easybooks --live \
  --from-date 2026-08-01 --to-date 2026-08-31
```

### Header-only live reads

`--headers-only` is a diagnostic. It performs the sales list, sales count, and purchase report reads without touching the detail route, which isolates authentication, the date window, and count agreement from detail-read behaviour when validating against a real account for the first time:

```bash
uv run uniops sync-easybooks --live --headers-only \
  --from-date 2026-08-01 --to-date 2026-08-31
```

A header-only run records `mode = live-headers`, never calls the sales-detail route, and leaves already-normalized sales lines untouched. Line reconciliation is skipped because no lines were retrieved, so absent lines are never mistaken for a source correction. Repeated header-only runs over the same window report every document as unchanged.

Because a header-only run hashes a fixed "not retrieved" marker in place of lines, alternating header-only and full runs reports documents as updated on each switch. No data is lost; only the change counters move.

The default live window overlaps the previous seven days because no trustworthy EasyBooks `updatedAt` field has been identified. Re-running overlapping windows is safe.

### Purchase report status

`POST /api/dynamic-report/mua-hang` returns HTTP 500 with a server-side `java.lang.NullPointerException` in `DynamicReportMuaHangServiceImpl.getDataDynamicReport`. The request body has never been directly observed and the current `{companyID, fromDate, toDate}` is incomplete; the server resolves the company from the token regardless. Adding the `group` header does not change it.

A failing purchase read must not discard a healthy sales read, so it degrades to a retrieval warning and the run continues with no purchase rows. Fixing it needs one directly observed `mua-hang` request body.

## Fixture contract

Fixture mode accepts one JSON object:

```json
{
  "sales_documents": [{ "id": "stable-document-id" }],
  "sales_lines": { "stable-document-id": [] },
  "purchase_rows": [{ "refID": "stable-purchase-document-id" }]
}
```

`backend/tests/fixtures/easybooks_bundle.json` is intentionally synthetic. It includes exponent-form zero (`0E-10`), an aggregate `total` that must not be read as a document amount, a sales detail whose `id` and `sAInvoiceID` are null, and a service purchase with zero unit price but non-zero purchase value.

## Normalization and identity

### Sales

Sales headers require the stable source `id`; it becomes `sales_documents.source_id`. Details are associated with the document ID used in the `sAInvoiceID` request parameter—never with the detail response's own `id` or `sAInvoiceID`, both of which have been observed as null.

Document-level money comes from `totalAmount` (subtotal), `totalDiscountAmount`, `totalVATAmount` (VAT), and `totalAllAmount` (grand total). The list also carries a `total` field: that is **result-set/report metadata**, not a document amount. EasyBooks populates it with a large aggregate on the first returned row and leaves it `null` on the rest, so UniOps never normalizes it into a document's financial totals.

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
2. run a narrow `--headers-only` window in a non-production UniOps database and confirm the sales list, count, and purchase report respond;
3. confirm the retrieved document total matches `sa-invoice-count` with no reconciliation warning;
4. re-run without `--headers-only` and confirm one sales-detail read per document;
5. compare sales count/list/detail and purchase report row counts with EasyBooks UI;
6. inspect raw payload redaction and normalized Decimal/date fields;
7. review reconciliation warnings, including any count disagreement;
8. repeat the same window and verify all documents report unchanged;
9. record the executed command and results without credentials.

