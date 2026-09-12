import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProductsView } from "./ProductsView";

afterEach(() => vi.restoreAllMocks());

const towel = {
  id: "product-1",
  sku: "UG000001",
  name: "Khăn giấy lau tay 175gr",
  unit: "Gói",
  category: "hand-towel",
  status: "active",
  specifications: { gsm: 22 },
  code: "TP.KT175",
  easybooks_material_goods_id: "eb-175",
  created_at: "2026-09-13T00:00:00Z",
  updated_at: "2026-09-13T00:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

describe("ProductsView", () => {
  it("shows the SKU and the EasyBooks code of each canonical product", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json([towel]));
    render(<ProductsView canWrite={false} onSessionLost={() => undefined} />);

    const row = (await screen.findByText("UG000001")).closest("tr")!;
    expect(within(row).getByText("TP.KT175")).toBeInTheDocument();
    expect(within(row).getByText("gsm: 22")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /discontinue/i })).not.toBeInTheDocument();
  });

  it("creates a product without sending a SKU and reports the one UniOps assigned", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(json({ ...towel, id: "product-2", sku: "UG000002" }, 201))
      .mockResolvedValue(json([]));
    render(<ProductsView canWrite onSessionLost={() => undefined} />);

    fireEvent.click(await screen.findByRole("button", { name: "+ New product" }));
    const form = screen.getByLabelText("Official name").closest("form")!;
    expect(within(form).queryByLabelText(/sku/i)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Official name"), { target: { value: "Napkin 2-ply" } });
    fireEvent.change(screen.getByLabelText("Unit"), { target: { value: "Gói" } });
    fireEvent.change(screen.getByLabelText("Specifications (JSON)"), { target: { value: '{"ply": 2}' } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Product UG000002 created")).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/products");
    const sent = JSON.parse((init as RequestInit).body as string);
    expect(sent).not.toHaveProperty("sku");
    expect(sent).toMatchObject({ name: "Napkin 2-ply", unit: "Gói", specifications: { ply: 2 } });
  });

  it("refuses specifications that are not a JSON object before calling the API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json([]));
    render(<ProductsView canWrite onSessionLost={() => undefined} />);

    fireEvent.click(await screen.findByRole("button", { name: "+ New product" }));
    fireEvent.change(screen.getByLabelText("Official name"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Unit"), { target: { value: "Gói" } });
    fireEvent.change(screen.getByLabelText("Specifications (JSON)"), { target: { value: "[1, 2]" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("JSON object");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("discontinues a product through PATCH with only the status", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json([towel]))
      .mockResolvedValueOnce(json({ ...towel, status: "discontinued" }))
      .mockResolvedValue(json([{ ...towel, status: "discontinued" }]));
    render(<ProductsView canWrite onSessionLost={() => undefined} />);

    fireEvent.click(await screen.findByRole("button", { name: "Discontinue" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/products/product-1");
    expect((init as RequestInit).method).toBe("PATCH");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({ status: "discontinued" });
    expect(await screen.findByRole("button", { name: "Reactivate" })).toBeInTheDocument();
  });
});
