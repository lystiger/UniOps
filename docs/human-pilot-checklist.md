# Internal Pilot Testing Checklist

This checklist provides a reproducible, step-by-step test script for internal pilot participants (Director, Office/Secretary, Factory Staff, Finance).

> [!IMPORTANT]
> **Pilot Language**: The internal UI/UX pilot is conducted primarily in **Vietnamese (`vi`)**, the default system language. English (`en`) is available for dual-language evaluation. Participants are encouraged to evaluate terminology clarity against [docs/glossary-vi.md](glossary-vi.md).

> [!IMPORTANT]
> **Round 2 (final V1 validation)**: Section 3 below is the script for the final round. It is a **task list, not a demo**. The facilitator sets the task, then stops talking. Do not explain a screen, do not point, do not confirm or correct an answer while the participant is working, and do not rephrase a label the participant is struggling with — the struggle is the result being measured. Record what the participant says in their own words.
>
> Round 1 (3 respondents: 1 management, 1 office, 1 finance, **0 factory**) could not validate factory usability at all. Round 2 is not complete without at least one factory/production participant running Section 3.

---

## 1. Participant Roles & Credentials

Before testing, verify the tester account has the appropriate role created via CLI:

```bash
# Example account setup:
uv run uniops user create --username director --role admin --full-name "Managing Director"
uv run uniops user create --username secretary --role office --full-name "Office Desk"
uv run uniops user create --username factory_lead --role factory-read --full-name "Floor Lead"
```

| Role | Intended Tester | Expected Permissions |
|---|---|---|
| `admin` | Director / Management | Full read and write; user administration |
| `office` | Front Desk / Secretary | Create and advance orders; link/unlink invoices; catalog edits |
| `factory-read` | Production / Floor Staff | Read-only board view; no mutation buttons |

---

## 2. Step-by-Step Pilot Test Script

### Step 0: First Open (do this on a browser profile that has never opened UniOps)
1. After signing in for the first time, a single dismissible line appears under the top bar:
   *"UniOps tập trung thông tin đơn hàng, dữ liệu EasyBooks và trạng thái đồng bộ tại một nơi. Một số thông tin tài chính vẫn cần kiểm tra trực tiếp trong EasyBooks."*
2. Read it, then click **Đã hiểu**.
   - *Expected*: it disappears and does not come back on later visits in that browser.
   - There is no tour, no carousel, and no step-by-step overlay. If a participant expects one, record that as a finding rather than providing one.

### Step 1: Sign In, Language Switcher & Authentication Check
1. Open the UniOps application URL (e.g. `http://localhost:5173` in development or internal server port).
2. **Language Switcher on Sign-in Screen**:
   - Observe that the interface defaults to Vietnamese ("Đăng nhập", "Tên đăng nhập", "Mật khẩu").
   - Click the **English** button in the top-right corner of the login card: verify that all labels instantly change to English ("Sign in", "Username", "Password") without reloading.
   - Click **Tiếng Việt** to return to Vietnamese for the pilot test.
3. Enter username and password on the login screen.
4. Click the password visibility toggle ("eye" button) to verify clear/masked password states.
5. Click **Đăng nhập** (Sign in).
   - *Expected*: Board or Overview loads in Vietnamese; user avatar/badge appears in topbar settings menu.

### Step 2: Account Settings, Role Inspection & Language Switch
1. Click the **Cài đặt** (Settings) button in the topbar banner.
2. Inspect the displayed username and role badge (e.g., "Trạng thái: Khối văn phòng", "Quản trị viên", or "Khối xưởng · Chỉ xem").
3. **Language Switcher in Settings**:
   - Under "Ngôn ngữ", click **English**. Verify that all navigation items and screen content immediately switch to English without page reload.
   - Click **Tiếng Việt** to switch back to Vietnamese.
4. Verify password change dialog ("Đổi mật khẩu") can be toggled.
5. Close settings by clicking outside or pressing Escape.

### Step 3: Order Desk & Navigation
1. Click **Orders** in the primary navigation.
2. Verify the 5 lifecycle columns render:
   - *Waiting / confirmed*
   - *Scheduled*
   - *Producing*
   - *Ready*
   - *Delivery / delivered*
3. Use the search bar to filter by customer name or order number.
4. Clear the search input and verify all active orders return.

### Step 4: Create a New Order (`office` or `admin`)
1. Click **+ New order** in the header or board actions.
2. Select a customer from the dropdown, or add a customer if needed.
3. Confirm **Order date** and **Required date** (cannot be before order date).
4. Add product lines: select product, enter quantity (e.g. `500`), unit (e.g. `kg`), and agreed unit price (e.g. `25000`).
   - Verify the required fields carry a `*` and the legend *"Các trường có dấu * là bắt buộc."* is visible, and that **Đơn giá thỏa thuận** is marked *(không bắt buộc)* beside its label rather than only inside the box.
   - Verify the helper lines under **Mô tả sản phẩm**, **Số lượng** and **Đơn giá thỏa thuận** are present and readable.
   - Enter `0` as a quantity and try to save: the error must name the field (*"Số lượng phải là một số lớn hơn 0."*), not a generic rejection.
5. Enter production notes (e.g. "Core 76mm, pallet wrap").
6. Click **Save order**.
   - *Expected*: Toast/notification confirms creation; order appears in *Waiting / confirmed* column with status **Waiting**.

### Step 5: Progress Order Lifecycle
1. Locate the newly created order in *Waiting / confirmed*.
2. Click **Confirm** → status becomes **Confirmed**.
3. Click **Schedule** → order moves to *Scheduled* column.
4. Click **Start production** → order moves to *Producing* column.
5. Click **Mark ready** → order moves to *Ready* column.
6. Click **Send to delivery** → order moves to *Delivery / delivered* column.
7. Click **Mark delivered** → order status becomes **Delivered**.
8. Optional operational stages:
   - Click **Mark invoiced** → order status becomes **Invoiced** (note: an operator can advance an order to `INVOICED` without a linked EasyBooks invoice; whether that is intended is open, see Topic 7 in [docs/finance-validation-questions.md](finance-validation-questions.md)).
   - Click **Close order** → order status becomes **Closed** (archived from board).

### Step 6: Order Cancellation Flow (`office` or `admin`)
1. Create a draft test order.
2. On the order card, click **Cancel order**.
3. Accept the confirmation prompt:
   - *Expected*: Order is moved to `CANCELLED` and safely removed from the active operational board.
   - *Backend verification*:
     - Attempting to update or edit lines on a cancelled order returns HTTP 422 Unprocessable Content.
     - Attempting to link an invoice to a cancelled order returns HTTP 409 Conflict.
     - Attempting to cancel an order that already has an invoice link returns HTTP 409 Conflict ("cannot cancel an order with linked invoices; unlink all invoices first"), surfaced in the board error banner.

### Step 7: Inspect Operational Exceptions ("Needs Attention")
1. Click **Overview** in the primary navigation.
2. Locate the **Needs attention** section.
3. Observe the breakdown between **Order exceptions** (delivered orders missing invoices, candidate ambiguities, customer/amount mismatches) and **Invoice backlog & data issues** (EasyBooks invoices not linked to UniOps orders, invoices missing customer code).
4. Verify the **Reference** column displays specific references (e.g. `1C26TSH/105` or `UO-20260910-XXXX`, with no English "Invoice" prefix in either language), and the **Customer** column shows the customer name.
5. Invoices show vi-VN formatted date (`DD/MM/YYYY`) and VND amount; order rows show status and required date.
6. Verify pagination indicator (e.g., "Showing 10 of 111") and test the **View all** / **Show 10** toggle.
7. Note for Administrator / Owner: Historical unlinked invoices preceding UniOps adoption can be filtered by setting `UNIOPS_ORDER_TRACKING_SINCE=YYYY-MM-DD` in `.env`.

### Step 8: Accounting Link & Candidate Matching
1. Return to **Orders** or open an order card's **Accounting** button (status badge: *Invoice candidate* or *Not invoiced*).
2. Inspect the **Accounting details** drawer:
   - Review order number, lifecycle status, order total.
   - **Payment** reads *"Chưa có dữ liệu xác nhận thanh toán"* with the note beginning *"UniOps chưa có đủ dữ liệu để kết luận…"*. It must never read *"Chưa thanh toán"*, *"Đã thanh toán"*, *"Thanh toán một phần"* or *"Quá hạn"*. This is Task C in Section 3.
   - Inspect scored candidate invoices retrieved from normalized EasyBooks records.
   - Verify candidate evidence: customer code match, amount match, date difference.
3. If role is `office` or `admin`:
   - Click **Link this invoice** to confirm match.
   - Verify badge updates to **Invoiced**.
   - Test **Unlink** button to verify clean link removal and return to candidate state.

### Step 9: Commercial & Finance Dashboards
1. Click **Finance** in the navigation.
2. Observe the Summary KPI row: *Sales*, *Purchases*, *Receivables outstanding*, *Sales − purchases*.
   - *Notice*: Receivables outstanding displays **"Chưa có dữ liệu xác nhận"** ("No confirmation data") with an explanatory note that EasyBooks exposes no payment/settlement facts. It is deliberately **not** a `0 ₫`, not a bare `—`, and not the **"Không tải được"** ("Could not load") a failed request would show. Verify a reader can tell those apart.
3. Click the **Sales** tab: inspect monthly totals, VAT breakdown, document counts.
4. Click the **Purchases** tab: inspect supplier counts and expense flows.
5. Click the **Receivables** tab: inspect customer list and invoice counts.
6. Test the **DateRangeFilter**:
   - Click the calendar button to open the dual-month picker.
   - Select quick presets: *This Month*, *Last Month*, *Last 3 Months*, *Last Year*, or *Clear*.
   - Confirm analytics update cleanly upon date changes.
   - *Note on Date Display*: Native browser `<input type="date">` controls render according to browser locale (e.g., `mm/dd/yyyy` under `en-US`), while the unambiguous Vietnamese `DD/MM/YYYY` representation is displayed alongside inside the Calendar trigger button (`(DD/MM/YYYY – DD/MM/YYYY)`).

### Step 10: EasyBooks Ingestion & Sync Observability
1. Click **Data** in the navigation.
2. Verify **Last successful sync** and **Last attempt** timestamps.
3. Review the **Recent synchronization runs** table:
   - Inspect columns: *Time*, *Mode*, *Status*, *Rows*, *Warnings*, *Duration / details*.
   - Verify that any partial sync or failure displays an explicit error message instead of a generic failure.

### Step 11: Sign Out
1. Click **Settings** in the topbar banner.
2. Click **Sign out**.
   - *Expected*: Session cookie is cleared, and application redirects to the Sign-in screen.

---

## 3. Final V1 Validation Round — Task Script

Six tasks. Each is given to the participant as the sentence in **bold** and nothing more.

| Task | Applies to | What the facilitator says (and nothing else) |
|---|---|---|
| A | All roles | **"Tìm một đơn hàng và cho biết việc gì cần làm tiếp theo với đơn đó."** *(Find an order and say what should happen next with it.)* |
| B | `office`, `admin` | **"Hãy tạo một đơn hàng mới."** *(Create a new order.)* No guidance of any kind, including on which fields are required. |
| C | All roles | **"Mở phần kế toán của một đơn hàng. Hãy đọc dòng Thanh toán và giải thích bằng lời của mình xem nó có nghĩa là gì."** *(Open an order's accounting panel. Read the Payment line and explain in your own words what it means.)* |
| D | All roles | **"Tìm lần đồng bộ EasyBooks gần nhất và cho biết nó có thành công hay không."** *(Find the most recent EasyBooks sync and say whether it succeeded.)* |
| E | All roles | **"Tìm doanh số của một khoảng thời gian mà bạn chọn."** *(Find sales for a period of your choosing.)* |
| F | **`factory-read` only** | **"Tìm một đơn hàng đang sản xuất và cho biết việc gì cần làm tiếp theo."** *(Find an order currently in production and say what should happen next.)* |

### Scoring

Record for each task: **completed unaided / completed after hesitation / not completed**, plus the participant's exact words. Do not score anything the facilitator prompted.

#### Task C is the one that failed in Round 1 — score it exactly

The payment line now reads **"Chưa có dữ liệu xác nhận thanh toán"**, with the note *"UniOps chưa có đủ dữ liệu để kết luận đã trả, chưa trả, trả một phần hoặc quá hạn. Hãy kiểm tra EasyBooks."*

| Participant's answer | Verdict |
|---|---|
| Any paraphrase of *"UniOps chưa biết đã thanh toán hay chưa"* — **UniOps does not know whether payment happened yet** | **CORRECT** |
| *"Khách chưa thanh toán"* / *"chưa trả tiền"* — the customer has not paid | **FAILED.** This is the Round 1 failure repeating. Record it verbatim and stop treating the wording as fixed. |
| *"Đã thanh toán rồi"*, *"quá hạn"*, *"trả một phần"* | **FAILED.** UniOps must not have suggested any settlement state. |
| *"Không biết"* / no answer | **FAILED**, but distinct from the above: this is a legibility problem, not a false conclusion. |

Task C must also be run once with the interface switched to English, where the line reads **"No payment confirmation data"**.

### Task F — factory participant preparation

Round 1 had no factory respondent. Before the round, create and verify the account:

```bash
uv run uniops user create --username factory_lead --role factory-read --full-name "Floor Lead"
```

Then confirm, **before** the participant sits down, that a `factory-read` sign-in:

1. Signs in and lands on the order board.
2. Can search and find orders, including one in *Đang sản xuất* (`IN_PRODUCTION`).
3. Reads each order's status badge and its **"Bước tiếp theo: …"** line — the read-only role is told the next lifecycle step as text, since it has no button to perform it.
4. Sees **no** control it cannot use: no *+ Tạo đơn hàng*, no status-advance button, no *Hủy đơn hàng*, no invoice *Liên kết* / *Hủy liên kết* inside the accounting panel.
5. Can still open the accounting panel read-only, and sees the payment wording from Task C there.

If any of the above fails, fix it before the round rather than coaching the participant past it.

---

## 4. Findings & Feedback Log Template

Record any issues, observations, or feedback on Vietnamese terminology encountered during pilot testing:

| Step # | User Role | Description of Issue or Observation | Unclear Wording / Term (Glossary Key) | Suggested Term / Alternative | Severity (Blocker / Annoyance / Suggestion) |
|---|---|---|---|---|---|
| | | | | | |

> *Note*: Refer to [docs/glossary-vi.md](glossary-vi.md) for current draft translations, accounting-sensitive flags, and alternatives under review.
