# Internal Pilot Testing Checklist

This checklist provides a reproducible, step-by-step test script for internal pilot participants (Director, Office/Secretary, Factory Staff, Finance).

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

### Step 1: Sign In & Authentication Check
1. Open the UniOps application URL (e.g. `http://localhost:5173` in development or internal server port).
2. Enter username and password on the login screen.
3. Click the password visibility toggle ("eye" button) to verify clear/masked password states.
4. Click **Sign in**.
   - *Expected*: Board or Overview loads; user avatar/badge appears in topbar settings menu.

### Step 2: Account Settings & Role Inspection
1. Click the **Settings** button in the topbar banner.
2. Inspect the displayed username and role tag (e.g., "Office", "Admin", or "Factory Read").
3. Verify password change dialog can be toggled.
4. Close settings by clicking outside or pressing Escape.

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

### Step 6: Order Cancellation Flow (`office` or `admin`)
1. Create a draft test order.
2. On the order card, click **Cancel order**.
3. Accept the confirmation prompt.
   - *Expected*: Order is moved to `CANCELLED` and safely removed from the active operational board.
   - *Backend verification*: API returns 422 if attempting to patch lines or link invoices to this cancelled order.

### Step 7: Inspect Operational Exceptions ("Needs Attention")
1. Click **Overview** in the primary navigation.
2. Locate the **Needs attention** section.
3. Verify any unlinked delivered orders or unlinked invoices appear with contextual reasons (e.g. "invoice dated ... is not linked to any UniOps order").

### Step 8: Accounting Link & Candidate Matching
1. Return to **Orders** or open an order card's **Accounting** button (status badge: *Invoice candidate* or *Not invoiced*).
2. Inspect the **Accounting details** drawer:
   - Review order number, lifecycle status, order total.
   - Inspect scored candidate invoices retrieved from normalized EasyBooks records.
   - Verify candidate evidence: customer code match, amount match, date difference.
3. If role is `office` or `admin`:
   - Click **Link this invoice** to confirm match.
   - Verify badge updates to **Invoiced**.
   - Test **Unlink** button to verify clean link removal and return to candidate state.

### Step 9: Commercial & Finance Dashboards
1. Click **Finance** in the navigation.
2. Observe the Summary KPI row: *Sales*, *Purchases*, *Receivables outstanding*, *Sales − purchases*.
   - *Notice*: Receivables outstanding displays `—` with explanatory note explaining that EasyBooks exposes no payment/settlement facts.
3. Click the **Sales** tab: inspect monthly totals, VAT breakdown, document counts.
4. Click the **Purchases** tab: inspect supplier counts and expense flows.
5. Click the **Receivables** tab: inspect customer list and invoice counts.
6. Test the **DateRangeFilter**:
   - Click the calendar button to open the dual-month picker.
   - Select quick presets: *This Month*, *Last Month*, *Last 3 Months*, *Last Year*, or *Clear*.
   - Confirm analytics update cleanly upon date changes.

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

## 3. Findings & Feedback Log Template

| Step # | User Role | Description of Issue or Observation | Severity (Blocker / Annoyance / Suggestion) |
|---|---|---|---|
| | | | |
