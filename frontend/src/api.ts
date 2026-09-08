import type { Customer, NewOrderLine, Order, OrderList, OrderStatus, Product } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = typeof body.detail === "string" ? body.detail : "Check the entered values";
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  customers: () => request<Customer[]>("/api/customers"),
  createCustomer: (payload: { name: string; tax_code?: string }) =>
    request<Customer>("/api/customers", {
      method: "POST",
      body: JSON.stringify({ ...payload, tax_code: payload.tax_code?.trim() || null }),
    }),
  products: () => request<Product[]>("/api/products"),
  createProduct: (payload: { code?: string; name: string; unit: string }) =>
    request<Product>("/api/products", {
      method: "POST",
      body: JSON.stringify({ ...payload, code: payload.code?.trim() || null }),
    }),
  orders: (search = "") =>
    request<OrderList>(`/api/orders?search=${encodeURIComponent(search)}&limit=500`),
  createOrder: (payload: {
    customer_id: string;
    order_date: string;
    required_date: string;
    notes: string;
    lines: NewOrderLine[];
  }) =>
    request<Order>("/api/orders", {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        lines: payload.lines.map(({ agreed_unit_price, product_id, ...line }) => ({
          ...line,
          product_id: product_id || null,
          agreed_unit_price: agreed_unit_price || null,
        })),
      }),
    }),
  changeStatus: (id: string, status: OrderStatus) =>
    request<Order>(`/api/orders/${id}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
};

