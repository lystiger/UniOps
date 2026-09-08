import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OrderBoard } from "./OrderBoard";

const order = {
  id: "order-1",
  order_number: "UO-20260908-ABC123",
  customer: {
    id: "customer-1",
    name: "Fixture Customer",
    tax_code: null,
    easybooks_accounting_object_code: null,
  },
  status: "DRAFT",
  order_date: "2020-01-01",
  required_date: "2020-01-03",
  notes: null,
  lines: [
    {
      id: "line-1",
      product_id: null,
      product: null,
      position: 1,
      description: "Paper roll",
      quantity: "20.0000",
      unit: "roll",
      agreed_unit_price: null,
      notes: null,
    },
  ],
};

afterEach(() => vi.restoreAllMocks());

describe("OrderBoard", () => {
  it("maps waiting orders, marks overdue, and advances explicitly", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [order], total: 1 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...order, status: "CONFIRMED" }), { status: 200 }));

    render(<OrderBoard refreshKey={0} onNewOrder={() => undefined} />);

    expect(await screen.findByText("Fixture Customer")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => expect(screen.getByText("Confirmed")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/orders/order-1/status",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("offers a direct new-order action when the board is empty", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }),
    );
    const onNewOrder = vi.fn();
    render(<OrderBoard refreshKey={0} onNewOrder={onNewOrder} />);
    await screen.findAllByText("No orders here");
    fireEvent.click(screen.getByRole("button", { name: "+ New order" }));
    expect(onNewOrder).toHaveBeenCalledOnce();
  });
});

