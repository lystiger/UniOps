import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const officeUser = {
  id: "user-1",
  username: "office",
  full_name: "Front Desk",
  role: "OFFICE",
  is_active: true,
  last_login_at: null,
};

const factoryUser = { ...officeUser, id: "user-2", username: "factory", full_name: null, role: "FACTORY_READ" };

const order = {
  id: "order-1",
  order_number: "UO-20260909-ABC123",
  customer: { id: "customer-1", name: "Fixture Customer", tax_code: null, easybooks_accounting_object_code: null },
  status: "DRAFT",
  order_date: "2026-09-09",
  required_date: "2026-09-12",
  notes: null,
  lines: [],
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

describe("App", () => {
  it("shows sign-in and no order data when there is no session", async () => {
    route({ "/api/auth/me": () => json({ detail: "sign in to use UniOps" }, 401) });

    render(<App />);

    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("Order board")).not.toBeInTheDocument();
  });

  it("opens the order desk once credentials are accepted", async () => {
    route({
      "/api/auth/me": () => json({ detail: "sign in to use UniOps" }, 401),
      "/api/auth/login": () => json(officeUser),
      "/api/orders": () => json({ items: [], total: 0 }),
    });

    render(<App />);

    fireEvent.change(await screen.findByLabelText("Username"), { target: { value: "office" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "office-password-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Order board" })).toBeInTheDocument();
    expect(screen.getByText("Front Desk")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "+ New order" }).length).toBeGreaterThan(0);
  });

  it("gives a factory reader the board without any control that changes it", async () => {
    route({
      "/api/auth/me": () => json(factoryUser),
      "/api/orders": () => json({ items: [order], total: 1 }),
    });

    render(<App />);

    expect(await screen.findByText("Fixture Customer")).toBeInTheDocument();
    expect(screen.getByText("Factory · read only")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "+ New order" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
  });

  it("returns to sign-in when the session ends while the board is open", async () => {
    let signedIn = true;
    route({
      "/api/auth/me": () => json(officeUser),
      "/api/orders": () =>
        signedIn ? json({ items: [], total: 0 }) : json({ detail: "sign in to use UniOps" }, 401),
      "/api/auth/logout": () => new Response(null, { status: 204 }),
    });

    render(<App />);
    await screen.findByRole("heading", { name: "Order board" });

    signedIn = false;
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "anything" } });

    await waitFor(() => expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument());
  });
});
