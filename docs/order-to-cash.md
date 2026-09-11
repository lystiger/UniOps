# Order to cash

```text
Operational order        UniOps owns this
      ↓
UniOps/EasyBooks link    UniOps owns this
      ↓
Sales invoice            EasyBooks owns this
      ↓
Payment data             EasyBooks owns this - not yet available
      ↓
Receivable read model    derived, owned by nobody, stored nowhere
```

## Who owns what

**EasyBooks owns every accounting fact.** The invoice, its number, its amounts,
and whatever payments exist against it are EasyBooks' to state. UniOps reads
them and never writes: there is no create, update, approve, post, or delete path
to EasyBooks anywhere in this milestone or the codebase.

**UniOps owns the operational order** — it exists before accounting does — **and
the link** between an order and an invoice. The link is a UniOps belief about a
relationship EasyBooks does not model. Creating one transfers no accounting
ownership; deleting one changes nothing in EasyBooks.

**Receivables are derived and read-only.** Nothing about payment state is
stored. Every figure is computed from the normalized accounting layer at request
time, so an EasyBooks correction changes the answer on the next call instead of
leaving a stale total behind.

## What EasyBooks actually gives us

Determined by reading every field of all 111 observed sales headers and all 147
detail lines in the production database, not from documentation.

### Verified live

| Concept | Field | Notes |
| --- | --- | --- |
| Invoice id | `id` | UUID, the document's stable identity |
| Invoice number | `invoiceNo` | present on 110 of 111 |
| Invoice series | `invoiceSeries` | e.g. `1C26TSH` |
| Invoice date | `date` | business date |
| Posted date | `postedDate` | |
| Customer code | line `accountingObjectCode` | the canonical link to a UniOps customer |
| Customer name | header `accountingObjectName` | header has the name, lines have the code |
| Amounts | `totalAmount`, `totalVATAmount`, `totalAllAmount` | |
| Document type | `typeID` 320, `typeName` "Bán hàng chưa thu tiền" | a credit sale |
| Receivable posting | line `debitAccount` = `131` | Vietnamese chart of accounts: accounts receivable |

### Observed but empty on every document

These fields exist in the payload and are null on all 111 documents, so nothing
can be built on them yet. They are named here because they are where payment
data would appear if it ever does.

| Concept | Field |
| --- | --- |
| Bank deposit reference | `mbDepositID` |
| Cash receipt reference | `mcReceiptID` |
| Sales order number | line `sAOrderNo`, `saoderNo`, `saoderDate` |
| Quote reference | line `sAQuoteID` |
| Contract reference | line `contractNo`, `contractCode`, `contractDate` |

### Not available at all

No field anywhere in the observed payloads carries:

- **a due date**, or a payment term from which one could be computed;
- **a paid amount**;
- **an outstanding amount**;
- **a payment status**;
- **payment transactions** of any kind.

None of that is in the **sales** payload. Separate receivable and payment
endpoints have since been observed and are documented in
[EasyBooks receivables discovery](easybooks-receivables-discovery.md); they
supply an invoice-level open amount, and confirm that a due date field exists and
is empty. They do not supply settlement.

### What follows from that

Every one of the 111 invoices is a credit sale posting to account 131, so a
receivable demonstrably **exists** for each. Whether it has since been settled is
invisible in this endpoint.

It is tempting to read `typeName` "Bán hàng chưa thu tiền" — "sale, money not yet
collected" — as "unpaid". That is wrong. It describes the document type at the
moment it was created: a sale on credit rather than for cash. A credit sale that
was paid last month still carries `typeID` 320, because the payment is a separate
receipt document UniOps has never seen. Reading it as current payment state
would report every settled invoice as unpaid.

So UniOps reports `INVOICED` where it can prove it, and `UNKNOWN` for everything
payment-derived. It does not report `0.00` outstanding, because that would assert
that every invoice has been paid.

## Linking an order to an invoice

### Cardinality

`order_accounting_links` is unique on the **pair**, not on either side. An order
may link to several invoices and an invoice to several orders. UniGreen has no
order data yet to say which of the three shapes actually occurs, and a
one-to-one key would be a guess that is expensive to reverse once links exist.

### Matching rules

Deterministic and explainable. No model, no learning, no hidden weights.

A sales document is a **candidate** for an order only if:

1. the canonical customer code agrees — an order whose customer has no EasyBooks
   code has no candidates, rather than every invoice in the window; and
2. the invoice date is within **7 days** of the order's required date.

Each candidate is then scored:

| Evidence | Contribution |
| --- | --- |
| customer code agrees | 0.50 (the floor; without it there is no candidate) |
| order total equals invoice subtotal or total | 0.40 |
| invoice within 1 day of required date | 0.10 |
| invoice within 7 days | 0.05 |

An order with any unpriced line has an **unknown** total, and unknown never
counts as an amount match.

A link is only strong enough to justify creating it without a person when
**exactly one** candidate exists, its amount matches, and its score reaches
**0.95**. Two plausible invoices means the answer is unknown, and the candidates
are returned for a human to choose between. Picking the highest score would
state a guess as a fact, in the one place where that is least acceptable.

**No link is ever created automatically.** `auto_linkable` identifies the case
and the UI shows it; a person still confirms. There are no orders in the system
yet against which a matcher could be validated, and a wrong accounting link is
worse than no link.

### Provenance

Every link records how it came about, and none is anonymous:

- `link_method` — `CUSTOMER_DATE_AMOUNT` when the confirmed pair satisfied the
  full rule, `MANUAL` when a person linked something the rule would not have;
- `confidence` — the score at the time, null if the customer codes disagree;
- `evidence` — the customer code, both totals, whether they matched, and the
  date difference in days;
- `created_by_user_id` — who confirmed it;
- `created_at`.

Only `MANUAL` and `CUSTOMER_DATE_AMOUNT` exist. A reference-based method is
impossible: EasyBooks carries no sales order, quote, or contract number on any
observed line, so there is nothing to match a UniOps order number against.

## Derived states

None of these is stored. All are computed per request, so an EasyBooks sync
cannot leave a stale flag behind.

| State | Values | Basis |
| --- | --- | --- |
| `lifecycle_status` | the existing order workflow | UniOps |
| `accounting_status` | `NOT_INVOICED`, `INVOICE_CANDIDATE`, `INVOICED` | links and candidates |
| `payment_status` | `UNKNOWN` only | a source exists, but records no settlement |
| `due_status` | `UNKNOWN` only | `dueDate` exists in the source and is null throughout |

The production lifecycle and the accounting state are separate machines. The
order status enum is not extended with payment values, and nothing derives one
from the other.

`PaymentStatus` declares `UNPAID`, `PARTIALLY_PAID`, and `PAID`, and `DueStatus`
declares `DUE` and `OVERDUE`. Nothing returns them and no test asserts them.
They exist so the read model has somewhere to go the day settlement is actually
recorded in EasyBooks.

An invoice may only be called `OVERDUE` when a real due date is earlier than the
reporting date **and** an outstanding amount above zero is known. Neither input
exists, so nothing is ever reported overdue.

## Operational exceptions

Explicit categories, no severity scoring, each returning the rows behind the
count:

- `DELIVERED_ORDER_NOT_INVOICED`
- `INVOICE_WITHOUT_ORDER`
- `AMBIGUOUS_INVOICE_CANDIDATES`
- `LINKED_CUSTOMER_MISMATCH`
- `LINKED_AMOUNT_MISMATCH`
- `INVOICE_WITHOUT_CUSTOMER_CODE`

Every category is always present in the response, so "none found" is visibly
none found rather than a category that quietly stopped being computed.

## Reconciliation

Two link checks joined the pipeline's validate stage:

- a link pointing at an order or sales document that no longer exists;
- a link joining an order and an invoice belonging to **different customers** —
  one of the two is wrong, and neither side is rewritten. The warning names it
  and a person decides.

An order/invoice **amount** difference is deliberately not a sync warning.
Freight, tax handling, discounts, and one order split across several invoices all
produce legitimate differences. It is evidence for a person to read, surfaced
through the exceptions view, not a fault to flag on every sync.

## What this milestone can and cannot answer

| Question | Answer |
| --- | --- |
| Which EasyBooks invoice corresponds to this order? | Yes, once linked, with provenance |
| Which delivered orders have no invoice? | Yes |
| Which invoices are linked to no order? | Yes |
| How much has each customer been invoiced? | Yes |
| Which invoices are unpaid or partly paid? | **No** — no payment source |
| How much does each customer currently owe? | **No** — invoiced is known, settled is not |
| Which receivables are overdue? | **No** — no due date exists |
| Can every answer be traced to immutable source data? | Yes, through `source_raw_record_id` |

Those routes have since been captured — see
[EasyBooks receivables discovery](easybooks-receivables-discovery.md) — and the
answers are still no, for a different reason than before.

EasyBooks does expose customer debt and invoice-level open balances. What it does
not expose for this company is settlement: the amount collected is zero against
all 40 customers in every window tested, all 372 observed open items still carry
their full original amount, and `dueDate` and `paymentClause` exist as fields and
are null on every row. Roughly 29.7 billion VND of cash receipts and bank
deposits are recorded, but never offset against the invoices.

So `payment_status` and `due_status` stay `UNKNOWN`, and they now stay that way
on verified evidence rather than on an absent endpoint. What would change it is
the bookkeeping practice, not another capture — specifically, using
`Đối trừ chứng từ` to offset receipts against invoices. Until then the only
per-customer figure EasyBooks offers is gross of about 18.8 billion dong of
payments already banked. See
[EasyBooks receivables reconciliation](easybooks-receivables-reconciliation.md).
