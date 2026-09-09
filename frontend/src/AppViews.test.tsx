import { fireEvent, render, screen } from "@testing-library/react";
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
    return new Response("{}", { status: 404 });
  });
}

afterEach(() => vi.restoreAllMocks());

describe("Design System Views & Navigation", () => {
  it("renders topbar branding and navigates across all operational views", async () => {
    mockApi();
    render(<App />);

    // Brand and location
    expect(await screen.findByText("OPS")).toBeInTheDocument();
    expect(screen.getByText("Hưng Yên · LIVE")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Order board" })).toBeInTheDocument();

    // Switch to Overview
    fireEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(await screen.findByRole("heading", { name: "Production overview" })).toBeInTheDocument();
    expect(screen.getByText("01 / OPERATIONS · Executive snapshot")).toBeInTheDocument();
    expect(screen.getByText("FACILITY STATUS")).toBeInTheDocument();

    // Switch to Finance
    fireEvent.click(screen.getByRole("button", { name: "Finance" }));
    expect(await screen.findByRole("heading", { name: "Financial ledger & reconciliation" })).toBeInTheDocument();
    expect(screen.getByText("04 / FINANCE · EasyBooks ledger")).toBeInTheDocument();
    expect(screen.getByText(/EasyBooks remains the sole financial authority/)).toBeInTheDocument();

    // Switch to Data
    fireEvent.click(screen.getByRole("button", { name: "Data" }));
    expect(await screen.findByRole("heading", { name: "Data & synchronization pipelines" })).toBeInTheDocument();
    expect(screen.getByText("05 / DATA · Pipeline & synchronization")).toBeInTheDocument();
    expect(screen.getByText("Extract")).toBeInTheDocument();
    expect(screen.getByText("Transform")).toBeInTheDocument();
    expect(screen.getByText("Load")).toBeInTheDocument();

    // Switch to New order
    fireEvent.click(screen.getByRole("button", { name: "+ New order" }));
    expect(await screen.findByRole("heading", { name: "New order" })).toBeInTheDocument();
    expect(screen.getByText("02 / SALES · Secretary intake")).toBeInTheDocument();

    // Return to Order board
    fireEvent.click(screen.getByRole("button", { name: "Order board" }));
    expect(await screen.findByRole("heading", { name: "Order board" })).toBeInTheDocument();
  });

  it("renders DataView with pipeline stages and integration rules", () => {
    render(<DataView />);
    expect(screen.getByText("EasyBooks Enterprise Extraction Pipeline")).toBeInTheDocument();
    expect(screen.getByText("MSSQL Read replica")).toBeInTheDocument();
    expect(screen.getByText("Schema & decimal validation")).toBeInTheDocument();
    expect(screen.getByText("UniOps operational DB")).toBeInTheDocument();
  });

  it("renders FinanceView with accounting policy notice", () => {
    render(<FinanceView onNavigateOrders={() => undefined} />);
    expect(screen.getByText(/Accounting System of Record principle/)).toBeInTheDocument();
    expect(screen.getByText("Invoice Candidate Matching")).toBeInTheDocument();
  });

  it("renders OverviewView with live metrics", async () => {
    mockApi();
    render(
      <OverviewView
        onNavigateOrders={() => undefined}
        onNewOrder={() => undefined}
        canWrite={true}
        onSessionLost={() => undefined}
      />,
    );
    expect(screen.getByText("01 / OPERATIONS · Executive snapshot")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE ORDERS")).toBeInTheDocument();
    expect(screen.getByText("PRODUCING NOW")).toBeInTheDocument();
  });
});
