import type {
  Customer,
  InvoiceCandidate,
  NewOrderLine,
  Order,
  OrderAccounting,
  OrderList,
  OrderStatus,
  Product,
  User,
} from "./types";

/** The session is missing or expired. The app answers this by showing sign-in. */
export class UnauthorizedError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    // The session lives in an HttpOnly cookie, so it has to be sent explicitly
    // for anything other than a plain same-origin default.
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = typeof body.detail === "string" ? body.detail : "Check the entered values";
    // A 401 on sign-in means the credentials were wrong and the reason belongs
    // on screen; a 401 anywhere else means the session ended. Both carry the
    // server's wording, and only the type tells the app which happened.
    throw response.status === 401 ? new UnauthorizedError(detail) : new Error(detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/auth/me"),
  login: (username: string, password: string) =>
    request<User>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  changePassword: (current_password: string, new_password: string) =>
    request<User>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
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
  orderAccounting: (id: string) => request<OrderAccounting>(`/api/orders/${id}/accounting`),
  invoiceCandidates: (id: string) =>
    request<InvoiceCandidate[]>(`/api/orders/${id}/invoice-candidates`),
  linkInvoice: (id: string, salesDocumentId: string) =>
    request<OrderAccounting>(`/api/orders/${id}/invoice-links`, {
      method: "POST",
      body: JSON.stringify({ sales_document_id: salesDocumentId }),
    }),
  unlinkInvoice: (id: string, linkId: string) =>
    request<OrderAccounting>(`/api/orders/${id}/invoice-links/${linkId}`, { method: "DELETE" }),
};
