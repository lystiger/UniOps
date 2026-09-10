# Finance & Accounting Policy Questions Awaiting Human Authority Validation

> **Boundary Reminder**: EasyBooks is the accounting system of record. UniOps does not guess, create, or alter accounting facts. The items listed below require explicit policy decisions and validation from the company bookkeeper, chief accountant, or finance director.

---

## 1. Authoritative Receivables & Debt Interpretation
* **Observed Reality**:
  * In the observed EasyBooks sales invoice payloads (`/v2/api/sa-invoice-objects-filter`), fields `mbDepositID` and `mcReceiptID` are `null` across all 111 observed documents.
  * In EasyBooks dynamic receivables reports (`/api/dynamic-report/cong-no-phai-thu`), bank receipt transactions are recorded against general customer codes but are not allocated or settled against specific sales invoice IDs.
* **Open Questions for Bookkeeper**:
  1. What is the official company procedure for matching customer bank deposits/cash receipts to individual sales invoices?
  2. Does the accounting department maintain an off-system allocation ledger (e.g. Excel) for invoice-level receivables aging, or is customer debt managed purely on an aggregate balance basis (Account 131)?
  3. Should UniOps display aggregate customer debt balances from Account 131, or wait until invoice-level receipt allocation is formally recorded in EasyBooks?

---

## 2. Paid / Unpaid Inference Semantics
* **Observed Reality**:
  * Because payment linkages do not exist on sales documents in EasyBooks, UniOps currently sets `payment_status = "UNKNOWN"` on all invoice cards and analytical summaries, explicitly displaying:
    > *"EasyBooks exposes no paid or outstanding amount on any observed sales document, and no payment source has been ingested."*
* **Open Questions for Bookkeeper**:
  1. Should an invoice ever be inferred as "PAID" based solely on FIFO (First-In, First-Out) matching of receipts to invoices?
  2. If partial payments occur, what threshold or rule distinguishes `PARTIALLY_PAID` from `PAID`?
  3. Should UniOps continue returning `null` / `UNKNOWN` until authoritative payment endpoints are connected?

---

## 3. Overdue Semantics & Due Date Rules
* **Observed Reality**:
  * The observed sales invoice payloads carry an issue date (`document_date` / `refDate`) but **no due date or payment term field** (`dueDate`, `termDays`, etc. are null or omitted).
* **Open Questions for Bookkeeper**:
  1. What are the standard credit terms (in days) per customer segment (e.g., net 15, net 30, net 60)?
  2. Is overdue calculated strictly from the invoice issue date (`refDate`) or from the operational delivery date?
  3. Does the company observe a grace period before classifying a customer balance as overdue for production holds?

---

## 4. Tax-Inclusive vs. Tax-Exclusive Figure Interpretation
* **Observed Reality**:
  * Sales documents expose `totalAmount` (gross total including VAT), `subtotal` (net total before VAT), and `vatAmount`.
  * Purchase dynamic reports expose `total_purchase_amount` and `vat_amount` (`thueGTGT`, which is an amount in VND, not a tax percentage).
* **Open Questions for Bookkeeper**:
  1. For executive KPIs and sales revenue metrics, should the company standard be **tax-exclusive** (`subtotal`) or **tax-inclusive** (`totalAmount`)?
  2. In candidate matching, UniOps matches order total against either invoice subtotal or total (scoring 0.40 confidence). Does operational order pricing agreed with customers include or exclude 8%/10% VAT by default?

---

## 5. Gross Commercial Flow vs. Profit / Cost Accounting
* **Observed Reality**:
  * UniOps calculates `sales_minus_purchases` on the Overview and Finance pages as simple commercial cashflow difference within the selected date window.
  * In `docs/data-architecture.md`, UniOps explicitly documents:
    > *"sales_minus_purchases is gross commercial flow, not profit. Purchases in a period are not the cost of the goods sold in that period, no period matching has been done, and nothing here is a margin."*
* **Open Questions for Bookkeeper**:
  1. How is Cost of Goods Sold (COGS, Account 632) recorded in EasyBooks (e.g., periodic inventory vs. perpetual inventory)?
  2. What allocation of raw materials (paper jumbo rolls) to production orders is acceptable for future gross margin reporting?

---

## 6. Summary of Action Items for Finance Pilot

| Question | Current UniOps Behavior | Decision Needed From Bookkeeper |
|---|---|---|
| Receivables balance | Displays `—` with explanation note | Authoritative source table for customer debt (Account 131 vs dynamic report) |
| Invoice payment status | Hardcoded `UNKNOWN` | Whether FIFO matching is permitted or explicit allocation required |
| Due dates | Displays `—` with `UNKNOWN` due status | Standard customer credit terms table (days) |
| Revenue KPI base | Displays gross total with separate VAT metric | Confirm whether Net or Gross is official revenue KPI |
| Profit metrics | Only displays `Sales − Purchases` | Provide official COGS methodology if margin reports are desired in V2 |
