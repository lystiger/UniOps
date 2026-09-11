import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { DataView } from "./components/DataView";
import { FinanceView } from "./components/FinanceView";
import { OverviewView } from "./components/OverviewView";

const user = {
  id: "user-1",
  username: "office",
  full_name: "Front Desk Admin",
  role: "OFFICE" as const,
  is_active: true,
  last_login_at: null,
};

const orders = [
  {
    id: "ord-1",
    order_number: "SO-20260909-001",
    customer: { id: "cust-1", name: "UniPackaging Corp" },
    status: "IN_PRODUCTION",
    order_date: "2026-09-09",
    required_date: "2026-09-15",
    accounting_status: "INVOICE_CANDIDATE",
    lines: [{ id: "l-1", description: "Jumbo Parent Roll 17gsm", quantity: "12", unit: "roll" }],
  },
  {
    id: "ord-2",
    order_number: "SO-20260909-002",
    customer: { id: "cust-2", name: "Green Napkin LLC" },
    status: "READY",
    order_date: "2026-09-01",
    required_date: "2026-09-05", // overdue
    accounting_status: "INVOICED",
    lines: [{ id: "l-2", description: "Table Napkin 33x33", quantity: "200", unit: "carton" }],
  },
];

const exceptionReport = { as_of: "2026-09-10", total: 0, groups: [] };
const commercialOverview = {
  from_date: null,
  to_date: null,
  sales: { document_count: 3, customer_count: 2, total: "1000000", vat_amount: "80000", undated_document_count: 0, by_month: [] },
  purchases: { document_count: 1, supplier_count: 1, total: "400000", vat_amount: "32000", undated_document_count: 0, by_month: [] },
  sales_minus_purchases: "600000",
};
const receivablesSummary = {
  as_of: "2026-09-10",
  from_date: null,
  to_date: null,
  total_invoiced: "1000000",
  invoice_count: 3,
  linked_invoice_count: 1,
  unlinked_invoice_count: 2,
  total_outstanding: null,
  total_overdue: null,
  unpaid_invoice_count: null,
  overdue_invoice_count: null,
  outstanding_status: "NO_PAYMENT_SOURCE",
  due_status: "EasyBooks exposes no due date on any observed sales document",
  customers: [],
};

function mockApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/api/auth/me")) {
      return new Response(JSON.stringify(user), { status: 200 });
    }
    if (url.includes("/api/orders")) {
      return new Response(JSON.stringify({ items: orders, total: orders.length }), { status: 200 });
    }
    if (url.includes("/api/customers")) {
      return new Response(JSON.stringify([{ id: "cust-1", name: "UniPackaging Corp" }]), { status: 200 });
    }
    if (url.includes("/api/products")) {
      return new Response(JSON.stringify([{ id: "prod-1", code: "P-01", name: "Parent Roll", unit: "kg" }]), { status: 200 });
    }
    if (url.includes("/api/operations/exceptions")) {
      return new Response(JSON.stringify(exceptionReport), { status: 200 });
    }
    if (url.includes("/api/analytics/overview")) {
      return new Response(JSON.stringify(commercialOverview), { status: 200 });
    }
    if (url.includes("/api/analytics/sales")) {
      return new Response(JSON.stringify(commercialOverview.sales), { status: 200 });
    }
    if (url.includes("/api/analytics/purchases")) {
      return new Response(JSON.stringify(commercialOverview.purchases), { status: 200 });
    }
    if (url.includes("/api/analytics/receivables")) {
      return new Response(JSON.stringify(receivablesSummary), { status: 200 });
    }
    if (url.includes("/api/sync-runs")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response("{}", { status: 404 });
  });
}

afterEach(() => vi.restoreAllMocks());

describe("Navigation and page identity", () => {
  it("renders topbar branding and navigates across all operational views", async () => {
    mockApi();
    render(<App />);

    // Wait for the board heading first: the loading screen carries the same
    // "OPS" wordmark, so querying for it alone can catch that transient node
    // instead of the topbar's.
    expect(await screen.findByRole("heading", { name: "Order board" })).toBeInTheDocument();
    expect(screen.getByText("OPS")).toBeInTheDocument();
    // The redesigned nav has no facility badge or fabricated live status.
    expect(screen.queryByText(/Hưng Yên/)).not.toBeInTheDocument();
    expect(screen.queryByText("LIVE")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Finance" }));
    expect(await screen.findByRole("heading", { name: "Finance" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Data" }));
    expect(await screen.findByRole("heading", { name: "Data" })).toBeInTheDocument();
    expect(await screen.findByText("EasyBooks synchronization")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "+ New order" }));
    expect(await screen.findByRole("heading", { name: "New order" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Orders" }));
    expect(await screen.findByRole("heading", { name: "Order board" })).toBeInTheDocument();
  });
});

describe("OverviewView", () => {
  it("shows real order counts and the commercial snapshot from analytics", async () => {
    mockApi();
    render(
      <OverviewView
        onNavigateOrders={() => undefined}
        onNewOrder={() => undefined}
        canWrite={true}
        onSessionLost={() => undefined}
      />,
    );

    expect(await screen.findByText("Active orders")).toBeInTheDocument();
    expect(screen.getAllByText("2").length).toBeGreaterThan(0); // 2 active orders
    expect(await screen.findByText("Nothing needs attention.")).toBeInTheDocument();
    expect(await screen.findByText(/1.000.000/)).toBeInTheDocument(); // sales total, vi-VN grouped
  });

  it("shows an API error distinctly, not a blank or a zero", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/orders")) return new Response("{}", { status: 500 });
      return new Response("{}", { status: 404 });
    });
    render(
      <OverviewView
        onNavigateOrders={() => undefined}
        onNewOrder={() => undefined}
        canWrite={true}
        onSessionLost={() => undefined}
      />,
    );
    expect((await screen.findAllByText("Could not load orders.")).length).toBeGreaterThan(0);
  });

  it("returns to sign-in on a 401 from an analytics call", async () => {
    const onSessionLost = vi.fn();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/analytics/overview")) {
        return new Response(JSON.stringify({ detail: "sign in to use UniOps" }), { status: 401 });
      }
      if (url.includes("/api/orders")) return new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 });
      if (url.includes("/api/operations/exceptions")) return new Response(JSON.stringify(exceptionReport), { status: 200 });
      if (url.includes("/api/analytics/receivables")) return new Response(JSON.stringify(receivablesSummary), { status: 200 });
      if (url.includes("/api/sync-runs")) return new Response(JSON.stringify([]), { status: 200 });
      return new Response("{}", { status: 404 });
    });
    render(
      <OverviewView
        onNavigateOrders={() => undefined}
        onNewOrder={() => undefined}
        canWrite={true}
        onSessionLost={onSessionLost}
      />,
    );
    await waitFor(() => expect(onSessionLost).toHaveBeenCalled());
  });
});

describe("FinanceView", () => {
  it("renders sales data on the default tab", async () => {
    mockApi();
    render(<FinanceView onSessionLost={() => undefined} />);
    expect(await screen.findByRole("tab", { name: "Sales" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findAllByText("Documents")).not.toHaveLength(0);
    expect(screen.getAllByText(/1.000.000/).length).toBeGreaterThan(0);
  });

  it("renders purchase data on the purchases tab", async () => {
    mockApi();
    render(<FinanceView onSessionLost={() => undefined} />);
    fireEvent.click(await screen.findByRole("tab", { name: "Purchases" }));
    expect(await screen.findByText("Suppliers")).toBeInTheDocument();
    expect(screen.getAllByText(/400.000/).length).toBeGreaterThan(0);
  });

  it("never shows a null receivable outstanding balance as zero", async () => {
    mockApi();
    render(<FinanceView onSessionLost={() => undefined} />);
    fireEvent.click(await screen.findByRole("tab", { name: "Receivables" }));
    expect(await screen.findByText(/Outstanding balance:/)).toHaveTextContent(
      "EasyBooks exposes no paid or outstanding amount on any observed sales document",
    );
    expect(screen.queryByText("0 ₫")).not.toBeInTheDocument();
  });

  it("only exposes receivable rows with a customer link as interactive", async () => {
    const summaryWithCustomers = {
      ...receivablesSummary,
      customers: [
        {
          customer_id: "cust-1",
          customer_code: "C-001",
          customer_name: "Linked Customer",
          invoice_count: 1,
          total_invoiced: "600000",
          oldest_invoice_date: "2026-09-01",
          newest_invoice_date: "2026-09-01",
          outstanding_amount: null,
          overdue_amount: null,
        },
        {
          customer_id: null,
          customer_code: "UNLINKED",
          customer_name: "Unlinked Customer",
          invoice_count: 1,
          total_invoiced: "400000",
          oldest_invoice_date: "2026-09-02",
          newest_invoice_date: "2026-09-02",
          outstanding_amount: null,
          overdue_amount: null,
        },
      ],
    };
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/analytics/receivables")) {
        return new Response(JSON.stringify(summaryWithCustomers), { status: 200 });
      }
      if (url.includes("/api/analytics/overview")) {
        return new Response(JSON.stringify(commercialOverview), { status: 200 });
      }
      if (url.includes("/api/analytics/sales")) {
        return new Response(JSON.stringify(commercialOverview.sales), { status: 200 });
      }
      if (url.includes("/api/analytics/purchases")) {
        return new Response(JSON.stringify(commercialOverview.purchases), { status: 200 });
      }
      if (url.includes("/api/sync-runs")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });

    render(<FinanceView onSessionLost={() => undefined} />);
    fireEvent.click(await screen.findByRole("tab", { name: "Receivables" }));

    const linkedRow = (await screen.findByText("Linked Customer")).closest("tr");
    const unlinkedRow = screen.getByText("Unlinked Customer").closest("tr");
    expect(linkedRow).toHaveAttribute("role", "button");
    expect(linkedRow).toHaveAttribute("tabindex", "0");
    expect(unlinkedRow).not.toHaveAttribute("role");
    expect(unlinkedRow).not.toHaveAttribute("tabindex");
    expect(unlinkedRow).not.toHaveClass("clickable");
  });

  it("refetches analytics when the date filter changes", async () => {
    const fetchMock = mockApi();
    render(<FinanceView onSessionLost={() => undefined} />);
    await screen.findAllByText("Documents");
    fetchMock.mockClear();

    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-01-01" } });

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("from_date=2026-01-01"),
        expect.anything(),
      ),
    );
  });

  it("shows a source-limitation error distinctly from an empty result", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/analytics/sales")) return new Response("{}", { status: 500 });
      if (url.includes("/api/analytics/overview")) return new Response(JSON.stringify(commercialOverview), { status: 200 });
      if (url.includes("/api/analytics/receivables")) return new Response(JSON.stringify(receivablesSummary), { status: 200 });
      if (url.includes("/api/sync-runs")) return new Response(JSON.stringify([]), { status: 200 });
      return new Response("{}", { status: 404 });
    });
    render(<FinanceView onSessionLost={() => undefined} />);
    expect(await screen.findByText("Could not load EasyBooks sales data.")).toBeInTheDocument();
  });
});

describe("DataView", () => {
  it("renders real sync runs, not fabricated pipeline stages", async () => {
    const runs = [
      {
        id: "run-1",
        mode: "incremental",
        from_date: null,
        to_date: null,
        started_at: "2026-09-09T15:44:00Z",
        finished_at: "2026-09-09T15:44:12Z",
        status: "SUCCEEDED",
        documents_seen: 42,
        documents_created: 2,
        documents_updated: 1,
        documents_unchanged: 39,
        documents_failed: 0,
        reconciliation_warnings: 0,
        error_summary: null,
      },
    ];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/sync-runs")) return new Response(JSON.stringify(runs), { status: 200 });
      return new Response("{}", { status: 404 });
    });
    render(<DataView onSessionLost={() => undefined} />);

    expect(await screen.findByText("Last successful sync")).toBeInTheDocument();
    expect(screen.getAllByText("Success").length).toBeGreaterThan(0);
    expect(screen.getAllByText("42").length).toBeGreaterThan(0);
    expect(screen.queryByText("Extract")).not.toBeInTheDocument();
    expect(screen.queryByText("Transform")).not.toBeInTheDocument();
  });

  it("shows an empty state when no sync has ever run, not a zeroed table", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify([]), { status: 200 }));
    render(<DataView onSessionLost={() => undefined} />);
    expect(await screen.findByText("No EasyBooks synchronization has run yet.")).toBeInTheDocument();
  });
});

describe("OverviewView Needs attention", () => {
  it("separates order and invoice issues, shows Reference and customer, formats dates as vi-VN, and shows pagination note", async () => {
    const mockExceptions = {
      as_of: "2026-09-10",
      total: 12,
      groups: [
        {
          category: "DELIVERED_ORDER_NOT_INVOICED",
          count: 1,
          items: [
            {
              category: "DELIVERED_ORDER_NOT_INVOICED",
              reference: "SO-20260909-001",
              detail: "DELIVERED order has no linked invoice",
              customer_name: "UniPackaging Corp",
              document_date: "2026-09-15",
              total_amount: "5000000.00",
              order_id: "ord-1",
              sales_document_id: null,
            },
          ],
        },
        {
          category: "INVOICE_WITHOUT_ORDER",
          count: 11,
          items: [
            {
              category: "INVOICE_WITHOUT_ORDER",
              reference: "1C26TSH/105",
              detail: "Invoice not linked to any UniOps order",
              customer_name: "CÔNG TY TNHH ABC",
              document_date: "2026-06-30",
              total_amount: "7210620.00",
              order_id: null,
              sales_document_id: "doc-105",
            },
          ],
        },
      ],
    };

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/orders")) {
        return new Response(JSON.stringify({ items: orders, total: orders.length }), { status: 200 });
      }
      if (url.includes("/api/operations/exceptions")) {
        return new Response(JSON.stringify(mockExceptions), { status: 200 });
      }
      if (url.includes("/api/analytics/overview")) {
        return new Response(JSON.stringify(commercialOverview), { status: 200 });
      }
      if (url.includes("/api/analytics/receivables")) {
        return new Response(JSON.stringify(receivablesSummary), { status: 200 });
      }
      if (url.includes("/api/sync-runs")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });

    render(
      <OverviewView
        onNavigateOrders={() => undefined}
        onNewOrder={() => undefined}
        canWrite={true}
        onSessionLost={() => undefined}
      />,
    );

    // Section count says what it counts with correct grammar
    expect(await screen.findByText("1 order issue · 11 invoice issues")).toBeInTheDocument();

    // Visibly separate headings
    expect(screen.getByText("Order exceptions (1)")).toBeInTheDocument();
    expect(screen.getByText("Invoice backlog & data issues (11)")).toBeInTheDocument();

    // Invoice renders as invoice reference, not as an order
    expect(screen.getByText("1C26TSH/105")).toBeInTheDocument();
    // Customer column is filled
    expect(screen.getByText("CÔNG TY TNHH ABC")).toBeInTheDocument();

    // Date formatted as DD/MM/YYYY (30/06/2026) and NO raw ISO date (2026-06-30) in table
    expect(screen.getByText("30/06/2026")).toBeInTheDocument();
    expect(screen.queryByText("2026-06-30")).not.toBeInTheDocument();

    // Truncation note "Showing 1 of 11" appears
    expect(screen.getByText("Showing 1 of 11")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View all (11)" })).toBeInTheDocument();
  });

  it("shows '0 order issues · 11 invoice issues' and renders 'Order exceptions (0)' with empty state when no order exceptions exist", async () => {
    const mockExceptions = {
      as_of: "2026-09-10",
      total: 11,
      groups: [
        {
          category: "INVOICE_WITHOUT_ORDER",
          count: 11,
          items: [
            {
              category: "INVOICE_WITHOUT_ORDER",
              reference: "1C26TSH/105",
              detail: "Invoice not linked to any UniOps order",
              customer_name: "CÔNG TY TNHH ABC",
              document_date: "2026-06-30",
              total_amount: "7210620.00",
              order_id: null,
              sales_document_id: "doc-105",
            },
          ],
        },
      ],
    };

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/orders")) {
        return new Response(JSON.stringify({ items: orders, total: orders.length }), { status: 200 });
      }
      if (url.includes("/api/operations/exceptions")) {
        return new Response(JSON.stringify(mockExceptions), { status: 200 });
      }
      if (url.includes("/api/analytics/overview")) {
        return new Response(JSON.stringify(commercialOverview), { status: 200 });
      }
      if (url.includes("/api/analytics/receivables")) {
        return new Response(JSON.stringify(receivablesSummary), { status: 200 });
      }
      if (url.includes("/api/sync-runs")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });

    render(
      <OverviewView
        onNavigateOrders={() => undefined}
        onNewOrder={() => undefined}
        canWrite={true}
        onSessionLost={() => undefined}
      />,
    );

    expect(await screen.findByText("0 order issues · 11 invoice issues")).toBeInTheDocument();
    expect(screen.getByText("Order exceptions (0)")).toBeInTheDocument();
    expect(screen.getByText("No order exceptions")).toBeInTheDocument();
    expect(screen.getByText("Invoice backlog & data issues (11)")).toBeInTheDocument();
  });
});
