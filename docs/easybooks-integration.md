# EasyBooks read-only integration

## Boundary

EasyBooks is the accounting system of record. UniOps only reads known endpoints and stores derived copies. The integration contains no create, update, delete, browser automation, endpoint discovery, or company-ID-only authorization assumption.

Live mode is opt-in and **has been exercised against the company account**: full years 2024-2026 have been ingested, counts reconciled exactly, and repeated runs reported every document unchanged. Fixture ingestion remains fully functional without a credential.

## Observed endpoints

Base URL: `https://app133.easybooks.vn`

| Purpose | Method | Path | Notes |
|---|---:|---|---|
| Sales list | GET | `/v2/api/sa-invoice-objects-filter` | Returns the complete matching array; no server pagination |
| Sales count | GET | `/v2/api/sa-invoice-count` | Bare non-negative JSON integer |
| Sales detail | GET | `/v2/api/sa-invoice-details/by-saInvoiceID` | `sAInvoiceID=<sales document UUID>` |
| Purchase report | POST | `/api/dynamic-report/mua-hang` | Full observed body; rows under `data` |

All five are connector constants. None of them is operator-configurable, so there is no route for an operator to point UniOps at an unobserved endpoint.

The HTTP transport rejects methods other than GET and POST. POST is allowed only for the purchase report route. Timeouts and exponential retry/backoff apply to network failures, 408, 429, and 5xx responses. Authentication headers are never logged.

### Request scoping

Every live read is scoped by two things, neither of them the `companyID` query parameter:

- the **bearer token**, whose `orgGetData`/`org` claims carry the organisation;
- the **`group` request header**, which selects the data group; read your own value from any EasyBooks API call in browser developer tools.

This was established directly. With the correct `group` present the sales list returns all 35 documents whether `companyID` is empty or populated; with `group` absent every filtered read returns an **empty array rather than an error**. A missing group is therefore indistinguishable from an empty accounting period, so live mode refuses to start without `UNIOPS_EASYBOOKS_GROUP`. `companyID` is retained as a request dimension but is no longer required, matching observed requests that send it empty.

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

### Obtaining a token automatically

Bearer tokens last 30 days, so pasting one by hand does not survive unattended operation. Setting a username and password lets UniOps obtain its own:

```dotenv
UNIOPS_EASYBOOKS_USERNAME=uniops-service-account
UNIOPS_EASYBOOKS_PASSWORD=
```

`POST /api/authenticate` takes `{username, password, rememberMe}`. It is the only POST besides the purchase report that the transport permits, and it creates no business data, so the read-only boundary is unchanged.

The token is read from the response under `id_token`, with `idToken`, `token`, `access_token`, `accessToken` and `jwt` also accepted. An unrecognised response is refused, naming the keys that came back so it can be diagnosed, rather than guessed at.

Verified end to end against a live account: with no token configured UniOps signed in, obtained a token carrying `org`, `orgGetData` and `yearWork`, and ingested 56 documents. With a deliberately invalid token configured alongside credentials it renewed and completed the run. Tokens issued this way lasted 24 hours, which no longer matters because renewal is automatic.

A token is fetched at startup when none is configured, and renewed **once** when a request is rejected, after which that request is retried. A renewed token that is also rejected is terminal, so a bad password cannot cause a refresh loop. Without credentials a rejection stays terminal as before. Neither the password nor the token is ever logged or included in a raised message.

Use a dedicated EasyBooks user rather than a person's login: a personal account ties the sync to someone's password changes and departure. In a real deployment the password belongs in a secret store, not a checked-out `.env`.

#### Why signing in needs an organisation

Two different tokens exist, and only one is accepted by the data API:

| | Working token | Token from a bare `/api/authenticate` |
|---|---|---|
| Lifetime | 30 days | 24 hours |
| Claims | `sub`, `org`, `orgGetData`, `yearWork`, `isDependent`, `auth` | `sub`, `username`, `userId`, `companyId`, `authorities` |
| `/v2/api/...` reads | accepted | rejected, HTTP 500 access denied |

The difference is the organisation. Reading the web client's own bundle showed the login payload it sends is not just credentials:

```
{username, password, rememberMe, org, admin, otp, secretCode}
```

Signing in without `org` yields a token carrying no organisation scoping, which the data API refuses. That is why an otherwise valid token was rejected while still inside its validity window.

The client performs two steps, and UniOps reproduces them:

1. `POST /api/login-by-user` with the credentials, answering with `isOTP` and `orgTrees`;
2. `POST /api/authenticate` with the credentials plus the chosen `org`, answering with the token in `id_token` or in the `Authorization` response header. Both are read.

The organisation is taken from `UNIOPS_EASYBOOKS_ORG` when set, otherwise from the pre-login response when the account offers exactly one. An ambiguous choice is refused rather than guessed.

A configured organisation the account does not offer is refused by name. **It is not the company ID**, and pasting one there produces a sign-in rejection that otherwise looks exactly like a wrong password. Leaving the setting empty is correct for a single-organisation account.

The two failures are reported separately: credentials rejected at pre-login blame the username and password, while a rejection at authenticate blames the organisation, since the credentials have already been accepted by then.

An account requiring a one-time password cannot sign in unattended, so `isOTP` is refused up front with an explanation rather than a failed authenticate.

`login-by-user` and `authenticate` are the only POSTs permitted besides the purchase report, and neither creates business data.

### Credential expiry

EasyBooks bearer tokens last **30 days** from issue, and using one does not extend it. A hand-pasted token therefore has to be replaced roughly monthly. Configuring a username and password removes that chore: UniOps obtains its own token and renews it on rejection, as described above.

Detecting a rejected credential takes more than a status code: EasyBooks answers both an absent and a malformed token with **HTTP 500, not 401**. What distinguishes it is the body, which carries Spring Security's `ExceptionTranslationFilter` / access-denied path; a genuine server fault, such as the report `NullPointerException`, carries a service class name instead.

The transport therefore treats 401 and 403 at face value, and a 500 as an auth failure only when those markers are present. Such a failure is terminal and never retried, because resending a stale token only repeats the rejection. The reported message names the environment variable to update and quotes neither the token nor the response body, which contains the account email and a server stack trace.

```
EasyBooks live read refused: EasyBooks rejected the credential (HTTP 500). The bearer
token has most likely expired - they last 30 days. Copy a current one from an
authenticated browser session into UNIOPS_EASYBOOKS_BEARER_TOKEN.
```

Unattended sync therefore requires credentials rather than a pasted token. Either way, monitor `GET /api/sync-runs` and alert when the newest run is not `SUCCEEDED`.

### Verified window coverage

Sales retrieval was exercised across a range of windows against the live account. The count endpoint reconciled exactly every time, with no warnings:

| Window | `sa-invoice-count` | Documents retrieved |
|---|---:|---:|
| 2024 full year | 227 | 227 |
| 2025 full year | 262 | 262 |
| 2026 full year | 111 | 111 |
| 2025 into 2026 | 51 | 51 |

Two findings follow. The token's `yearWork` claim does **not** restrict which years can be read; earlier zero-row results for prior years were caused solely by the missing `group` header. And 262 documents arriving in a single response is further confirmation that the list is not server-paginated.

A full-year ingestion of 2026 - 111 sales documents each requiring its own detail read, plus purchases - completed in about 14 seconds with no failures, and repeated as 166 unchanged documents. Every sales document carried a customer code, with no orphaned documents and no duplicate line keys.

An inverted window is rejected by the CLI. EasyBooks answers one with an empty result rather than an error, which would otherwise read as "no documents" instead of "bad request".

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

### The report ends with a grand-total row

The last row of the `mua-hang` response is a presentation footer, not a purchase:

```json
{ "soCTu": "Tổng cộng", "refID": null, "ngayCTu": null, "maKH": null, "typeID": null,
  "soLuongMua": 141413.91, "giaTriMua": 3434358898.0 }
```

Its money fields hold the sum of every row above it. Ingested as a document it counted the same money twice, and an all-time purchase total came out at exactly double the truth - 54 real documents summing to 3,434,358,898, plus one footer carrying the same figure.

It is recognised by having no document identity at all: no `refID`, no `ngayCTu`/`ngayHoaDon`/`ngayHachToan`, no `accountingObjectCode`/`maKH`, no `typeID`. The label `soCTu` is the only populated text field, and matching on that would break the moment the report is rendered in another language, so identity is what decides.

Skipped rows are counted as a reconciliation warning on the sync run rather than dropped silently, so a change in the report's shape becomes visible instead of quietly changing a total.

### Purchase report row order is unstable

The report returns a document's rows in a different order between identical requests. The same unchanged document was observed coming back permuted, with row contents intact.

Hashing the rows as received therefore produced a different payload hash every run, so unchanged documents were stored as new raw versions and reported as updated, and the raw table grew on every sync without any source change. Across a full-year window this affected 5 of 55 purchase documents per run.

Rows are now ordered by canonical content when grouped into a document. The source order carries no meaning, so nothing is lost, and an unchanged document hashes identically every time. Four consecutive live runs over 2026 now report all 166 documents unchanged with the raw record count static.

### Purchase report

The report was previously sent as `{companyID, fromDate, toDate}`, which the server rejected with HTTP 500 and a `java.lang.NullPointerException` in `DynamicReportMuaHangServiceImpl.getDataDynamicReport`: the body was missing fields it dereferences unconditionally. UniOps now reproduces the observed body in full.

Only `fromDate`, `toDate`, and `companyID` vary. Everything else is the constant the EasyBooks web application sends, including `typeReport=SO_CHI_TIET_MUA_HANG`, `fileName=SoNhatKiMuaHang.xlsx`, `typeReportConfig=11`, empty filter strings, and empty `accountingObjects` / `listMaterialGoods` / `listRSProductionOrderID` arrays.

The response is an envelope; the rows sit under `data`. Each row carries `totalResult`, which is a result-set row count rather than money and is never normalized into an amount.

#### Secondary dates — semantics unknown

The observed request carried `fromDateSecond` and `toDateSecond` both set to the **current date** while the report range was `2026-05-01..2026-09-08`. They are therefore demonstrably not the report range, and their actual meaning has not been observed.

They are reproduced because the real UI sends them, their construction is isolated in `EasyBooksClient._secondary_report_dates`, and no business logic reads them. The value is the current EasyBooks business date in `Asia/Ho_Chi_Minh`: using UTC would roll over seven hours early and send the wrong day. The clock is injected through the client's `today` argument so tests freeze it instead of depending on the wall clock.

#### The sales dynamic report is deliberately absent

`/api/dynamic-report/ban-hang` was exercised against the live account and then removed rather than implemented.

It requires an explicit `listMaterialGoods` naming every material good to include. An empty list is not "all": it returns seven empty scaffolding rows carrying `isEmptyData` under HTTP 200, so a wrong list yields a silently incomplete report rather than an error. Supplying a correct list would first require observing a material-goods endpoint that has never been seen.

What it returns is also redundant. With a goods list assembled from already-ingested lines it produced 49 rows across 35 documents - the same 35 documents and the same 49 lines already read through `sa-invoice-objects-filter` and `sa-invoice-details`, whose `donGia`/`soLuong`/`thanhTien` values UniOps already stores as Decimals. The additional fields are presentation (`donGiaString`, `colorNegative`, `linkRef`), not new facts.

Removing it also narrows the write-capable surface: exactly one POST route remains allowed.

#### Pagination is not required

The body carries `itemsPerPage: 30` and `page: 1`, so paging had to be ruled out rather than assumed. Against the live account, pages 1, 2, and 3 returned **byte-identical** payloads (same SHA-256, verified stable across refetches) and a single response held all 32 rows for the window despite the page size of 30.

The server ignores `page`. No page iteration is implemented. The parameter is still sent as the observed constant, and `purchase_report(page=...)` exists only so the finding can be re-verified.

## What the sales payload does not carry

Every field of all 111 observed sales headers and all 147 detail lines was read
directly out of the production raw payloads. The result matters because it bounds
what any receivables feature can honestly claim.

Present and usable: `id`, `invoiceNo` (110 of 111), `invoiceSeries`, `date`,
`postedDate`, `accountingObjectName` on the header, `accountingObjectCode` on the
lines, and the money fields. Line `debitAccount` is `131` throughout — accounts
receivable in the Vietnamese chart of accounts — and every document is `typeID`
320, "Bán hàng chưa thu tiền", a credit sale.

Present but null on **every** document: `mbDepositID` and `mcReceiptID` (the bank
deposit and cash receipt references), and on every line `sAOrderNo`, `saoderNo`,
`saoderDate`, `sAQuoteID`, `contractNo`, `contractCode`.

Absent entirely: any due date, paid amount, outstanding amount, payment status,
or payment transaction.

Two consequences. There is no sales order or contract reference to match a UniOps
order against, so order/invoice matching can only use customer, amount, and date.
And no payment or settlement state can be derived at all — `typeName` describes
what the document *was* when created, not whether it has since been paid, so
reading it as "unpaid" would report every settled invoice as outstanding.

No payments or receipts endpoint has been observed. None has been added, because
guessing one would break the boundary this integration is built on. See
[Order to cash](order-to-cash.md).

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

#### Customer identity

The sales list names the customer (`accountingObjectName`, `accountingObjectAddress`) but carries **no** `accountingObjectCode`. The code appears only on detail lines, which in turn carry no name. Neither half identifies a customer alone, so UniOps pairs them: the code comes from the lines, the name from the header.

Observed across 35 live documents: every line carried a code, no document's lines disagreed, and 35 documents resolved to 12 distinct customers with no unlinked document. The codes are 10- or 14-digit Vietnamese tax codes, the 14-digit form being a branch suffix, so the identity is stable rather than a name match.

A header that already supplies a code keeps it; the lines never override it. Lines that disagree on a code yield no code and a reconciliation warning rather than an arbitrary pick. A header-only read has no lines, so it leaves the code unset instead of guessing—meaning header-only runs catalogue no customers.

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

`thueGTGT` is the VAT **amount** in dong, not a rate. It was first modelled as `NUMERIC(8,4)`, which SQLite accepted regardless of precision and PostgreSQL refused as a numeric field overflow on every real invoice. Every observed line divides out to exactly 0.08 of its purchase amount, but no rate is inferred or stored from that: the stored value is the amount the report gave.

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

