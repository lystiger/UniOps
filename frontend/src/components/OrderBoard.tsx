import { useCallback, useEffect, useMemo, useState } from "react";
import { api, UnauthorizedError } from "../api";
import type { Order, OrderStatus } from "../types";
import { AccountingBadge, AccountingPanel } from "./AccountingPanel";
import { StatusBadge } from "./StatusBadge";

const columns: { title: string; statuses: OrderStatus[] }[] = [
  { title: "Waiting / confirmed", statuses: ["DRAFT", "CONFIRMED"] },
  { title: "Scheduled", statuses: ["SCHEDULED"] },
  { title: "Producing", statuses: ["IN_PRODUCTION"] },
  { title: "Ready", statuses: ["READY"] },
  {
    title: "Delivery / delivered",
    statuses: ["DELIVERY_PENDING", "DELIVERED", "INVOICED", "CLOSED"],
  },
];

const nextStatus: Partial<Record<OrderStatus, OrderStatus>> = {
  DRAFT: "CONFIRMED",
  CONFIRMED: "SCHEDULED",
  SCHEDULED: "IN_PRODUCTION",
  IN_PRODUCTION: "READY",
  READY: "DELIVERY_PENDING",
  DELIVERY_PENDING: "DELIVERED",
  DELIVERED: "INVOICED",
  INVOICED: "CLOSED",
};

const nextLabel: Partial<Record<OrderStatus, string>> = {
  DRAFT: "Confirm",
  CONFIRMED: "Schedule",
  SCHEDULED: "Start production",
  IN_PRODUCTION: "Mark ready",
  READY: "Send to delivery",
  DELIVERY_PENDING: "Mark delivered",
  DELIVERED: "Mark invoiced",
  INVOICED: "Close order",
};

function formatDue(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" }).format(
    new Date(`${value}T00:00:00`),
  );
}

function isOverdue(order: Order) {
  const today = new Date();
  const localToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return order.required_date < localToday && !["DELIVERED", "INVOICED", "CLOSED", "CANCELLED"].includes(order.status);
}

// A stable identity. An inline default would be a new function on every render,
// which would change `load` every render and refetch the board without end.
const ignoreSessionLoss = () => undefined;

function lineSummary(order: Order) {
  const first = order.lines[0];
  if (!first) return "No lines";
  const summary = `${first.quantity} ${first.unit} · ${first.product?.name ?? first.description}`;
  return order.lines.length > 1 ? `${summary} +${order.lines.length - 1}` : summary;
}

export function OrderBoard({
  refreshKey,
  onNewOrder,
  canWrite = true,
  onSessionLost = ignoreSessionLoss,
}: {
  refreshKey: number;
  onNewOrder: () => void;
  /** FACTORY_READ sees the board without any control that would change it. */
  canWrite?: boolean;
  onSessionLost?: () => void;
}) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [movingId, setMovingId] = useState("");
  const [accountingOrder, setAccountingOrder] = useState<Order | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.orders(search);
      setOrders(response.items.filter((order) => order.status !== "CANCELLED"));
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(reason instanceof Error ? reason.message : "Could not load orders");
    } finally {
      setLoading(false);
    }
  }, [search, onSessionLost]);

  useEffect(() => {
    const timer = window.setTimeout(load, search ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [load, refreshKey, search]);

  const dueCount = useMemo(() => orders.filter(isOverdue).length, [orders]);

  async function advance(order: Order) {
    const target = nextStatus[order.status];
    if (!target) return;
    setMovingId(order.id);
    setError("");
    try {
      const updated = await api.changeStatus(order.id, target);
      setOrders((items) => items.map((item) => (item.id === updated.id ? updated : item)));
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(reason instanceof Error ? reason.message : "Status was not changed");
    } finally {
      setMovingId("");
    }
  }

  return (
    <section className="board-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">01 / OPERATIONS · Production overview</p>
          <h1>Order board</h1>
          <p className="heading-sub">Tổng quan sản xuất &amp; tiến độ đơn hàng</p>
          <p className="heading-meta">{orders.length} active orders · <strong>{dueCount} overdue</strong></p>
        </div>
        <div className="board-actions">
          <label className="search-box">
            <span>Search</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Order or customer"
            />
          </label>
          {canWrite && (
            <button className="primary-button" onClick={onNewOrder}>+ New order</button>
          )}
        </div>
      </div>

      {error && <div className="message error" role="alert">{error}</div>}
      {loading ? (
        <div className="loading-state">Loading order board…</div>
      ) : (
        <div className="board-grid" aria-label="Order status board">
          {columns.map((column) => {
            const columnOrders = orders.filter((order) => column.statuses.includes(order.status));
            return (
              <section className="board-column" key={column.title}>
                <header>
                  <h2>{column.title}</h2>
                  <span>{columnOrders.length}</span>
                </header>
                <div className="card-stack">
                  {columnOrders.length === 0 && <p className="empty-column">No orders here</p>}
                  {columnOrders.map((order) => (
                    <article className={isOverdue(order) ? "order-card overdue" : "order-card"} key={order.id}>
                      <div className="ticket-rule" aria-hidden="true" />
                      <div className="card-topline">
                        <span className="order-number">{order.order_number}</span>
                        <StatusBadge status={order.status} />
                      </div>
                      <h3>{order.customer.name}</h3>
                      <p className="line-summary">{lineSummary(order)}</p>
                      <div className="due-row">
                        <span>{isOverdue(order) ? "Overdue" : "Required"}</span>
                        <strong>{formatDue(order.required_date)}</strong>
                      </div>
                      <button
                        className="accounting-line"
                        type="button"
                        onClick={() => setAccountingOrder(order)}
                        aria-label={`Accounting for ${order.order_number}`}
                      >
                        <AccountingBadge status={order.accounting_status} />
                      </button>
                      {canWrite && nextStatus[order.status] && (
                        <button
                          className="advance-button"
                          disabled={movingId === order.id}
                          onClick={() => advance(order)}
                        >
                          {movingId === order.id ? "Updating…" : nextLabel[order.status]}
                        </button>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
      {accountingOrder && (
        <AccountingPanel
          order={accountingOrder}
          canWrite={canWrite}
          onClose={() => setAccountingOrder(null)}
          onChanged={load}
          onSessionLost={onSessionLost}
        />
      )}
    </section>
  );
}
