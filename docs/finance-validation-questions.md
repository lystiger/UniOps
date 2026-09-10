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

## 6. Debit / Credit Interpretation for Future KPIs
* **Observed Reality**:
  * In the ingested EasyBooks raw data, debit and credit account fields (`tkNo` / `tkCo`) appear exclusively on purchase documents (54 / 54 purchase raw payloads, covering 71 line items). They do not appear on sales documents (0 / 111 sales documents, 0 / 111 sales lines carry `tkNo` or `tkCo`).
  * In the 71 observed purchase line records, the credit account (`tkCo`) is uniformly `331` (71 occurrences: trade payables to suppliers). The debit accounts (`tkNo`) are:
    * `152` (62 occurrences: Raw materials / Nguyên liệu, vật liệu)
    * `154` (6 occurrences: Manufacturing costs / Chi phí sản xuất dở dang)
    * `6421` (2 occurrences: Selling expenses / Chi phí bán hàng)
    * `6422` (1 occurrence: General administrative expenses / Chi phí quản lý doanh nghiệp)
    * In addition, `tkThueGTGT` appears as `1331` for deductible VAT.
  * Sales documents expose only currency amounts (`totalAmount`, `subtotal`, `vatAmount`) with no general ledger accounts. Accounts commonly used in Vietnamese accounting for sales (such as Account 511 for revenue or Account 131 for trade receivables) do not appear in the ingested sales payloads.
  * UniOps currently reads purchase `tkNo` and `tkCo` exclusively as raw hash inputs in `backend/app/integrations/easybooks/normalization.py:302-303` to construct unique line deduplication signatures (`_fallback_purchase_signature`). UniOps does not store them in database columns on `PurchaseLine` (or `SalesLine`), does not normalize them into domain models, and does not use them in any financial reporting or KPI calculations.
* **Open Questions for Bookkeeper**:
  1. Which specific general ledger account pairings (Nợ/Có) define recognized sales revenue (e.g. Account 511) vs deferred revenue for customer deposits?
  2. For receivables KPIs, should trade customer debt reflect the ending debit balance of Account 131 specifically, and how should credit balances (customer prepayments) be displayed? *(Cross-reference: see Topic 1 for customer debt and receivables aging policies).*
  3. When calculating gross commercial flow vs operating flow, which account transactions represent true third-party trade obligations versus internal adjustments?

---

## 7. Operational `INVOICED` and `CLOSED` Lifecycle vs. Invoice Linking
* **Observed Reality**:
  * The UniOps order lifecycle includes the progression `DELIVERED → INVOICED → CLOSED`.
  * The Order Board provides a manual "Mark invoiced" button when an order is in `DELIVERED` status.
  * In the current implementation, an operator can advance an order to `INVOICED` without a linked EasyBooks invoice; whether that is intended is open, see questions below.
  * Conversely, an order can have a confirmed invoice link while remaining in earlier operational stages (e.g. `IN_PRODUCTION`), because operational status and accounting status are tracked independently.
* **Open Questions for Bookkeeper & Management**:
  1. Should advancing an order to `INVOICED` strictly require at least one confirmed EasyBooks invoice link (blocking manual advancement if unlinked)?
  2. Or is operational `INVOICED` intended as a factory/office workflow signal (e.g., invoice request issued) independent of EasyBooks reconciliation?
  3. Under what conditions should an order transition to `CLOSED`: upon operational delivery, upon confirmed invoice linkage, or upon full cash settlement in EasyBooks?

---

## 8. Summary of Action Items for Finance Pilot

| Topic | Current UniOps Behavior | Decision Needed From Bookkeeper / Management |
|---|---|---|
| 1. Receivables balance | Displays `—` with explanation note | Authoritative source for customer debt (Account 131 ledger vs dynamic report) |
| 2. Invoice payment status | Hardcoded `UNKNOWN` | Whether FIFO matching is permitted or explicit allocation required |
| 3. Due dates & terms | Displays `—` with `UNKNOWN` due status | Standard customer credit terms table (days) and overdue calculation base |
| 4. Revenue KPI base | Displays gross total with separate VAT metric | Confirm whether Net or Gross is official revenue KPI |
| 5. Profit / margin metrics | Only displays `Sales − Purchases` | Provide official COGS methodology if margin reports are desired in V2 |
| 6. Debit / Credit KPIs | Purchases carry tkNo (152, 154, 6421, 6422) and tkCo (331); sales carry no ledger accounts. UniOps uses purchase accounts only for raw line hashing | Specify which ledger accounts (Nợ/Có) govern future financial reporting |
| 7. Operational Invoiced status | Allows advancing to `INVOICED` without invoice link | Confirm whether linking an invoice should be mandatory before `INVOICED` |

