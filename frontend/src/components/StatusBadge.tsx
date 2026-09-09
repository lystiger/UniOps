import type { OrderStatus } from "../types";

interface StatusVisual {
  label: string;
  symbol: string;
  tone: "draft" | "pending" | "accepted" | "rejected";
}

const statusVisuals: Record<OrderStatus, StatusVisual> = {
  DRAFT: { label: "Waiting", symbol: "●", tone: "draft" },
  CONFIRMED: { label: "Confirmed", symbol: "●", tone: "pending" },
  SCHEDULED: { label: "Scheduled", symbol: "●", tone: "pending" },
  IN_PRODUCTION: { label: "Producing", symbol: "●", tone: "pending" },
  READY: { label: "Ready", symbol: "✓", tone: "accepted" },
  DELIVERY_PENDING: { label: "Delivery pending", symbol: "✓", tone: "accepted" },
  DELIVERED: { label: "Delivered", symbol: "✓", tone: "accepted" },
  INVOICED: { label: "Invoiced", symbol: "✓", tone: "accepted" },
  CLOSED: { label: "Closed", symbol: "✓", tone: "draft" },
  CANCELLED: { label: "Cancelled", symbol: "×", tone: "rejected" },
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  const visual = statusVisuals[status] ?? {
    label: status,
    symbol: "●",
    tone: "draft" as const,
  };

  return (
    <span
      className={`status-badge status-${status.toLowerCase()} status-tone-${visual.tone}`}
      role="status"
    >
      <span className="status-symbol" aria-hidden="true">
        {visual.symbol}
      </span>
      <span className="status-label">{visual.label}</span>
    </span>
  );
}

