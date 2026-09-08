import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NewOrder } from "./NewOrder";

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
    fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "customer-1" } });
    fireEvent.change(screen.getByLabelText("Product"), { target: { value: "product-1" } });
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "12.5000" } });
    fireEvent.change(screen.getByLabelText("Agreed price"), { target: { value: "20000.00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save order" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
    const submitted = JSON.parse((fetchMock.mock.calls[2][1] as RequestInit).body as string);
    expect(submitted.lines[0].quantity).toBe("12.5000");
    expect(submitted.lines[0].agreed_unit_price).toBe("20000.00");
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
    fireEvent.change(within(productForm).getByLabelText("Name"), { target: { value: "Paper roll" } });
    fireEvent.submit(productForm);

    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
    const submitted = JSON.parse((fetchMock.mock.calls[2][1] as RequestInit).body as string);
    expect(submitted.code).toBeNull();
  });
});
