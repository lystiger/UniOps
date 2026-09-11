import { useCallback, useEffect, useMemo, useState } from "react";
import { api, formatApiError, UnauthorizedError } from "../api";
import { quantity } from "../format";
import { useT } from "../i18n";
import type { Dictionary } from "../i18n/types";
import type { Order, OrderStatus } from "../types";
import { AccountingBadge, AccountingPanel } from "./AccountingPanel";
import { StatusBadge } from "./StatusBadge";

interface ColumnDef {
  key: keyof Dictionary["orders"]["columns"];
  statuses: OrderStatus[];
}

const columnDefs: ColumnDef[] = [
  { key: "waitingConfirmed", statuses: ["DRAFT", "CONFIRMED"] },
  { key: "scheduled", statuses: ["SCHEDULED"] },
  { key: "producing", statuses: ["IN_PRODUCTION"] },
  { key: "ready", statuses: ["READY"] },
  {
    key: "deliveryDelivered",
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

function getNextLabel(status: OrderStatus, t: Dictionary): string | undefined {
  switch (status) {
    case "DRAFT":
      return t.orders.actions.confirm;
    case "CONFIRMED":
      return t.orders.actions.schedule;
    case "SCHEDULED":
      return t.orders.actions.startProduction;
    case "IN_PRODUCTION":
      return t.orders.actions.markReady;
    case "READY":
      return t.orders.actions.sendToDelivery;
    case "DELIVERY_PENDING":
      return t.orders.actions.markDelivered;
    case "DELIVERED":
      return t.orders.actions.markInvoiced;
    case "INVOICED":
      return t.orders.actions.closeOrder;
    default:
      return undefined;
  }
}

const cancellableStatuses: OrderStatus[] = [
  "DRAFT",
  "CONFIRMED",
  "SCHEDULED",
  "IN_PRODUCTION",
  "READY",
  "DELIVERY_PENDING",
];

function formatDue(value: string): string {
  const d = new Date(`${value}T00:00:00`);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}`;
}

function isOverdue(order: Order): boolean {
  const today = new Date();
  const localToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return order.required_date < localToday && !["DELIVERED", "INVOICED", "CLOSED", "CANCELLED"].includes(order.status);
}

// A stable identity. An inline default would be a new function on every render,
// which would change `load` every render and refetch the board without end.
const ignoreSessionLoss = () => undefined;

function lineSummary(order: Order, t: Dictionary): string {
  const first = order.lines[0];
  if (!first) return t.orders.noLines;
  const summary = `${quantity(first.quantity)} ${first.unit} · ${first.product?.name ?? first.description}`;
  return order.lines.length > 1 ? `${summary} ${t.orders.moreLines(order.lines.length - 1)}` : summary;
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
  const t = useT();

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
      setError(formatApiError(reason, t).message);
    } finally {
      setLoading(false);
    }
  }, [search, onSessionLost, t]);

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
      // A single-order read never computes accounting_status (see OrderRead) -
      // it comes back null here, not "not invoiced". Keep the board's last known
      // value rather than have a routine status change blank the badge.
      setOrders((items) =>
        items.map((item) =>
          item.id === updated.id ? { ...updated, accounting_status: item.accounting_status } : item,
        ),
      );
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(formatApiError(reason, t).message);
    } finally {
      setMovingId("");
    }
  }

  async function cancelOrder(order: Order) {
    if (!window.confirm(t.orders.actions.confirmCancel({ orderNumber: order.order_number }))) return;
    setMovingId(order.id);
    setError("");
    try {
      await api.changeStatus(order.id, "CANCELLED");
      setOrders((items) => items.filter((item) => item.id !== order.id));
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(formatApiError(reason, t).message);
    } finally {
      setMovingId("");
    }
  }

  return (
    <section className="board-page">
      <div className="page-heading">
        <div>
          <h1>{t.orders.title}</h1>
          <p className="page-context">
            {t.orders.activeOrdersSummary({ count: orders.length, overdueCount: dueCount })}
          </p>
        </div>
        <div className="board-actions">
          <label className="search-box">
            <span>{t.orders.searchLabel}</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t.orders.searchPlaceholder}
            />
          </label>
          {canWrite && (
            <button className="primary-button" onClick={onNewOrder}>
              {t.orders.actions.newOrderBtn}
            </button>
          )}
        </div>
      </div>

      {error && <div className="message error" role="alert">{error}</div>}
      {loading ? (
        <div className="loading-state">{t.orders.loading}</div>
      ) : (
        <div className="board-grid" aria-label={t.orders.boardAria}>
          {columnDefs.map((colDef) => {
            const columnTitle = t.orders.columns[colDef.key];
            const columnOrders = orders.filter((order) => colDef.statuses.includes(order.status));
            return (
              <section className="board-column" key={colDef.key}>
                <header>
                  <h2>{columnTitle}</h2>
                  <span>{columnOrders.length}</span>
                </header>
                <div className="card-stack">
                  {columnOrders.length === 0 && <p className="empty-column">{t.orders.emptyColumn}</p>}
                  {columnOrders.map((order) => {
                    const nextBtnLabel = getNextLabel(order.status, t);
                    return (
                      <article className={isOverdue(order) ? "order-card overdue" : "order-card"} key={order.id}>
                        <div className="ticket-rule" aria-hidden="true" />
                        <div className="card-topline">
                          <span className="order-number">{order.order_number}</span>
                          <StatusBadge status={order.status} />
                        </div>
                        <h3>{order.customer.name}</h3>
                        <p className="line-summary">{lineSummary(order, t)}</p>
                        <div className="due-row">
                          <span>{isOverdue(order) ? t.orders.overdueDelivery : t.orders.requiredLabel}</span>
                          <strong>{formatDue(order.required_date)}</strong>
                        </div>
                        <button
                          className="accounting-line"
                          type="button"
                          onClick={() => setAccountingOrder(order)}
                          aria-label={t.orders.accountingAria(order.order_number)}
                        >
                          <AccountingBadge status={order.accounting_status} />
                        </button>
                        {canWrite && nextStatus[order.status] && (
                          <button
                            className="advance-button"
                            disabled={movingId === order.id}
                            onClick={() => advance(order)}
                          >
                            {movingId === order.id ? t.orders.actions.updating : nextBtnLabel}
                          </button>
                        )}
                        {canWrite && cancellableStatuses.includes(order.status) && (
                          <button
                            className="cancel-order-button"
                            type="button"
                            disabled={movingId === order.id}
                            onClick={() => cancelOrder(order)}
                            aria-label={t.orders.actions.cancelOrderAria(order.order_number)}
                          >
                            {t.orders.actions.cancelOrder}
                          </button>
                        )}
                      </article>
                    );
                  })}
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
