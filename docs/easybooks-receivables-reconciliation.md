# EasyBooks receivables: reconciling the three figures

Three EasyBooks-native numbers claim to describe what customers owe UniGreen and
disagree by a factor of thirteen. This document establishes what each one
measures, why they differ, and whether any of them can be treated as
authoritative.

All figures were read from the company account on 2026-09-09. Nothing was
created, updated, offset, or posted; every call is a GET.

**The answer in one sentence:** the debt report is a *gross open-item list* that
only decreases when a receipt is manually offset against an invoice, the general
ledger is a *double-entry balance* that decreases the moment cash is posted, and
the difference between them is roughly 18.8 billion dong of customer money that
has been banked but never allocated to the invoices it paid.

## 1. The three conflicting figures

| Source | Figure | What it turns out to be |
| --- | ---: | --- |
| Customer debt report | 22,751,078,855 | gross unallocated open items |
| General ledger 131 | 3,402,625,442 Dr / 247,566,888 Cr | true double-entry balance |
| Dashboard receivables | 1,717,272,006 | net receivable **movement** during 2026 |

They are not three estimates of one quantity. They are three different
quantities, and only one of them is a receivable balance.

## 2. Exact source endpoints

```text
GET /api/accounting-objects/getSAReceiptDebit
    ?fromDate=2000-01-01&toDate=2026-09-09&objectCode=&objectName=

GET /api/accounting-objects/getSAReceiptDebitBill
    ?fromDate=2000-01-01&toDate=2026-09-09&accountObjectID=<customer UUID>

GET /api/trang-chu/so-du-tai-khoan                    (no date parameters)

GET /api/trang-chu/bieu-do-no-phai-thu-tra?fromDate=…&toDate=…

GET /api/m-c-receiptsDTO?page=0&size=500&searchVoucher={"fromDate":…,"toDate":…}
GET /api/mb-deposits/search-all?page=0&size=500
    &searchVoucher={"typeID":null,"statusRecorded":null,"currencyID":null,"fromDate":…,"toDate":…}
```

## 3. Same-date reproduction, and one limitation

As of **2026-09-09**, window opening **2000-01-01** so that "arising" covers all
history:

| Measure | Value |
| --- | ---: |
| Debt report opening (`soDuDauNam`) | 841,072,534 |
| Debt report arising (`soPhatSinh`) | 21,910,006,321 |
| Debt report collected (`soDaThu`) | **0** |
| Debt report closing (`soConPhaiThu`) | **22,751,078,855** |
| Open items, 591 rows across 40 customers | **22,751,078,855** |
| GL 131 closing debit | **3,402,625,442** |
| GL 131 closing credit | 247,566,888 |
| GL 131 net | 3,155,058,554 |
| GL 131 accumulated debit | 21,041,955,620 |
| GL 131 accumulated credit | 18,703,129,600 |
| Dashboard receivables, 2026 | **1,717,272,006** |

**Limitation, stated rather than smoothed over.** `so-du-tai-khoan` accepts no
date parameters. Its balance is "as EasyBooks stands now", and it reported
`debitAmount` and `creditAmount` of zero for its own period while carrying
lifetime accumulations, so opening equals closing. It could not be pinned to
2026-09-09 the way the other two could. The comparison below is therefore
between a same-day debt report and a current ledger balance, which is sound only
because no receivable movement was posted between those points — itself an
assumption, not a verified fact.

## 4. Why they differ

### The debt report never subtracts payment

The debt report's own arithmetic holds for all 40 customers in every window
tested:

```text
soDuDauNam + soPhatSinh - soDaThu == soConPhaiThu
```

`soDaThu` is the only term that could reduce it, and it is **zero everywhere** —
every customer, every window from a single day to twenty-six years. The report
is a sum of documents that remain open, and a document leaves the list only when
it is offset. Nothing has ever been offset, so nothing has ever left.

### The ledger does subtract payment

Account 131 has accumulated **18,703,129,600** in credits. Something has been
crediting receivables all along. Matching the payment documents to the customers
carrying debt identifies what:

| | Rows | Amount |
| --- | ---: | ---: |
| Bank deposits, all | 414 | 26,240,363,515 |
| — to a debt-carrying customer | 291 | **18,830,359,648** |
| — other (interest, transfers, non-customers) | 123 | 7,410,003,867 |
| Cash receipts, all | 83 | 3,498,680,441 |
| — to a debt-carrying customer | 71 | 648,680,441 |

Customer bank deposits alone come to 18,830,359,648 against GL credits of
18,703,129,600 — **within 0.68%**. Their `reason` fields say plainly what they
are: *"Thu tiền bằng TGNH từ CÔNG TY CỔ PHẦN THƯƠNG MẠI VÀ DỊCH VỤ NGỌC HÀ"*,
money collected by bank transfer from a named customer.

### So the gap is unallocated cash

```text
debt report            22,751,078,855
less GL 131 credits   -18,703,129,600
                     ─────────────────
                        4,047,949,255
GL 131 net              3,155,058,554
residual                  892,890,701
```

The residual is the same order as the 868,050,701 difference between what the
debt report calls lifetime arising (21,910,006,321) and GL accumulated debits
(21,041,955,620). The two sides agree to about 1% without any adjustment being
invented to make them agree.

### The dashboard measures movement, not balance

Requesting the chart for different windows settles it:

| Window | Phải thu khách hàng |
| --- | ---: |
| 2026-09-01 … 2026-09-30 | **0** |
| 2024 | 151,528,738 |
| 2025 | 748,242,752 |
| 2026 | 1,717,272,006 |
| 2000 … 2026 | 2,313,986,020 |

A single month returning zero cannot be a balance — the company plainly owed
money in September 2026. The all-time figure of 2,313,986,020 sits within 1% of
GL 131's lifetime net movement (21,041,955,620 − 18,703,129,600 =
2,338,826,020). The dashboard is a *period movement* chart whose selector reads
"Năm nay", this year.

Comparing it with either of the other two was comparing a change to a level.

## 5. Per-customer breakdown

The debt report and the open-item report agree **exactly, for all 40 of 40
customers**. Sum of open items equals reported closing balance, delta zero, in
every case. 591 open items in total.

Largest balances:

| Customer code | Name | Closing | Open items | Δ | Rows |
| --- | --- | ---: | ---: | ---: | ---: |
| 0106837694 | THIÊN VƯƠNG PAPER | 6,680,799,000 | 6,680,799,000 | 0 | 114 |
| 0101394777 | NGỌC HÀ | 3,175,990,344 | 3,175,990,344 | 0 | 54 |
| 0101770580 | XÂY DỰNG VÀ THƯƠNG MẠI … | 1,801,326,492 | 1,801,326,492 | 0 | 47 |
| 0101394777-003 | NGỌC HÀ — Vĩnh Phúc branch | 1,545,593,503 | 1,545,593,503 | 0 | 62 |
| 0101394777-024 | NGỌC HÀ — branch | 897,372,000 | 897,372,000 | 0 | 13 |
| 0106643843 | SẢN XUẤT VÀ KINH DOANH … | 379,721,779 | 379,721,779 | 0 | 30 |
| 0100100618 | KIM KHÍ THĂNG LONG | 176,428,800 | 176,428,800 | 0 | 26 |

**There are no discrepancy customers.** The disagreement is not concentrated in
a handful of accounts, not a rounding artefact, and not a mapping error. It is a
single systematic difference in what the two reports count, applying uniformly.

A per-customer GL 131 breakdown could not be obtained — see
[what could not be established](#9-what-could-not-be-established).

## 6. Historical opening balances

The 841,072,534 opening balance is **6 rows carrying `typeID` 742**, against 585
rows of `typeID` 320 credit sales. The 742 total equals the reported
`soDuDauNam` exactly, which identifies 742 as the opening-balance carry-forward
document type.

They are genuine EasyBooks opening entries, presumably from system setup. Whether
the underlying debt was real at the time, and whether it has since been paid
outside EasyBooks, is not answerable from the API. It is a question for the
bookkeeper.

Note the scale: at 841,072,534 the opening balances are **3.7%** of the debt
report total. They are not the explanation for the gap.

## 7. Negative balances, advances, credits

None. Across 591 open items there is **no negative amount**, and **no customer
has a negative closing balance**. The debt report exposes gross receivables with
no advance, prepayment, or credit-balance rows at all.

GL 131 does carry a credit balance of 247,566,888 alongside its debit balance,
which is where customer credits would sit. The debt report shows no
corresponding rows, consistent with it being a debit-side open-item list rather
than a net position.

## 8. Account structure

Account 131 "Phải thu của khách hàng" is **flat**. The 40-account chart returned
by `so-du-tai-khoan` shows child subaccounts under 111 (1111), 112 (1121), 133
(1331) and 211 (2111), and **none under 131**. Every open item observed carries
`account: "131"` — all 591 of them.

There is no 1311/1312 split, no foreign-currency subaccount, and no separate
customer account to reconcile against. Currency is VND throughout.

## 9. What could not be established

Recorded as failures rather than omitted:

- **Posting lines of a receipt or deposit were never read.** The `Báo có` screen
  shows a `HÀNG TIỀN` detail grid with `TK Nợ` / `TK Có` columns and a
  `CHỨNG TỪ THAM CHIẾU` (reference documents) tab, which is where allocation
  would appear. Both list screens default to a window containing no rows, and
  their date inputs are datepicker-bound: their values can be read
  (`01/09/2026`, `09/09/2026`) but Playwright's `fill()` and `click()` both time
  out against them, so the window could not be widened and no row could be
  selected. That the deposits credit 131 is therefore **inferred from the 0.68%
  match**, not read off a posting line.
- **Per-customer GL 131 balances.** This needs a ledger or debt-detail report.
  The `BÁO CÁO` menu could not be opened — the left sidebar intercepts pointer
  events, and a DOM-level click returned only the process menus.
- **Historical offset records.** `/ban-hang/doi-tru-chung-tu` loaded lookup data
  only (currencies, account lists) and issued no data query, consistent with a
  screen that needs a customer chosen first. No historical offsets were seen. The
  evidence that offsetting is unused is indirect but strong: `soDaThu` is zero
  for every customer in every window, and all 591 open items still carry their
  full original amount.

## 10. Reconciliation matrix

| Source | Granularity | As-of? | Includes opening? | Nets credits? | Invoice-level? |
| --- | --- | --- | --- | --- | --- |
| Debt report `getSAReceiptDebit` | customer | yes, window end | yes (`typeID` 742) | **no** | no |
| Open items `getSAReceiptDebitBill` | document | yes, window end | yes | **no** | yes |
| GL 131 `so-du-tai-khoan` | account | now only, no date parameter | yes | **yes** | no |
| Dashboard `bieu-do-no-phai-thu-tra` | company | **no — period movement** | no | yes | no |
| Cash receipts `m-c-receiptsDTO` | document | period | n/a | n/a | no allocation |
| Bank deposits `mb-deposits/search-all` | document | period | n/a | n/a | no allocation |

## 11. Evidence classification

### VERIFIED LIVE

- Debt report internal arithmetic, all 40 customers, every window tested.
- `soDaThu` is zero for every customer in every window.
- Debt report closing equals sum of open items, exactly, for all 40 customers.
- `typeID` 742 totals 841,072,534 and equals the reported opening balance.
- No negative amounts and no negative customer balances in the debt report.
- Account 131 is flat; every open item posts to it.
- GL 131 balances and lifetime accumulations, as reported by `so-du-tai-khoan`.
- Dashboard returns 0 for September 2026 and differs by window, so it is not a
  balance.
- Payment document counts and totals, and how much belongs to debt-carrying
  customers.

### OBSERVED BUT NOT VERIFIED

- That the dashboard equals GL 131 net movement. The all-time figures agree to
  within 1% (2,313,986,020 vs 2,338,826,020); the residual is unexplained.
- That no receivable movement occurred between the debt report's as-of date and
  the ledger read, which the same-date comparison relies on.

### INFERRED

- **Customer bank deposits are the credits to account 131.** From a 0.68% match
  in magnitude and from `reason` text naming the customer, not from a posting
  line.
- **The gap is unallocated cash.** Follows from the above plus the arithmetic in
  section 4.

### UNRESOLVED

- Whether the opening balances represent debt that is still genuinely owed.
- Where the ~868 million debit-side difference between the debt report's
  "arising" and GL accumulated debits comes from.
- The 247,566,888 credit balance on 131 — which customers, and why.
- Whether the offsetting workflow has ever been used, as opposed to merely
  appearing unused.

## 12. Authoritative-source recommendation

**DO NOT PUBLISH RECEIVABLES YET.**

Not because no source is credible — GL 131 is credible — but because the number a
person would act on cannot be produced from it.

| Source | Classification | Reason |
| --- | --- | --- |
| GL 131 `so-du-tai-khoan` | **AUTHORITATIVE CANDIDATE** | true double-entry balance, reflects cash received |
| Debt report `getSAReceiptDebit` | **DIAGNOSTIC ONLY** | gross of ~18.8bn of received cash; overstates by ~7× |
| Open items `getSAReceiptDebitBill` | **SUPPORTING SOURCE** | correct document inventory, wrong amounts outstanding |
| Dashboard `bieu-do-no-phai-thu-tra` | **UNSUITABLE** | period movement, not a balance |
| Cash receipts / bank deposits | **SUPPORTING SOURCE** | prove money arrived; carry no invoice allocation |

The blocking problem is that GL 131 is only available **company-wide**. UniOps
needs "how much does *this customer* owe", and the only per-customer source is
the debt report, which is gross. Publishing it would tell UniGreen that
THIÊN VƯƠNG PAPER owes 6,680,799,000 when much of that has demonstrably been
paid into the company's bank account.

Two things would unblock this, in order of preference:

1. **The bookkeeper starts using `Đối trừ chứng từ`** to offset receipts against
   invoices. Then `soDaThu` populates, open items shrink to what is genuinely
   outstanding, and the debt report becomes both per-customer and correct. This
   is the real fix and it is an accounting-process fix, not a software one.
2. **A per-customer 131 ledger report is located** and verified to net cash. That
   would give a defensible per-customer balance without changing anyone's
   workflow, but it still leaves invoice-level settlement unknown.

Until one of those exists, `payment_status` and `due_status` stay `UNKNOWN` and
no outstanding figure is published. This is condition **D**: the accounting
workflow must be corrected before UniOps can publish receivables.

## 13. Questions for the accountant

Concrete and answerable:

1. When you decide how much a customer owes, which screen do you look at?
2. Do you use **Đối trừ chứng từ** after receiving a payment? If not, what tells
   you an invoice has been paid?
3. Bank deposits totalling about 18.8 billion are recorded against customers who
   still show the full invoice amount outstanding. Is that money considered to
   have settled those invoices?
4. Account 131 shows about 3.4 billion owed while the customer debt report shows
   about 22.75 billion. Which do you treat as correct?
5. The opening balances of 841,072,534 across 6 entries — where did they come
   from, and is that debt still owed?
6. Account 131 carries a credit balance of 247,566,888. Which customers are in
   credit, and why?
7. Do any customers pay in advance, or leave deposits?
8. Do you reconcile account 131 monthly? Against what?
9. Invoice due dates and payment terms are empty on every invoice. Are payment
   terms agreed with customers, and recorded anywhere?

## 14. What UniOps should build, and when

Nothing about receivables yet.

Once offsetting is in use — and only then — the shape is already clear from the
existing pipeline, and no layer needs to change:

1. Ingest `getSAReceiptDebit` and `getSAReceiptDebitBill` as **snapshots**, not
   transactions, under new raw entity types, preserving `snapshot_as_of`.
2. Join open items to `sales_documents` on `referenceID`, which is already proven
   against live data.
3. Derive `payment_status` per invoice from `creditAmount` against `totalCredit`,
   using the rules already documented in order-to-cash.
4. Leave `due_status` at `UNKNOWN` until due dates are actually entered.

Ingesting any of it before the offsetting question is settled would build a
pipeline whose numbers nobody can defend.
