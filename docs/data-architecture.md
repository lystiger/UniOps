# UniOps data architecture

UniOps is an operational system with a small data platform underneath it. This
document describes the layers, what each is responsible for, and the rules that
keep them separable.

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

## The rule that shapes everything else

> **Raw source data must survive changes in our interpretation of the source schema.**

We will misread the source. It has already happened twice, and both times the
raw layer is what made the mistake fixable rather than permanent:

- `thueGTGT` was modelled as a VAT *rate* in `NUMERIC(8,4)`. It is a VAT
  **amount** in dong. SQLite stored it anyway; PostgreSQL refused it.
- The purchase report's grand-total footer was ingested as a purchase document,
  double-counting every purchase in an all-time total.

In both cases the payloads were untouched and the correction was a
re-interpretation, not a re-fetch. That is the whole argument for the raw layer.

## Layers

### Source

EasyBooks, through a connector restricted to endpoints that have been directly
observed. Every path is a module constant; none is operator-configurable, so
there is no route by which UniOps can be pointed at an unobserved endpoint.
EasyBooks is read and never written. See
[EasyBooks integration](easybooks-integration.md).

A second source would be added as a second connector writing into the same raw
layer with its own `source_system`, not by widening this one.

### Raw — `easybooks_raw_records`

Exactly what the source returned, stored as JSON, keyed by
`(source_system, entity_type, source_id, payload_hash)`.

Purpose:

- **auditability** — what did EasyBooks actually say, on the day we asked;
- **replay** — re-derive the normalized layer without re-fetching;
- **debugging** — compare what we stored against what we read;
- **recovery from interpretation mistakes** — the two above;
- **change detection** — an identical payload has an identical hash, so an
  unchanged document creates no new version.

The layer is **append-only**. A changed payload is stored beside the old one,
never over it. Nothing in the codebase updates or deletes a raw payload, and a
normalized row's foreign key onto it is `ON DELETE RESTRICT` so a raw version
cannot be removed while something claims to have come from it.

Raw is not queried by the application. It exists for the pipeline and for people.

### Staging / accounting — `sales_documents`, `sales_lines`, `purchase_documents`, `purchase_lines`

The normalized replica of EasyBooks accounting data.

Purpose:

- parse source-specific fields into typed values — `Decimal` money, business
  dates, booleans;
- rename source vocabulary into UniOps vocabulary, once;
- preserve accounting semantics rather than improve them: `giaTriMua` is
  authoritative even when quantity times unit price disagrees, because that is
  what the accounting system says.

This layer is a **replica, not a ledger**. UniOps does not post entries, does not
compute balances, and is not the accounting system of record.

### Core / domain — `customers`, `products`, `orders`, `order_lines`, `order_accounting_links`

Stable business entities that belong to UniOps and outlive any EasyBooks API
change. Customers and products are canonical, carrying EasyBooks identifiers as
attributes rather than being defined by them. Orders and order lines have no
EasyBooks counterpart at all: they exist before accounting does.

`order_accounting_links` belongs here rather than in the accounting layer: it is
a UniOps belief about a relationship EasyBooks does not model, not a fact
EasyBooks stated. See [Order to cash](order-to-cash.md).

If EasyBooks were replaced, this layer would keep its shape and the two above it
would be rewritten.

### Marts — `app/services/analytics.py`, `app/services/exceptions_view.py`

Derived, query-oriented read models over the accounting layer, for dashboards,
management reporting, and later ML/AI features.

There are **no mart tables**. Every figure is computed on request from the
normalized tables. At the current size — hundreds of documents — that is fast
enough and cannot go stale, which a materialized table could. The point at which
to revisit is tens of thousands of documents in a single window, not before.

Money is summed in Python with `Decimal`, not with SQL `SUM`. SQLite has no
decimal type and aggregates through C doubles, so a SQL sum there is float
arithmetic on money.

Accounting and payment states — `NOT_INVOICED`, `INVOICED`, `UNKNOWN` and the
rest — are derived here too, never stored. A stored flag would go stale the
moment EasyBooks corrected the document behind it. Where a figure cannot be
derived because the source does not carry it, the mart returns `null` with a
sentence saying why, rather than a zero that would read as a real answer.

### Operational — `easybooks_sync_runs`, `users`, `user_sessions`

Not part of the data flow: how the system is run and who may use it. Sync runs
record what each ingestion did; users and sessions are authentication.

## Table map

| Table | Layer |
| --- | --- |
| `easybooks_raw_records` | RAW |
| `sales_documents`, `sales_lines` | STAGING / ACCOUNTING |
| `purchase_documents`, `purchase_lines` | STAGING / ACCOUNTING |
| `customers`, `products` | CORE / DOMAIN |
| `orders`, `order_lines` | CORE / DOMAIN |
| `order_accounting_links` | CORE / DOMAIN |
| *(no tables)* `app/services/analytics.py` | MART |
| `easybooks_sync_runs` | OPERATIONAL |
| `users`, `user_sessions` | OPERATIONAL |

## The connector boundary

```text
EasyBooks HTTP response          app/integrations/easybooks/client.py
        ↓
source-specific parsing          app/integrations/easybooks/sync.py
        ↓
raw document                     easybooks_raw_records
        ↓
typed internal record            app/integrations/easybooks/contracts.py
        ↓
normalization                    app/integrations/easybooks/normalization.py
        ↓
accounting tables                sales_*, purchase_*
```

`contracts.py` holds frozen dataclasses — `SalesDocumentRecord`,
`SalesLineRecord`, `PurchaseDocumentRecord`, `PurchaseLineRecord` — and they are
the boundary. Above them, EasyBooks names. Below them, UniOps names only.

`normalization.py` is the single module allowed to know that `thueGTGT` means
`vat_amount`, `giaTriMua` means `purchase_amount`, and `totalAllAmount` means
`total_amount`. Nothing in `app/services`, `app/api`, or the frontend contains a
source field name, and adding one there is the mistake this layering exists to
prevent.

The records are frozen because a normalized document is a statement about one
observed payload. The one derived value applied afterwards — a sales customer
code taken from the detail lines, because the header does not carry one — is
applied with `dataclasses.replace`, producing a new record rather than editing a
statement about something else.

## Lineage

Every normalized document names the raw version it came from:

| Column | Meaning |
| --- | --- |
| `sales_documents.source_raw_record_id` | the raw header payload it was normalized from |
| `sales_documents.source_lines_raw_record_id` | the raw detail payload; null after a headers-only read |
| `purchase_documents.source_raw_record_id` | the raw row set for the document |
| `*.sync_run_id` | the run that last changed the row |
| `*.synced_at` | when it was last written |

So the question "which exact EasyBooks payload produced this row?" is one join:

```sql
SELECT r.retrieved_at, r.payload_hash, r.payload
FROM sales_documents d
JOIN easybooks_raw_records r ON r.id = d.source_raw_record_id
WHERE d.source_id = :source_id;
```

Lines carry no lineage of their own. They belong to a document and are
reproduced from the same payload, so a pointer on each line would duplicate the
document's without adding a fact.

The pointer is updated even when the normalized content does not change, because
a source payload can change in a field UniOps does not normalize. The row is
then correctly reported unchanged, but it is now explained by a newer raw
version and must say so.

Rows that existed before lineage was introduced were backfilled with the newest
raw version held for them, which is best effort: the exact version was not
recoverable. Anything a sync has touched since records it exactly, and the
reconciliation stage reports any document still missing a pointer.

## Pipeline stages

```text
Extract → Raw → Normalize → Validate/Reconcile → Publish
```

**Validate/reconcile** (`reconciliation.py`) is a named stage, not a side effect.
It does two things:

- *document reconciliation* — compares a sales header against its own lines:
  line amounts against subtotal, line VAT against header VAT, and
  subtotal − discount + VAT against the header total, outside a one-unit
  rounding tolerance;
- *pipeline integrity* — orphan lines, and documents that lost their lineage.

Findings are warnings counted on the sync run, never silent, and never a reason
to discard source data.

There is deliberately **no** purchase header-versus-lines check. A purchase
document's total is computed by summing its own rows, so comparing the two would
prove nothing. Inventing a check there would be inventing a guarantee EasyBooks
does not give.

## What the layering is not

- Not a warehouse. There is no dbt, Spark, Kafka, Airflow, or separate analytics
  database, because no current UniOps problem needs one.
- Not a general BI framework. The mart answers named business questions and
  grows one question at a time.
- Not an accounting system. See the responsibilities section in the
  [README](../README.md).

## Where AI would attach

```text
RAW → ACCOUNTING → CORE → MARTS → FEATURES / AI
```

A future model consumes the mart and core layers, which are curated, typed, and
stable. It does not consume raw EasyBooks responses. Nothing of the sort is
implemented, and the layering exists so that it can be added later without
anything upstream having to change.
