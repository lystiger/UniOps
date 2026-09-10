import { useMemo, useState } from "react";
import { api } from "../api";
import { isoDate, money, today } from "../format";
import { useApiResource } from "../hooks";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  Section,
  Skeleton,
  Stat,
  StatRow,
  SyncStatus,
} from "./primitives";
import { StatusBadge } from "./StatusBadge";
import type { ExceptionCategory, ExceptionItem, Order } from "../types";

const ORDER_CATEGORIES: Set<ExceptionCategory> = new Set([
  "DELIVERED_ORDER_NOT_INVOICED",
  "AMBIGUOUS_INVOICE_CANDIDATES",
  "LINKED_CUSTOMER_MISMATCH",
  "LINKED_AMOUNT_MISMATCH",
]);

const INVOICE_CATEGORIES: Set<ExceptionCategory> = new Set([
  "INVOICE_WITHOUT_ORDER",
  "INVOICE_WITHOUT_CUSTOMER_CODE",
]);

const pipelineBuckets: { label: string; statuses: Order["status"][] }[] = [
  { label: "Waiting", statuses: ["DRAFT", "CONFIRMED"] },
  { label: "Scheduled", statuses: ["SCHEDULED"] },
  { label: "Producing", statuses: ["IN_PRODUCTION"] },
  { label: "Ready", statuses: ["READY"] },
  { label: "Delivery pending", statuses: ["DELIVERY_PENDING", "DELIVERED"] },
  { label: "Invoiced / closed", statuses: ["INVOICED", "CLOSED"] },
];

interface AttentionRow extends ExceptionItem {
  order?: Order;
}

export function OverviewView({
  onNavigateOrders,
  onNewOrder,
  canWrite,
  onSessionLost,
}: {
  onNavigateOrders: () => void;
  onNewOrder: () => void;
  canWrite: boolean;
  onSessionLost: () => void;
}) {
  const [showAllInvoices, setShowAllInvoices] = useState(false);
  const orders = useApiResource(() => api.orders(""), [], onSessionLost);
  const exceptions = useApiResource(
    () => api.exceptions(showAllInvoices ? 500 : 10),
    [showAllInvoices],
    onSessionLost,
  );
  const commercial = useApiResource(() => api.analyticsOverview(), [], onSessionLost);
  const receivables = useApiResource(() => api.analyticsReceivables(), [], onSessionLost);
  const sync = useApiResource(() => api.syncRuns(5), [], onSessionLost);

  const activeOrders = useMemo(
    () => (orders.data?.items ?? []).filter((order) => order.status !== "CANCELLED"),
    [orders.data],
  );
  const orderById = useMemo(() => {
    const map = new Map<string, Order>();
    for (const order of activeOrders) map.set(order.id, order);
    return map;
  }, [activeOrders]);

  const producingCount = activeOrders.filter((o) => o.status === "IN_PRODUCTION").length;
  const readyCount = activeOrders.filter((o) => o.status === "READY").length;
  const deliveryCount = activeOrders.filter((o) =>
    ["DELIVERY_PENDING", "DELIVERED"].includes(o.status),
  ).length;

  const { orderRows, invoiceRows, orderTotalCount, invoiceTotalCount } = useMemo(() => {
    const groups = exceptions.data?.groups ?? [];
    let oTotal = 0;
    let iTotal = 0;
    const oItems: AttentionRow[] = [];
    const iItems: AttentionRow[] = [];

    for (const group of groups) {
      if (ORDER_CATEGORIES.has(group.category)) {
        oTotal += group.count;
        for (const item of group.items) {
          oItems.push({
            ...item,
            order: item.order_id ? orderById.get(item.order_id) : undefined,
          });
        }
      } else if (INVOICE_CATEGORIES.has(group.category)) {
        iTotal += group.count;
        for (const item of group.items) {
          iItems.push({
            ...item,
            order: item.order_id ? orderById.get(item.order_id) : undefined,
          });
        }
      }
    }

    return {
      orderRows: oItems,
      invoiceRows: iItems,
      orderTotalCount: oTotal,
      invoiceTotalCount: iTotal,
    };
  }, [exceptions.data, orderById]);

  return (
    <div className="overview-page">
      <PageHeader title="Overview" context={isoDate(today())} />

      <Section>
        {orders.loading ? (
          <Skeleton rows={1} />
        ) : orders.error ? (
          <ErrorState>Could not load orders.</ErrorState>
        ) : (
          <StatRow>
            <Stat label="Active orders" value={activeOrders.length} />
            <Stat label="Producing" value={producingCount} tone="producing" />
            <Stat label="Ready" value={readyCount} tone="ready" />
            <Stat label="Delivery pending" value={deliveryCount} />
          </StatRow>
        )}
      </Section>

      <Section
        title="Needs attention"
        action={
          exceptions.data && exceptions.data.total > 0 ? (
            <span className="section-count">
              {orderTotalCount} order · {invoiceTotalCount} invoice issues
            </span>
          ) : undefined
        }
      >
        {exceptions.loading ? (
          <Skeleton />
        ) : exceptions.error ? (
          <ErrorState>Could not load exceptions.</ErrorState>
        ) : orderTotalCount === 0 && invoiceTotalCount === 0 ? (
          <EmptyState>Nothing needs attention.</EmptyState>
        ) : (
          <div className="attention-groups">
            {orderTotalCount > 0 && (
              <div className="attention-group">
                <div className="attention-group-head">
                  <span className="attention-group-title">
                    Order exceptions ({orderTotalCount})
                  </span>
                </div>
                <DataTable
                  columns={[
                    {
                      key: "reference",
                      header: "Reference",
                      render: (row: AttentionRow) => row.order?.order_number ?? row.reference,
                    },
                    {
                      key: "customer",
                      header: "Customer",
                      render: (row: AttentionRow) =>
                        row.customer_name ?? row.order?.customer.name ?? "—",
                    },
                    { key: "issue", header: "Issue", render: (row: AttentionRow) => row.detail },
                    {
                      key: "status",
                      header: "Status",
                      render: (row: AttentionRow) =>
                        row.order ? <StatusBadge status={row.order.status} /> : "—",
                    },
                    {
                      key: "required",
                      header: "Required",
                      render: (row: AttentionRow) =>
                        row.document_date
                          ? isoDate(row.document_date)
                          : row.order
                            ? isoDate(row.order.required_date)
                            : "—",
                    },
                  ]}
                  rows={orderRows}
                  rowKey={(row) => `${row.category}-${row.reference}`}
                />
                {orderTotalCount > orderRows.length && (
                  <p className="section-note">
                    Showing {orderRows.length} of {orderTotalCount}
                  </p>
                )}
              </div>
            )}

            {invoiceTotalCount > 0 && (
              <div className="attention-group">
                <div className="attention-group-head">
                  <span className="attention-group-title">
                    Invoice backlog & data issues ({invoiceTotalCount})
                  </span>
                </div>
                <DataTable
                  columns={[
                    {
                      key: "reference",
                      header: "Reference",
                      render: (row: AttentionRow) => row.reference,
                    },
                    {
                      key: "customer",
                      header: "Customer",
                      render: (row: AttentionRow) => row.customer_name ?? "—",
                    },
                    { key: "issue", header: "Issue", render: (row: AttentionRow) => row.detail },
                    {
                      key: "date",
                      header: "Invoice date",
                      render: (row: AttentionRow) =>
                        row.document_date ? isoDate(row.document_date) : "—",
                    },
                    {
                      key: "amount",
                      header: "Amount",
                      align: "right",
                      render: (row: AttentionRow) =>
                        row.total_amount ? money(row.total_amount) : "—",
                    },
                  ]}
                  rows={invoiceRows}
                  rowKey={(row) => `${row.category}-${row.reference}`}
                />
                <div className="attention-pagination-bar">
                  <span>
                    {invoiceTotalCount > invoiceRows.length
                      ? `Showing ${invoiceRows.length} of ${invoiceTotalCount}`
                      : `Showing all ${invoiceRows.length}`}
                  </span>
                  {invoiceTotalCount > 10 && (
                    <button
                      type="button"
                      className="attention-view-all-btn"
                      onClick={() => setShowAllInvoices((prev) => !prev)}
                    >
                      {showAllInvoices ? "Show 10" : `View all (${invoiceTotalCount})`}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </Section>

      <Section title="Production pipeline">
        {orders.loading ? (
          <Skeleton />
        ) : orders.error ? (
          <ErrorState>Could not load orders.</ErrorState>
        ) : (
          <DataTable
            columns={[
              { key: "label", header: "Status", render: (row: (typeof pipelineBuckets)[number]) => row.label },
              {
                key: "count",
                header: "Orders",
                align: "right",
                render: (row: (typeof pipelineBuckets)[number]) =>
                  activeOrders.filter((order) => row.statuses.includes(order.status)).length,
              },
            ]}
            rows={pipelineBuckets}
            rowKey={(row) => row.label}
          />
        )}
      </Section>

      <Section title="Commercial snapshot">
        {commercial.loading || receivables.loading ? (
          <Skeleton rows={1} />
        ) : commercial.error ? (
          <ErrorState>Could not load EasyBooks analytics.</ErrorState>
        ) : (
          <StatRow>
            <Stat label="Sales" value={money(commercial.data?.sales.total)} />
            <Stat label="Purchases" value={money(commercial.data?.purchases.total)} />
            <Stat
              label="Receivables outstanding"
              value={
                receivables.error
                  ? "—"
                  : money(receivables.data?.total_outstanding ?? null)
              }
            />
            <Stat label="Sales − purchases" value={money(commercial.data?.sales_minus_purchases)} />
          </StatRow>
        )}
        {!receivables.loading && !receivables.error && receivables.data && receivables.data.total_outstanding === null && (
          <p className="section-note">{receivables.data.outstanding_status}.</p>
        )}
      </Section>

      <Section title="EasyBooks sync">
        <SyncStatus runs={sync.data} loading={sync.loading} />
        {sync.error && <ErrorState>Could not load synchronization history.</ErrorState>}
      </Section>

      <div className="overview-footer-actions">
        <button className="secondary-button" type="button" onClick={onNavigateOrders}>
          View order board
        </button>
        {canWrite && (
          <button className="primary-button" type="button" onClick={onNewOrder}>
            + New order
          </button>
        )}
      </div>
    </div>
  );
}
