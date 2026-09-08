import type { OrderStatus } from "../types";

const labels: Record<OrderStatus, string> = {
  DRAFT: "Waiting",
  CONFIRMED: "Confirmed",
  SCHEDULED: "Scheduled",
  IN_PRODUCTION: "Producing",
  READY: "Ready",
  DELIVERY_PENDING: "Delivery pending",
  DELIVERED: "Delivered",
  INVOICED: "Invoiced",
  CLOSED: "Closed",
  CANCELLED: "Cancelled",
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{labels[status]}</span>;
}

