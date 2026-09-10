# Vietnamese Terminology Glossary (Bảng thuật ngữ tiếng Việt)

> **DRAFT — requires owner and bookkeeper approval before the pilot. No term here is approved.**  
> *(BẢN THẢO — Cần chủ doanh nghiệp và kế toán trưởng phê duyệt trước khi thử nghiệm chính thức. Chưa có thuật ngữ nào được coi là quyết định cuối cùng).*

This document establishes the terminology used in the Vietnamese localization (`frontend/src/i18n/vi.ts`). Every entry is marked `DRAFT`. EasyBooks observed terms are preferred where applicable. Terms carrying accounting or financial implications are explicitly flagged.

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

---

## 5. Payment Status (Trạng thái Thanh toán)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `accounting.paymentStatus.UNKNOWN` | Unknown | Chưa có thông tin | Chưa rõ, Chưa xác định | `AccountingPanel`, `FinanceView` | **Accounting Critical**: EasyBooks does not expose payment allocation on sales invoices. Must NEVER be translated as "Chưa thanh toán" (Unpaid). | DRAFT |

---

## 6. Synchronization Statuses (Trạng thái Đồng bộ EasyBooks)

| Key | English UI text | Vietnamese draft | Alternatives | Where used | Notes / risk | Status |
|---|---|---|---|---|---|---|
| `sync.status.SUCCEEDED` | Success | Thành công | Hoàn tất | `format.ts`, `DataView` | All records ingested cleanly | DRAFT |
| `sync.status.PARTIAL` | Partial | Một phần | Thành công một phần | `format.ts`, `DataView` | Header stored, detail lines failed for some | DRAFT |
| `sync.status.FAILED` | Failure | Thất bại | Lỗi đồng bộ | `format.ts`, `DataView` | Sync terminated with fatal error | DRAFT |
| `sync.status.RUNNING` | Running | Đang đồng bộ | Đang chạy | `format.ts`, `DataView` | Ingestion job in progress | DRAFT |

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
| `finance.salesMinusPurchases` | Sales − purchases | Dòng thương mại (Bán − Mua) | Chênh lệch thương mại | `FinanceView`, `OverviewView` | **Accounting Critical**: MUST NOT be translated as "Lợi nhuận" (Profit), "Lãi", or "Biên độ" (Margin). This is gross commercial cashflow (Topic 5). | DRAFT |
| `finance.receivables` | Receivables | Công nợ phải thu | Theo dõi công nợ | `FinanceView`, tabs | Sourced directly from EasyBooks report path `cong-no-phai-thu`. | DRAFT |
| `finance.receivablesOutstanding` | Receivables outstanding | Số dư công nợ chưa thu | Nợ phải thu | `FinanceView` | Value is unknown (`—`) due to missing payment allocations (Topic 1). | DRAFT |
| `finance.salesVat` | Output VAT | Thuế GTGT đầu ra | Thuế GTGT bán ra | `FinanceView` | VAT on sales documents | DRAFT |
| `finance.purchaseVat` | Input VAT | Thuế GTGT đầu vào | Thuế GTGT khấu trừ | `FinanceView` | VAT on purchase documents | DRAFT |

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
| `common.cancel` | Cancel | Hủy | Bỏ qua | Dialogs, modals | DRAFT |
| `common.close` | Close | Đóng | Thoát | Modals, drawers | DRAFT |
| `common.search` | Search | Tìm kiếm | Tra cứu | Inputs | DRAFT |
| `common.loading` | Loading… | Đang tải… | Vui lòng chờ… | Spinners, skeletons | DRAFT |
| `common.empty` | No data | Không có dữ liệu | Trống | Empty state | DRAFT |
| `common.required` | Required | Bắt buộc | Cần điền | Form indicators | DRAFT |
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
   - Bản thảo hiển thị **"Chưa có thông tin"** cho payment status `UNKNOWN`. Xác nhận không suy đoán "Chưa thanh toán" khi chưa có chứng từ thu tiền.
