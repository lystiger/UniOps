# EasyBooks receivables: source discovery

What EasyBooks can and cannot prove about invoice settlement, customer debt, and
payment allocation. Everything here was observed against the company account on
2026-09-09 by driving the EasyBooks web client and recording its own network
traffic. No endpoint was guessed from a naming pattern, and nothing was created,
updated, or deleted.

The short answer:

> EasyBooks exposes customer debt and invoice-level open balances through the
> customer-collection screen, and it exposes cash receipts and bank deposits as
> documents. It does **not** expose any invoice-level payment allocation for this
> company: no invoice has ever been marked settled, and the amount collected is
> zero against every customer.

That makes settlement state derivable only in one direction — an invoice that
appears in the open-items list is unpaid — and leaves "when was this paid" and
"which payment settled which invoice" unanswerable from the source as it stands.

## How these endpoints were found

The authenticated navigation DOM captured earlier lists the application's own
routes. Six of them are receivable- or payment-shaped, and each was opened in a
real signed-in session while every API call it made was recorded:

| Screen route | Vietnamese | What it is |
| --- | --- | --- |
| `/thu-tien-khach-hang` | Thu tiền khách hàng | Customer collection |
| `/phieu-thu` | Phiếu thu | Cash receipt voucher |
| `/bao-co` | Báo có | Bank credit advice (money in) |
| `/ban-hang/doi-tru-chung-tu` | Đối trừ chứng từ | Document offsetting — allocation |
| `/sao-ke-ngan-hang` | Sao kê ngân hàng | Bank statement |
| `/` | Trang chủ | Dashboard |

Only the routes those screens actually called are recorded below. Windows and
customer ids were varied afterwards to establish semantics; the paths and
parameter shapes are the ones the client itself sent.

## Observed endpoints

### Customer debt — `getSAReceiptDebit`

```text
GET /api/accounting-objects/getSAReceiptDebit
    ?fromDate=YYYY-MM-DD&toDate=YYYY-MM-DD&objectCode=&objectName=
```

Returns a plain JSON array, one row per customer. No envelope, no pagination
parameter, 40 rows for this company.

| Field | Meaning | Screen column |
| --- | --- | --- |
| `accountingObjectID` | customer UUID | — |
| `accountingObjectCode` | tax code | Mã đối tượng |
| `accountingObjectName` | name | Tên đối tượng |
| `soDuDauNam` | opening balance at window start | Số dư đầu kỳ |
| `soPhatSinh` | arising within window | Số phát sinh |
| `soDaThu` | **collected within window** | Số đã thu |
| `soConPhaiThu` | **closing amount still receivable** | Số còn phải thu |

### Invoice-level open items — `getSAReceiptDebitBill`

```text
GET /api/accounting-objects/getSAReceiptDebitBill
    ?fromDate=YYYY-MM-DD&toDate=YYYY-MM-DD&accountObjectID=<customer UUID>
```

One row per **open** document for that customer. 372 rows across the six
largest-balance customers.

| Field | Meaning |
| --- | --- |
| `referenceID` | the sales document UUID — joins to `sales_documents.source_id` |
| `date` | document date, `DD/MM/YYYY` |
| `noFBook` | financial book number, e.g. `BH104` |
| `invoiceNo` | invoice number |
| `dueDate` | **payment due date — present as a field, null on every row** |
| `paymentClause` | **payment term — present as a field, null on every row** |
| `totalCredit`, `totalCreditOriginal` | document total |
| `creditAmount`, `creditAmountOriginal` | amount still open |
| `account` | `131` on every row |
| `typeID` | `320` on 367 rows, `742` on 5 |
| `employeeID`, `employeeName`, `noMBook` | null on every row |

### Payment documents

```text
GET /api/m-c-receiptsDTO?page=0&size=N&searchVoucher={"fromDate":…,"toDate":…}
GET /api/mb-deposits/search-all?page=0&size=N
    &searchVoucher={"typeID":null,"statusRecorded":null,"currencyID":null,"fromDate":…,"toDate":…}
```

Cash receipts (`typeID` 100) and bank deposits (`typeID` 160). Both take real
server-side paging — unlike the sales list, `size` is honoured. Headers carry
`id`, `date`, `postedDate`, `noFBook`, `accountingObjectName`, `totalAmount`,
`recorded`, and for deposits `accountingObjectID` and `bankAccountDetailID`.

**Neither header carries any invoice reference.** The `Báo có` screen has a
lower detail area with two tabs, `HÀNG TIỀN` (money lines, with debit and credit
account columns) and `CHỨNG TỪ THAM CHIẾU` (reference documents) — so a per
document allocation surface exists in the product. Its endpoint was not
captured, because every document list filtered to the default window came back
empty and no row could be opened. See [What is still unknown](#what-is-still-unknown).

### Ledger and dashboard

```text
GET /api/trang-chu/so-du-tai-khoan
GET /api/trang-chu/bieu-do-no-phai-thu-tra?fromDate=…&toDate=…
```

Account balances by account number, including `131 Phải thu của khách hàng`, with
opening, movement, and closing debit and credit amounts. The chart route returns
two rows, `Phải thu khách hàng` and `Phải trả nhà cung cấp`.

Also observed and not pursued: `/api/bank-transaction/get-all-bank-transaction-without-page`
(bank statement lines).

## Classification

Per the rule that these categories must not be mixed:

### VERIFIED LIVE

| Fact | Evidence |
| --- | --- |
| Customer closing receivable balance | `soConPhaiThu`, 40 customers |
| Customer opening balance and period movement | `soDuDauNam`, `soPhatSinh` |
| Amount collected per customer per window | `soDaThu` — verified, and it is zero |
| Invoice-level open amount | `creditAmount` / `totalCredit`, 372 rows |
| Invoice identity of an open item | `referenceID`, joins to our `sales_documents` |
| Which invoices are still open | membership of the `getSAReceiptDebitBill` list |
| Cash receipts exist as documents | 83 rows, 3,498,680,441 VND |
| Bank deposits exist as documents | 414 rows, 26,240,363,515 VND |
| General-ledger 131 balance | `so-du-tai-khoan` |

The balance arithmetic was checked rather than assumed. For all 40 customers, in
every window tested:

```text
soDuDauNam + soPhatSinh - soDaThu == soConPhaiThu
```

And `soConPhaiThu` is a genuine as-of closing balance: the window's **end** date
is the "as of", and the figure is identical whether the window starts in 2024 or
in 2000.

| Window | opening | arising | collected | closing |
| --- | ---: | ---: | ---: | ---: |
| 2026-09-09 only | 22,751,078,855 | 0 | 0 | 22,751,078,855 |
| 2026 | 18,726,277,263 | 4,024,801,592 | 0 | 22,751,078,855 |
| 2025 | 8,761,858,283 | 9,964,418,980 | 0 | 18,726,277,263 |
| 2024–2026 | 841,072,534 | 21,910,006,321 | 0 | 22,751,078,855 |
| 2000–2026 | 841,072,534 | 21,910,006,321 | 0 | 22,751,078,855 |

### OBSERVED BUT NOT VERIFIED

- **The `CHỨNG TỪ THAM CHIẾU` allocation tab.** The tab exists on the bank-credit
  document. No document was opened, so its endpoint, shape, and whether it holds
  any rows are unknown.
- **The bill list returning 26 rows where the screen footer said 24.** Observed
  once on the today-window call. Not explained; possibly two rows the grid
  filters client-side.
- **`typeID` 742 on 5 of 372 open items.** Every other row is 320, a credit sale.
  What 742 is has not been established.
- **Server paging on the payment routes.** `size=500` returned 83 and 414 rows,
  which is consistent with paging that works and with there simply being fewer
  rows than the page size. Not separately proven.

### INFERRED

- **An invoice absent from `getSAReceiptDebitBill` has been settled.** This
  follows from the list being open items, but nothing in the payload states it,
  and with `soDaThu` at zero there is no settled invoice to confirm it against.
  It is not safe to build on yet.

### UNAVAILABLE

| Concept | Status |
| --- | --- |
| Invoice due date | field `dueDate` exists, **null on all 372 rows** |
| Payment term | field `paymentClause` exists, **null on all 372 rows** |
| Payment allocation to an invoice | no endpoint captured, and no allocated amount anywhere |
| Payment date for an invoice | unanswerable without allocation |
| Partially paid invoices | `creditAmount != totalCredit` on **0 of 372** rows |
| Paid amount per invoice | always zero by implication of the above |

## The finding that matters most

EasyBooks holds roughly **29.7 billion VND** of recorded money-in from customers:

```text
cash receipts     83 documents     3,498,680,441
bank deposits    414 documents    26,240,363,515
```

And the receivables report says **zero has been collected** from any of the 40
customers, in any window, with every one of the 372 open items still carrying its
full original amount.

Both statements come from EasyBooks. They are only compatible one way: the
receipts and deposits are recorded as cash movements but are **never offset
against the sales invoices**. The `Đối trừ chứng từ` screen exists to do exactly
that offsetting, and this company does not appear to use it.

The consequence for UniOps is specific. Invoice-level settlement cannot be
derived, not because the source lacks the capability, but because the data has
never been entered. A settlement model built now would report every invoice as
unpaid and would be indistinguishable from having no model at all.

## The contradiction, since resolved

Three EasyBooks-native receivable totals disagreed by up to thirteen times:

```text
getSAReceiptDebit, sum of soConPhaiThu      22,751,078,855
general ledger 131, closing debit            3,402,625,442   (closing credit 247,566,888)
dashboard "Phải thu khách hàng", 2026        1,717,272,006
```

They measure three different things, and the reconciliation is written up in
[EasyBooks receivables reconciliation](easybooks-receivables-reconciliation.md).
In short: the debt report is gross of about 18.8 billion dong of customer money
that has been banked but never offset against invoices; the ledger nets it; and
the dashboard is period movement rather than a balance.

The conclusion below stands, and the reason is now stronger: the debt report
cannot be published because it overstates by roughly seven times, and the ledger
figure that is correct is only available company-wide.

## What follows for the data model

Against the model-selection cases: this is **Case C with an invoice-level
refinement**, not Case B. There are no payment allocation records to model, so
`payment_documents` and `payment_allocations` would be tables with nothing true
to put in them.

What the source supports:

1. **A receivable snapshot, not a transaction table.** `getSAReceiptDebit` and
   `getSAReceiptDebitBill` answer "as of date X", and the closing figure changes
   with the window's end date. Rows are a report reading, not durable events, and
   must be stored as snapshots carrying `snapshot_as_of`, the customer, the
   balance, `source_raw_record_id`, and `sync_run_id`.
2. **Open-item membership at invoice level.** `referenceID` joins to
   `sales_documents.source_id`, already proven against live data: all 20 customer
   codes in our sales documents appear among the report's 40, and 62 of the 372
   observed open items match a document we already hold.
3. **Nothing about due dates.** `dueDate` and `paymentClause` exist and are empty,
   so `due_status` stays `UNKNOWN` and nothing is ever reported overdue. This is
   now a verified emptiness rather than an absent field.

Raw-first still applies: each report reading is preserved in
`easybooks_raw_records` under its own entity type before anything is normalized.
Suggested entity types, named for what the source actually is:

```text
customer_debt_snapshot     one getSAReceiptDebit reading
customer_open_items        one getSAReceiptDebitBill reading, per customer
cash_receipt               one m-c-receiptsDTO document
bank_deposit               one mb-deposits document
```

`payment` is deliberately not among them. What was found is a report snapshot and
two cash-document families, and forcing them into a payment entity would state a
relationship to invoices that does not exist.

## What is still unknown

Worth one more capture session, in priority order:

1. **Open a bank deposit and a cash receipt** with the list filtered to a window
   that actually contains rows, and record the `CHỨNG TỪ THAM CHIẾU` tab's
   endpoint. This is the one thing that could still turn up an allocation
   structure. The attempts here failed only because the date filter on those two
   screens has three matching inputs and the wrong one was filled.
2. **Ask the bookkeeper about the 6.7× gap** above. No amount of further capture
   settles it; it is a question about how the books are kept.
3. **`typeID` 742** on 5 open items.
4. **Whether `soDaThu` is ever non-zero** for any company using this EasyBooks
   instance — that would confirm the field populates when offsetting is used, and
   with it the whole settlement path.

## Reproducing this

The capture scripts are not checked in: they carry the operator's credentials in
their environment and drive a live production accounting system. They logged in
with `UNIOPS_EASYBOOKS_USERNAME` / `_PASSWORD`, confirmed the offered
organisation, opened each screen, and recorded every request and response. Header
values were never written to disk; only header names were kept, so no bearer
token appears in any artefact.

Verification passes re-issued the **same** observed routes with different date
windows by reusing the live session's own headers programmatically. That varies
parameter values on a captured route; it does not invent one.
