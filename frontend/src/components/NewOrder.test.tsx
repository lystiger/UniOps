import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NewOrder } from "./NewOrder";

// Labels now carry a "*" or a "(optional)" marker. Both are aria-hidden, so a
// browser's accessible name is still the bare field name, but Testing Library
// matches on the label's text content — hence the anchored patterns below.

afterEach(() => vi.restoreAllMocks());

describe("NewOrder", () => {
  it("loads catalog data and submits decimal values as strings", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "customer-1", name: "Fixture Customer", tax_code: null, easybooks_accounting_object_code: null }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "product-1", code: "P-01", name: "Paper roll", unit: "roll", easybooks_material_goods_id: null }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "order-1" }), { status: 201 }));
    const onCreated = vi.fn();
    render(<NewOrder onCreated={onCreated} />);

    await screen.findByRole("option", { name: "Fixture Customer" });
    fireEvent.change(screen.getByLabelText(/^Customer/), { target: { value: "customer-1" } });
    fireEvent.change(screen.getByLabelText(/^Product /), { target: { value: "product-1" } });
    fireEvent.change(screen.getByLabelText(/^Quantity/), { target: { value: "12.5000" } });
    fireEvent.change(screen.getByLabelText(/^Agreed price/), { target: { value: "20000.00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save order" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
    const submitted = JSON.parse((fetchMock.mock.calls[2][1] as RequestInit).body as string);
    expect(submitted.lines[0].quantity).toBe("12.5000");
    expect(submitted.lines[0].agreed_unit_price).toBe("20000.00");
  });

  it("marks required and optional fields and explains the ones the pilot stumbled on", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));
    render(<NewOrder onCreated={() => undefined} />);

    // One of two pilot participants found 1-2 fields unclear. Which fields were
    // mandatory was not stated anywhere, and the price field used its
    // placeholder as the only hint that it was optional.
    expect(await screen.findByText("Fields marked * are required.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Customer\*/)).toBeRequired();
    expect(screen.getByLabelText(/^Quantity\*/)).toBeRequired();
    expect(screen.getByLabelText(/^Agreed price \(optional\)/)).not.toBeRequired();

    expect(screen.getByText("Counted in the unit named beside it.")).toBeInTheDocument();
    expect(screen.getByText("Price for one unit, in Vietnamese dong (₫).")).toBeInTheDocument();
    expect(screen.getByText("Filled in from the product you choose; you can edit it.")).toBeInTheDocument();

    // The placeholder no longer stands in for a label.
    expect(screen.getByLabelText(/^Agreed price/)).toHaveAttribute("placeholder", "0");
  });

  it("names the field a bad quantity is in, rather than passing on a generic API rejection", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([{ id: "customer-1", name: "Fixture Customer", tax_code: null, easybooks_accounting_object_code: null }]),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));
    render(<NewOrder onCreated={() => undefined} />);

    await screen.findByRole("option", { name: "Fixture Customer" });
    fireEvent.change(screen.getByLabelText(/^Customer/), { target: { value: "customer-1" } });
    fireEvent.change(screen.getByLabelText(/^Description/), { target: { value: "Paper roll" } });
    fireEvent.change(screen.getByLabelText(/^Quantity/), { target: { value: "0" } });
    fireEvent.click(screen.getByRole("button", { name: "Save order" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Quantity must be a number greater than 0.",
    );
    // Nothing was sent: the API would have answered a generic "request invalid".
    expect(fetchMock.mock.calls.some(([path]) => String(path).endsWith("/api/orders"))).toBe(false);
  });

  it("reports catalog conflicts instead of failing silently", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "product code or EasyBooks material ID already exists" }), { status: 409 }),
      );
    render(<NewOrder onCreated={() => undefined} />);

    const panel = await screen.findByRole("complementary");
    const productForm = within(panel).getByRole("button", { name: "Add product" }).closest("form")!;
    fireEvent.change(within(productForm).getByLabelText(/^Name/), { target: { value: "Paper roll" } });
    fireEvent.submit(productForm);

    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
    const submitted = JSON.parse((fetchMock.mock.calls[2][1] as RequestInit).body as string);
    expect(submitted.code).toBeNull();
  });
});
