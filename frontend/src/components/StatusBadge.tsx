import type { OrderStatus } from "../types";
import { useT } from "../i18n";

interface StatusVisual {
  symbol: string;
  tone: "draft" | "pending" | "accepted" | "rejected";
}

const statusVisuals: Record<OrderStatus, StatusVisual> = {
  DRAFT: { symbol: "●", tone: "draft" },
  CONFIRMED: { symbol: "●", tone: "pending" },
  SCHEDULED: { symbol: "●", tone: "pending" },
  IN_PRODUCTION: { symbol: "●", tone: "pending" },
  READY: { symbol: "✓", tone: "accepted" },
  DELIVERY_PENDING: { symbol: "✓", tone: "accepted" },
  DELIVERED: { symbol: "✓", tone: "accepted" },
  INVOICED: { symbol: "✓", tone: "accepted" },
  CLOSED: { symbol: "✓", tone: "draft" },
  CANCELLED: { symbol: "×", tone: "rejected" },
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  const t = useT();
  const visual = statusVisuals[status] ?? {
    symbol: "●",
    tone: "draft" as const,
  };
  const label = t.orders.status[status] ?? status;

  return (
    <span
      className={`status-badge status-${status.toLowerCase()} status-tone-${visual.tone}`}
      role="status"
    >
      <span className="status-symbol" aria-hidden="true">
        {visual.symbol}
      </span>
      <span className="status-label">{label}</span>
    </span>
  );
}
