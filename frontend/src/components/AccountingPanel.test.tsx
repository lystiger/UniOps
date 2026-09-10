import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountingPanel } from "./AccountingPanel";
import type { Order } from "../types";

const order = {
  id: "order-1",
  order_number: "UO-20260301-ABC123",
  customer: { id: "c-1", name: "Fixture Customer", tax_code: null, easybooks_accounting_object_code: "KH-01" },
  status: "DELIVERED",
  order_date: "2026-03-01",
  required_date: "2026-03-01",
  notes: null,
  lines: [],
  accounting_status: "INVOICE_CANDIDATE",
} as unknown as Order;

const notInvoiced = {
  order_id: "order-1",
  order_number: "UO-20260301-ABC123",
  lifecycle_status: "DELIVERED",
  order_total: "10000.00",
  accounting_status: "NOT_INVOICED",
  payment_status: "UNKNOWN",
  outstanding_amount: null,
  outstanding_status: "EasyBooks exposes no paid or outstanding amount on any observed sales document",
  invoices: [],
  candidate_count: 1,
};

const candidate = {
  sales_document_id: "doc-1",
  source_id: "inv-1",
  invoice_number: "HD000123",
  document_date: "2026-03-01",
  total_amount: "10000.00",
  confidence: "1.0000",
  evidence: { amount_match: true },
};

function route(handlers: Record<string, () => Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    const match = Object.keys(handlers).find((path) => url.startsWith(path));
    return match ? handlers[match]() : new Response("{}", { status: 404 });
  });
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

afterEach(() => vi.restoreAllMocks());

describe("AccountingPanel", () => {
  it("says why outstanding is blank instead of showing a zero", async () => {
    route({
      "/api/orders/order-1/accounting": () => json(notInvoiced),
      "/api/orders/order-1/invoice-candidates": () => json([]),
    });

    render(<AccountingPanel order={order} canWrite onClose={() => undefined} onChanged={() => undefined} />);

    expect(await screen.findByText("Not invoiced")).toBeInTheDocument();
    expect(screen.getByText(/no paid or outstanding amount/)).toBeInTheDocument();
    expect(screen.getByText("No invoice linked to this order.")).toBeInTheDocument();
  });

  it("lets a writer confirm a candidate and says EasyBooks is untouched", async () => {
    const fetchMock = route({
      "/api/orders/order-1/accounting": () => json(notInvoiced),
      "/api/orders/order-1/invoice-candidates": () => json([candidate]),
      "/api/orders/order-1/invoice-links": () => json({ ...notInvoiced, accounting_status: "INVOICED" }, 201),
    });
    const onChanged = vi.fn();

    render(<AccountingPanel order={order} canWrite onClose={() => undefined} onChanged={onChanged} />);

    fireEvent.click(await screen.findByRole("button", { name: "Link" }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    const linkCall = fetchMock.mock.calls.find(([path]) => String(path).endsWith("/invoice-links"));
    expect(JSON.parse((linkCall![1] as RequestInit).body as string)).toEqual({
      sales_document_id: "doc-1",
    });
    expect(screen.getByText(/EasyBooks is never changed/)).toBeInTheDocument();
  });

  it("warns rather than guesses when several invoices fit", async () => {
    route({
      "/api/orders/order-1/accounting": () => json(notInvoiced),
      "/api/orders/order-1/invoice-candidates": () =>
        json([candidate, { ...candidate, sales_document_id: "doc-2", invoice_number: "HD000124" }]),
    });

    render(<AccountingPanel order={order} canWrite onClose={() => undefined} onChanged={() => undefined} />);

    expect(await screen.findByText(/UniOps will not guess/)).toBeInTheDocument();
  });

  it("offers a reader no way to change anything", async () => {
    route({
      "/api/orders/order-1/accounting": () => json(notInvoiced),
      "/api/orders/order-1/invoice-candidates": () => json([candidate]),
    });

    render(
      <AccountingPanel order={order} canWrite={false} onClose={() => undefined} onChanged={() => undefined} />,
    );

    expect(await screen.findByText("HD000123")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Link" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Unlink" })).not.toBeInTheDocument();
  });

  it("closes on Escape, like the settings menu and date picker", async () => {
    route({
      "/api/orders/order-1/accounting": () => json(notInvoiced),
      "/api/orders/order-1/invoice-candidates": () => json([]),
    });
    const onClose = vi.fn();

    render(<AccountingPanel order={order} canWrite onClose={onClose} onChanged={() => undefined} />);
    await screen.findByText("Not invoiced");

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes from the dimmed backdrop, but not from a press inside the panel", async () => {
    route({
      "/api/orders/order-1/accounting": () => json(notInvoiced),
      "/api/orders/order-1/invoice-candidates": () => json([]),
    });
    const onClose = vi.fn();

    render(<AccountingPanel order={order} canWrite onClose={onClose} onChanged={() => undefined} />);
    const inside = await screen.findByText("Not invoiced");
    const backdrop = screen.getByRole("dialog");
    expect(backdrop).toHaveAttribute("aria-modal", "true");

    fireEvent.mouseDown(inside);
    fireEvent.click(inside);
    // A text selection dragged out of the panel ends its click on the backdrop.
    fireEvent.mouseDown(inside);
    fireEvent.click(backdrop);
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.mouseDown(backdrop);
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
