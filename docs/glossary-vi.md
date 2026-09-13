# Vietnamese Terminology Glossary (Bảng thuật ngữ tiếng Việt)

> **DRAFT — requires owner and bookkeeper approval before the pilot. No term here is approved.**  
> *(BẢN THẢO — Cần chủ doanh nghiệp và kế toán trưởng phê duyệt trước khi thử nghiệm chính thức. Chưa có thuật ngữ nào được coi là quyết định cuối cùng).*

This document establishes the terminology used in the Vietnamese localization (`frontend/src/i18n/vi.ts`). Every entry is marked `DRAFT`. EasyBooks observed terms are preferred where applicable. Terms carrying accounting or financial implications are explicitly flagged.

### Status meanings used in the `Status` column

| Status | Meaning |
|---|---|
| `DRAFT` | Wording proposed by the build; still needs owner/bookkeeper review, but the underlying fact is one UniOps can observe. |
| `UNSUPPORTED` | **The source cannot produce this fact at all today.** The wording exists only to say so. It must never be replaced by a term that asserts the fact. |
| `NEEDS FINANCE CONFIRMATION` | The fact exists, but its official definition is a finance policy decision that has not been made. See [docs/finance-validation-questions.md](finance-validation-questions.md). |
| `FUTURE / UNVALIDATED` | Not implemented in V1. Listed so nobody assumes it exists. |

No entry in this document is `APPROVED`. Nothing below may be treated as final.

### Pilot 1 correction (2026-09-11)

The first pilot found that **`accounting.paymentStatus.UNKNOWN` = "Chưa có thông tin"** was read by one of two task participants as *"the customer definitely has not paid."* That is a conclusion UniOps has no data for. The wording was changed to **"Chưa có dữ liệu xác nhận thanh toán"** / **"No payment confirmation data"**, and a supporting note now names all four conclusions UniOps cannot draw. See section 5.

---

## 1. Navigation & Pages (Điều hướng & Trang)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `nav.overview` | Overview | Tổng quan | Tổng thể | `nav.overview`, page title | Standard executive summary terminology | DRAFT |
| `nav.orders` | Orders | Đơn hàng | Quản lý đơn hàng | `nav.orders`, page title | Standard manufacturing operational order term | DRAFT |
| `nav.finance` | Finance | Tài chính | Kế toán - Tài chính | `nav.finance`, page title | Broad domain term | DRAFT |
| `nav.data` | Data | Dữ liệu | Đồng bộ dữ liệu | `nav.data`, page title | Read-only EasyBooks ingestion history view | DRAFT |
| `nav.newOrder` | New order | Tạo đơn hàng | Thêm đơn hàng, Đơn mới | `nav.newOrder`, button | Action verb creating a new sales/production order | DRAFT |

---

## 2. Order Lifecycle Statuses & Action Buttons (Trạng thái & Thao tác Đơn hàng)

### Order Statuses (Trạng thái vòng đời)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `orders.status.DRAFT` | Waiting | Chờ xử lý | Bản nháp, Mới tạo | `orders.status.DRAFT`, `StatusBadge` | Factory intake stage awaiting confirmation | DRAFT |
| `orders.status.CONFIRMED` | Confirmed | Đã xác nhận | Đã duyệt | `orders.status.CONFIRMED`, `StatusBadge` | Confirmed by office/sales | DRAFT |
| `orders.status.SCHEDULED` | Scheduled | Đã lên lịch | Đã xếp lịch SX | `orders.status.SCHEDULED`, `StatusBadge` | Production queue scheduled | DRAFT |
| `orders.status.IN_PRODUCTION` | Producing | Đang sản xuất | Đang làm | `orders.status.IN_PRODUCTION`, `StatusBadge` | Active on plant machinery | DRAFT |
| `orders.status.READY` | Ready | Sẵn sàng giao | Đã hoàn thành | `orders.status.READY`, `StatusBadge` | Manufactured and packaged in warehouse | DRAFT |
| `orders.status.DELIVERY_PENDING` | Delivery pending | Chờ giao hàng | Đang chuyển | `orders.status.DELIVERY_PENDING`, `StatusBadge` | Handed to logistics/driver | DRAFT |
| `orders.status.DELIVERED` | Delivered | Đã giao hàng | Giao thành công | `orders.status.DELIVERED`, `StatusBadge` | Customer signed receipt | DRAFT |
| `orders.status.INVOICED` | Invoiced | Đã xuất HĐ (vận hành) | Đã lập HĐ, Báo kế toán | `orders.status.INVOICED`, `StatusBadge` | **Accounting Risk**: Operational status only. Distinguishable from accounting link status to avoid confusing factory progress with official EasyBooks invoice confirmation (Topic 7). | DRAFT |
| `orders.status.CLOSED` | Closed | Đã đóng | Hoàn tất | `orders.status.CLOSED`, `StatusBadge` | Archived from board | DRAFT |
| `orders.status.CANCELLED` | Cancelled | Đã hủy | Hủy đơn | `orders.status.CANCELLED`, `StatusBadge` | Terminated; blocked if invoices linked | DRAFT |

### Order Actions (Nút thao tác)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `orders.actions.confirm` | Confirm | Xác nhận đơn | Duyệt đơn | `OrderBoard` | Action advancing DRAFT -> CONFIRMED | DRAFT |
| `orders.actions.schedule` | Schedule | Lên lịch SX | Xếp lịch | `OrderBoard` | Action advancing CONFIRMED -> SCHEDULED | DRAFT |
| `orders.actions.startProduction` | Start production | Bắt đầu sản xuất | Cho vào máy | `OrderBoard` | Action advancing SCHEDULED -> IN_PRODUCTION | DRAFT |
| `orders.actions.markReady` | Mark ready | Báo sẵn sàng | Hoàn thành SX | `OrderBoard` | Action advancing IN_PRODUCTION -> READY | DRAFT |
| `orders.actions.sendToDelivery` | Send to delivery | Chuyển giao hàng | Xuất kho giao | `OrderBoard` | Action advancing READY -> DELIVERY_PENDING | DRAFT |
| `orders.actions.markDelivered` | Mark delivered | Đã giao hàng | Giao xong | `OrderBoard` | Action advancing DELIVERY_PENDING -> DELIVERED | DRAFT |
| `orders.actions.markInvoiced` | Mark invoiced | Đánh dấu đã xuất HĐ | Báo đã ra HĐ | `OrderBoard` | Advances DELIVERED -> INVOICED | DRAFT |
| `orders.actions.closeOrder` | Close order | Đóng đơn hàng | Hoàn tất | `OrderBoard` | Advances INVOICED -> CLOSED | DRAFT |
| `orders.actions.cancelOrder` | Cancel order | Hủy đơn hàng | Hủy đơn | `OrderBoard` | Cancellation button | DRAFT |
| `orders.actions.confirmCancel` | Cancel order {orderNumber}? This cannot be undone. | Bạn có chắc chắn muốn hủy đơn hàng {orderNumber}? Thao tác này không thể hoàn tác. | Hủy đơn {orderNumber}? | `OrderBoard` | Confirmation modal before cancel | DRAFT |

---

## 3. Board Columns & Pipeline Buckets (Cột Bảng & Phân nhóm Tiến độ)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `orders.columns.intake` | Intake | Tiếp nhận | Tiếp nhận đơn | `OrderBoard` | Contains DRAFT, CONFIRMED, SCHEDULED | DRAFT |
| `orders.columns.production` | Production | Sản xuất | Đang sản xuất | `OrderBoard` | Contains IN_PRODUCTION, READY | DRAFT |
| `orders.columns.delivery` | Delivery / delivered | Giao hàng / Đã giao | Vận chuyển & Giao hàng | `OrderBoard` | Contains DELIVERY_PENDING, DELIVERED | DRAFT |
| `orders.columns.invoiced` | Invoiced | Đã xuất HĐ | Hóa đơn | `OrderBoard` | Contains operational INVOICED orders | DRAFT |
| `overview.buckets.activeOrders` | Active orders | Đơn hàng đang xử lý | Tổng đơn đang chạy | `OverviewView` | Non-cancelled pipeline count | DRAFT |
| `overview.buckets.producing` | Producing | Đang sản xuất | Đang chạy | `OverviewView` | Count of IN_PRODUCTION | DRAFT |
| `overview.buckets.ready` | Ready | Sẵn sàng giao | Chờ xuất xưởng | `OverviewView` | Count of READY | DRAFT |
| `overview.buckets.deliveryPending` | Delivery pending | Chờ giao hàng | Đang giao | `OverviewView` | Count of DELIVERY_PENDING + DELIVERED | DRAFT |

---

## 4. Accounting & Invoice Link Statuses (Trạng thái Liên kết Hóa đơn Kế toán)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `accounting.status.NO_INVOICE` | No invoice | Chưa liên kết hóa đơn | Chưa có HĐ, Chưa gán HĐ | `AccountingPanel` | No EasyBooks invoice linked to order | DRAFT |
| `accounting.status.INVOICE_CANDIDATE` | Invoice candidate | Có hóa đơn gợi ý | Hóa đơn tiềm năng, Khớp dự kiến | `AccountingPanel` | Heuristic candidate found; no link created yet | DRAFT |
| `accounting.status.INVOICED` | Invoiced | Đã liên kết hóa đơn | Đã gán HĐ EasyBooks | `AccountingPanel` | **Accounting Term**: Confirmed relationship between UniOps order and EasyBooks invoice. Distinguishable from operational INVOICED. | DRAFT |
| `accounting.status.AMOUNT_MISMATCH` | Amount mismatch | Lệch số tiền | Không khớp giá trị | `AccountingPanel` | Order total differs from invoice subtotal & total | DRAFT |
| `accounting.status.OVER_INVOICED` | Over-invoiced | Hóa đơn vượt giá trị | Hóa đơn lớn hơn đơn | `AccountingPanel` | Invoiced amount exceeds order value | DRAFT |
| `accounting.actions.linkInvoice` | Link invoice | Liên kết hóa đơn | Gán hóa đơn | `AccountingPanel` | Drawer action | DRAFT |
| `accounting.actions.unlink` | Unlink | Hủy liên kết | Gỡ liên kết | `AccountingPanel` | Removes relationship in UniOps | DRAFT |
| `accounting.confidence` | Confidence | Độ tin cậy | Mức độ khớp | `AccountingPanel` | Heuristic score (e.g. 100%, 80%) | DRAFT |
| `accounting.suggested` | Suggested EasyBooks invoices | Hóa đơn EasyBooks gợi ý | Danh sách HĐ phù hợp | `AccountingPanel` | Heuristic match drawer section | DRAFT |
| `accounting.outstandingExposesNote` | EasyBooks exposes no paid or outstanding amount on any observed sales document, and no payment source has been ingested | EasyBooks không thể hiện số tiền đã thanh toán hay còn nợ trên bất kỳ chứng từ bán hàng nào đã ghi nhận, và chưa đồng bộ nguồn thanh toán | Không có số liệu công nợ trên EasyBooks | `AccountingPanel`, `FinanceView` | **Accounting Critical**: Explains why outstanding is `—` rather than zero (Topic 1). | DRAFT |
| `accounting.linkMethod.MANUAL` | Linked manually | Liên kết thủ công | Gán thủ công | `AccountingPanel` | Shown instead of the raw `MANUAL` code | DRAFT |
| `accounting.linkMethod.CUSTOMER_DATE_AMOUNT` | Matched by customer, date and amount | Khớp theo khách hàng, ngày và số tiền | Khớp tự động | `AccountingPanel` | Shown instead of the raw `CUSTOMER_DATE_AMOUNT` code | DRAFT |

---

## 5. Payment Status (Trạng thái Thanh toán)

> **All payment terminology below is `UNSUPPORTED`, not provisional wording awaiting a nicer phrase.** EasyBooks exposes no payment allocation on any observed sales document (`mbDepositID` and `mcReceiptID` are null on all 111). UniOps therefore has no data from which to conclude *đã trả*, *chưa trả*, *trả một phần*, or *quá hạn*. The only reachable state is `UNKNOWN`; `UNPAID`, `PARTIALLY_PAID` and `PAID` are declared in the code but unreachable and must not appear in any screen, document, or translation until a payment source is ingested **and** the bookkeeper has confirmed the matching rule (Topic 1 and Topic 2 of [docs/finance-validation-questions.md](finance-validation-questions.md)).

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `accounting.paymentStatus.UNKNOWN` | No payment confirmation data | Chưa có dữ liệu xác nhận thanh toán | *(none — see note)* | `AccountingPanel` | **Accounting Critical**: names the missing data, not a settlement. The previous "Chưa có thông tin" was misread in Pilot 1 as "chưa thanh toán". Must NEVER be replaced by "Chưa thanh toán", "Đã thanh toán", "Trả một phần" or "Quá hạn". | UNSUPPORTED |
| `accounting.paymentUnknownNote` | UniOps does not currently have enough data to determine whether the invoice is paid, unpaid, partially paid, or overdue. Check EasyBooks for confirmation. | UniOps chưa có đủ dữ liệu để kết luận đã trả, chưa trả, trả một phần hoặc quá hạn. Hãy kiểm tra EasyBooks. | — | `AccountingPanel` | **Accounting Critical**: states all four conclusions UniOps cannot draw, and names EasyBooks as where the answer lives. | UNSUPPORTED |
| `accounting.paymentStatus.UNPAID` | Unpaid | Chưa thanh toán | — | *(unreachable)* | **Do not display.** No observed EasyBooks field supports it. | UNSUPPORTED |
| `accounting.paymentStatus.PARTIALLY_PAID` | Partially paid | Thanh toán một phần | — | *(unreachable)* | **Do not display.** Requires both a payment source and a bookkeeper-confirmed partial-payment threshold (Topic 2.2). | UNSUPPORTED |
| `accounting.paymentStatus.PAID` | Paid | Đã thanh toán | — | *(unreachable)* | **Do not display.** Requires a bookkeeper-confirmed receipt-to-invoice allocation rule (Topic 2.1). | UNSUPPORTED |
| `common.unsupportedValue` | No confirmation data | Chưa có dữ liệu xác nhận | Chưa có số liệu | `AccountingPanel`, `FinanceView`, `OverviewView` | **Accounting Critical**: the shared treatment for a figure the source cannot produce. Deliberately distinct from a zero, from an empty result, and from `common.loadFailedValue` (a request that failed). Rendered muted, never as a warning. | UNSUPPORTED |
| `common.loadFailedValue` | Could not load | Không tải được | — | `FinanceView`, `OverviewView` | A failed request, which retrying may fix. Must not be confused with an unsupported figure. | DRAFT |

### 5.1 Receivable, overdue and VAT terminology — not yet confirmed

| Key | Vietnamese draft | What is unresolved | Status |
|---|---|---|---|
| `finance.receivablesOutstanding` | Số dư công nợ chưa thu | Which EasyBooks report is the official source of a customer balance — the `cong-no-phai-thu` dynamic report or the Account 131 ledger — is a bookkeeper decision (Topic 1). UniOps returns `null`, never `0`. | NEEDS FINANCE CONFIRMATION |
| `finance.columns.outstanding` | Còn phải thu | Same as above, per invoice. Currently always rendered via `common.unsupportedValue`. | NEEDS FINANCE CONFIRMATION |
| *(overdue semantics)* | Quá hạn thanh toán | No due date exists on any observed sales document, and standard credit terms per customer have not been supplied (Topic 3). UniOps reports `due_status = UNKNOWN` and must never compute overdue from the invoice date alone. Distinct from `orders.overdueDelivery` ("Trễ hạn giao"), which is a **delivery** deadline and is supported. | NEEDS FINANCE CONFIRMATION |
| `finance.stats.vat` | Thuế GTGT | Whether the official sales figure is before VAT (`subtotal`) or after VAT (`totalAmount`) is a policy decision, not a display preference (Topic 4). UniOps currently shows the gross total with VAT as a separate figure, and this is **not** confirmed as the company standard. | NEEDS FINANCE CONFIRMATION |
| *(payables / công nợ phải trả)* | Công nợ phải trả | Not implemented in V1. No supplier-balance figure exists anywhere in the product. Listed here only so that its absence is not mistaken for a zero. | FUTURE / UNVALIDATED |

---

## 6. Synchronization Statuses (Trạng thái Đồng bộ EasyBooks)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `sync.status.SUCCEEDED` | Success | Thành công | Hoàn tất | `format.ts`, `DataView` | All records ingested cleanly | DRAFT |
| `sync.status.PARTIAL` | Partial | Một phần | Thành công một phần | `format.ts`, `DataView` | Header stored, detail lines failed for some | DRAFT |
| `sync.status.FAILED` | Failure | Thất bại | Lỗi đồng bộ | `format.ts`, `DataView` | Sync terminated with fatal error | DRAFT |
| `sync.status.RUNNING` | Running | Đang đồng bộ | Đang chạy | `format.ts`, `DataView` | Ingestion job in progress | DRAFT |
| `data.syncError.documentsFailed` | Could not read {n} document(s) from EasyBooks | Không thể đọc {n} chứng từ từ EasyBooks | — | `DataView` | "Chứng từ", not "hóa đơn": a sync reads every document type | DRAFT |
| `data.syncError.stopped` | Sync stopped because of an error | Đồng bộ bị dừng do gặp lỗi | Đồng bộ thất bại | `DataView` | Fatal error before any document was counted as failed | DRAFT |
| `data.syncError.technicalDetails` | Technical details | Chi tiết kỹ thuật | Chi tiết lỗi | `DataView` | Collapsed by default; holds EasyBooks' untranslated error text for debugging | DRAFT |

---

## 7. User Roles (Vai trò Người dùng)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `roles.ADMIN` | Admin | Quản trị viên | Quản trị hệ thống | `AccountMenu`, `types.ts` | Full access + user management | DRAFT |
| `roles.OFFICE` | Office | Khối văn phòng | Nhân viên kinh doanh / điều phối | `AccountMenu`, `types.ts` | Order creation, editing, invoice linking | DRAFT |
| `roles.FACTORY_READ` | Factory · read only | Khối xưởng · Chỉ xem | Phân xưởng sản xuất (chỉ xem) | `AccountMenu`, `types.ts` | Plant floor read-only order monitoring | DRAFT |

---

## 8. Finance Terms (Thuật ngữ Tài chính)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `finance.sales` | Sales | Doanh số bán hàng | Doanh số | `FinanceView`, tabs | **Accounting Critical**: "Doanh số" represents gross commercial invoice volume, NOT recognized accounting revenue ("Doanh thu") (Topic 4). | DRAFT |
| `finance.purchases` | Purchases | Chi mua hàng | Chi phí mua hàng, Mua vào | `FinanceView`, tabs | Total purchase invoice volume | DRAFT |
| `finance.salesMinusPurchases` | Sales − purchases | Dòng thương mại (Bán − Mua) | Chênh lệch thương mại | `FinanceView`, `OverviewView` | **Accounting Critical**: MUST NOT be translated as "Lợi nhuận" (Profit), "Lãi", or "Biên độ" (Margin). This is gross commercial cashflow (Topic 5). Verified in the Pilot 1 corrective pass: no backend field, schema, or screen labels it as profit. | NEEDS FINANCE CONFIRMATION |
| `finance.receivables` | Receivables | Công nợ phải thu | Theo dõi công nợ | `FinanceView`, tabs | Sourced directly from EasyBooks report path `cong-no-phai-thu`. | DRAFT |
| `finance.receivablesOutstanding` | Receivables outstanding | Số dư công nợ chưa thu | Nợ phải thu | `FinanceView`, `OverviewView` | Value is unsupported at the source and renders as `common.unsupportedValue`, never as `0 ₫` and never as the bare `—` a failed load would leave (Topic 1). See §5.1. | NEEDS FINANCE CONFIRMATION |
| `finance.salesVat` | Output VAT | Thuế GTGT đầu ra | Thuế GTGT bán ra | `FinanceView` | VAT on sales documents. Whether the headline sales figure should be before or after VAT is unconfirmed (Topic 4); see §5.1. | NEEDS FINANCE CONFIRMATION |
| `finance.purchaseVat` | Input VAT | Thuế GTGT đầu vào | Thuế GTGT khấu trừ | `FinanceView` | VAT on purchase documents. Same open question as above. | NEEDS FINANCE CONFIRMATION |

---

## 9. Overview & Needs Attention (Tổng quan & Cần xử lý)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `overview.attention.title` | Needs attention | Cần xử lý | Cảnh báo cần chú ý | `OverviewView` | Operational exception section | DRAFT |
| `overview.attention.orderExceptions` | Order exceptions | Vấn đề đơn hàng | Lỗi đơn hàng | `OverviewView` | Group heading for order issues | DRAFT |
| `overview.attention.noOrderExceptions` | No order exceptions | Không có vấn đề đơn hàng | Không có lỗi đơn hàng | `OverviewView` | Empty state when count is 0 | DRAFT |
| `overview.attention.invoiceBacklog` | Invoice backlog & data issues | Tồn đọng hóa đơn & dữ liệu | Hóa đơn chưa khớp & lỗi dữ liệu | `OverviewView` | Group heading for invoice issues | DRAFT |
| `overview.attention.orderIssuesCount` | {n} order issue(s) | {n} vấn đề đơn hàng | {n} đơn hàng cần xử lý | `OverviewView` | Dynamic pluralization count | DRAFT |
| `overview.attention.invoiceIssuesCount` | {n} invoice issue(s) | {n} vấn đề hóa đơn | {n} hóa đơn cần xử lý | `OverviewView` | Dynamic pluralization count | DRAFT |
| `overview.overdueDelivery` | Overdue | Trễ hạn giao | Quá hạn giao hàng | `OrderBoard` | **Accounting Critical**: Delivery deadline has passed. Must NEVER be translated as "Quá hạn thanh toán" (Payment overdue). | DRAFT |
| `overview.attention.unknownIssue` | Needs review | Cần kiểm tra | Cần xem lại | `OverviewView` | Fallback for an issue category the UI doesn't know yet, so the backend's English detail never shows | DRAFT |

### Attention Issues Categories (`overview.attentionIssues.*`)

| Category | English text | Vietnamese draft | Notes / risk | Status |
|---|---|---|---|---|
| `DELIVERED_ORDER_NOT_INVOICED` | Delivered order has no confirmed EasyBooks invoice link | Đơn hàng đã giao chưa có liên kết hóa đơn EasyBooks | Operational order delivered without accounting invoice | DRAFT |
| `INVOICE_WITHOUT_ORDER` | Invoice has no linked UniOps order | Hóa đơn chưa liên kết với đơn hàng UniOps nào | Ingested invoice unlinked | DRAFT |
| `AMBIGUOUS_INVOICE_CANDIDATES` | Invoice matches multiple order candidates with equal confidence | Hóa đơn khớp với nhiều đơn hàng có cùng độ tin cậy | Multiple candidates require human selection | DRAFT |
| `LINKED_CUSTOMER_MISMATCH` | Linked invoice customer differs from order customer | Khách hàng trên hóa đơn khác với khách hàng của đơn hàng | Discrepancy warning | DRAFT |
| `LINKED_AMOUNT_MISMATCH` | Order total {orderTotal} matches neither invoice subtotal {invoiceSubtotal} nor total {invoiceTotal} | Tổng tiền đơn hàng {orderTotal} không khớp với tiền hàng {invoiceSubtotal} hoặc tổng tiền {invoiceTotal} của hóa đơn | Shows exact numeric VND amounts | DRAFT |
| `INVOICE_WITHOUT_CUSTOMER_CODE` | Invoice has no customer code | Hóa đơn không có mã đối tượng pháp nhân | Missing `accounting_object_code` in EasyBooks | DRAFT |

---

## 10. Common Actions, Labels & Dialogs (Thao tác, Nhãn & Hộp thoại Chung)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Status |
|---|---|---|---|---|---|
| `common.save` | Save | Lưu | Lưu lại | Forms, dialogs | DRAFT |
| `common.datePlaceholder` | dd/mm/yyyy | ngày/tháng/năm | nn/tt/nnnn | `DateInput` (Finance filter, New order) | Placeholder of the day-first date field; the field never follows the browser's date order | DRAFT |
| `common.invalidDate` | Not a valid date. Type day/month/year, e.g. 31/12/2026. | Ngày không hợp lệ. Nhập theo dạng ngày/tháng/năm, ví dụ 31/12/2026. | Sai định dạng ngày | `DateInput` | Shown as the field's validation message; the form will not submit | DRAFT |
| `common.dateOutOfRange` | This date is outside the allowed range. | Ngày nằm ngoài khoảng cho phép. | Ngày không hợp lệ | `DateInput` | e.g. a required date before the order date, or From after To | DRAFT |
| `common.cancel` | Cancel | Hủy | Bỏ qua | Dialogs, modals | DRAFT |
| `common.close` | Close | Đóng | Thoát | Modals, drawers | DRAFT |
| `common.search` | Search | Tìm kiếm | Tra cứu | Inputs | DRAFT |
| `common.loading` | Loading… | Đang tải… | Vui lòng chờ… | Spinners, skeletons | DRAFT |
| `common.empty` | No data | Không có dữ liệu | Trống | Empty state | DRAFT |
| `common.required` | Required | Bắt buộc | Cần điền | Form indicators | DRAFT |
| `common.optional` | Optional | Không bắt buộc | Tùy chọn | New order field markers | Shown beside a label as "(không bắt buộc)"; `aria-hidden`, because the control's own `required` attribute is what a screen reader announces | DRAFT |
| `newOrder.requiredLegend` | Fields marked * are required. | Các trường có dấu * là bắt buộc. | — | New order form | Explains the `*` once, so the marker is never colour-only | DRAFT |
| `newOrder.descriptionHelp` | Filled in from the product you choose; you can edit it. | Tự động điền theo sản phẩm đã chọn; có thể sửa lại. | — | New order line | Pilot 1: 1 of 2 respondents found 1–2 fields unclear | DRAFT |
| `newOrder.quantityHelp` | Counted in the unit named beside it. | Tính theo đơn vị ghi ở ô bên cạnh. | — | New order line | Ties the quantity to the unit field beside it | DRAFT |
| `newOrder.agreedPriceHelp` | Price for one unit, in Vietnamese dong (₫). | Đơn giá cho một đơn vị, tính bằng đồng (₫). | — | New order line | **Deliberately silent on VAT**: whether agreed order pricing includes VAT is unvalidated (Topic 4.2). Do not add "chưa VAT" or "đã VAT" until the bookkeeper confirms. | NEEDS FINANCE CONFIRMATION |
| `newOrder.errors.quantityInvalid` | Quantity must be a number greater than 0. | Số lượng phải là một số lớn hơn 0. | — | New order form | Replaces a generic API "request invalid" with the field at fault | DRAFT |
| `orders.nextStep` | Next step: | Bước tiếp theo: | Việc tiếp theo | `OrderBoard`, read-only roles | Names the next lifecycle step as text for `FACTORY_READ`, which has no control to advance it | DRAFT |
| `firstUse.body` | UniOps brings order information, EasyBooks data, and sync status together in one place. Some financial information still has to be checked directly in EasyBooks. | UniOps tập trung thông tin đơn hàng, dữ liệu EasyBooks và trạng thái đồng bộ tại một nơi. Một số thông tin tài chính vẫn cần kiểm tra trực tiếp trong EasyBooks. | — | First-use callout, dismissed once | Pilot 1 facilitator note: "cũng phải mất thời gian để làm quen" | DRAFT |
| `auth.signIn` | Sign in | Đăng nhập | Đăng nhập hệ thống | Login form | DRAFT |
| `auth.signingIn` | Signing in… | Đang đăng nhập… | Đang xác thực… | Login button | DRAFT |
| `auth.username` | Username | Tên đăng nhập | Tài khoản | Login input | DRAFT |
| `auth.password` | Password | Mật khẩu | Mã bảo mật | Login input | DRAFT |
| `auth.changePassword` | Change password | Đổi mật khẩu | Thay đổi mật khẩu | Account menu | DRAFT |
| `auth.signOut` | Sign out | Đăng xuất | Thoát tài khoản | Account menu | DRAFT |
| `dateFilter.calendar` | Calendar | Lịch | Chọn khoảng ngày | DateRangeFilter trigger | DRAFT |
| `dateFilter.thisMonth` | This Month | Tháng này | Tháng hiện tại | DateRangeFilter preset | DRAFT |
| `dateFilter.lastMonth` | Last Month | Tháng trước | Tháng vừa rồi | DateRangeFilter preset | DRAFT |
| `dateFilter.last3Months` | Last 3 Months | 3 tháng gần nhất | Quý gần nhất | DateRangeFilter preset | DRAFT |
| `dateFilter.lastYear` | Last Year | Năm trước | Năm ngoái | DateRangeFilter preset | DRAFT |
| `dateFilter.clear` | Clear | Xóa bộ lọc | Bỏ chọn | DateRangeFilter preset | DRAFT |
| `dateFilter.from` | From | Từ ngày | Từ | DateRangeFilter input | DRAFT |
| `dateFilter.to` | To | Đến ngày | Đến | DateRangeFilter input | DRAFT |

---

## 11. Loading Screen Proverbs (Tục ngữ Màn hình Khởi động)

Short Vietnamese proverbs about diligence and work, attributed to "Tục ngữ" (5 entries):

1. **"Có công mài sắt, có ngày nên kim."** — *Tục ngữ*  
   *(Meaning: Diligence and perseverance overcome any hardship).*
2. **"Vạn sự khởi đầu nan, gian nan đừng nản."** — *Tục ngữ*  
   *(Meaning: Everything is hard at the beginning; stay steadfast).*
3. **"Muốn biết phải hỏi, muốn giỏi phải học."** — *Tục ngữ*  
   *(Meaning: Inquire to know, learn to excel).*
4. **"Chớ thấy sóng cả mà ngã tay chèo."** — *Tục ngữ*  
   *(Meaning: Do not drop the oars when the waves run high).*
5. **"Cần cù bù thông minh."** — *Tục ngữ*  
   *(Meaning: Diligence and hard work compensate for everything).*

---

## 12. Questions Awaiting Human Authority Validation (Câu hỏi dành cho Chủ doanh nghiệp & Kế toán trưởng)

1. **Thuật ngữ Doanh số vs Doanh thu (Topic 4)**:
   - Bản thảo sử dụng **"Doanh số bán hàng"** cho tổng giá trị hóa đơn xuất ra, tránh dùng "Doanh thu" vì chưa có chuẩn ghi nhận doanh thu. Kế toán trưởng có đồng ý giữ phân biệt này không?
2. **Chênh lệch Dòng thương mại Bán − Mua (Topic 5)**:
   - Bản thảo dùng **"Dòng thương mại (Bán − Mua)"** thay vì "Lợi nhuận" hay "Lãi gộp" vì chưa tính giá vốn thành phẩm (Account 632) và phân bổ phôi giấy cuộn. Kế toán trưởng có đồng ý cách gọi này trên màn hình Quản trị không?
3. **Thuật ngữ Đã xuất hóa đơn: Vận hành vs Kế toán (Topic 7)**:
   - UniOps hiện cho phép nhân viên vận hành bấm **"Đánh dấu đã xuất HĐ"** trên bảng đơn hàng để báo hiệu tiến độ, trong khi drawer kế toán hiển thị **"Đã liên kết hóa đơn"** chỉ khi có hóa đơn EasyBooks thực tế. Bản thảo phân biệt thành `Đã xuất HĐ (vận hành)` và `Đã liên kết hóa đơn (EasyBooks)`. Chủ doanh nghiệp có muốn giữ hai thuật ngữ riêng biệt này không?
4. **Cảnh báo Trễ hạn giao hàng (Topic 3)**:
   - Trên thẻ đơn hàng, nhãn **"Trễ hạn giao"** được kích hoạt khi ngày cần hàng (`required_date`) đã qua mà đơn chưa giao. Xin xác nhận KHÔNG dùng từ "Quá hạn" đơn thuần để tránh nhân viên nhầm lẫn với quá hạn thanh toán công nợ.
5. **Trạng thái Thanh toán Hóa đơn (Topic 2)**:
   - Sau đợt thử nghiệm thứ nhất, bản thảo đã đổi từ **"Chưa có thông tin"** sang **"Chưa có dữ liệu xác nhận thanh toán"**, kèm câu giải thích: *"UniOps chưa có đủ dữ liệu để kết luận đã trả, chưa trả, trả một phần hoặc quá hạn. Hãy kiểm tra EasyBooks."* Xin xác nhận cách diễn đạt này, và xác nhận UniOps tuyệt đối không suy đoán "Chưa thanh toán" khi chưa có chứng từ thu tiền.
6. **Nguồn chính thức của số dư công nợ (Topic 1)**:
   - Trong EasyBooks, báo cáo nào hiện được dùng làm **nguồn chính thức** cho số dư công nợ phải thu của khách hàng? Xin nêu đúng tên báo cáo và người có thẩm quyền xác nhận quy tắc này.
7. **Doanh số trước hay sau VAT (Topic 4)**:
   - Theo quy định/sổ sách hiện tại, con số doanh số **chính thức** là trước VAT hay sau VAT? Đây là câu hỏi về quy định, không phải về sở thích hiển thị.
8. **Công nợ phải trả (chưa có trong V1)**:
   - UniOps hiện **không** có bất kỳ số liệu công nợ phải trả nào. Xin xác nhận điều này không bị hiểu nhầm là "bằng 0".
