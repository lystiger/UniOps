import { useMemo, useState } from "react";
import { api } from "../api";
import { isoDate, money } from "../format";
import { useApiResource } from "../hooks";
import { useT } from "../i18n";
import type { Dictionary } from "../i18n/types";
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

interface PipelineBucketDef {
  key: keyof Dictionary["overview"]["pipeline"]["buckets"];
  statuses: Order["status"][];
}

const pipelineBucketDefs: PipelineBucketDef[] = [
  { key: "waiting", statuses: ["DRAFT", "CONFIRMED"] },
  { key: "scheduled", statuses: ["SCHEDULED"] },
  { key: "producing", statuses: ["IN_PRODUCTION"] },
  { key: "ready", statuses: ["READY"] },
  { key: "deliveryPending", statuses: ["DELIVERY_PENDING", "DELIVERED"] },
  { key: "invoicedClosed", statuses: ["INVOICED", "CLOSED"] },
];

interface AttentionRow extends ExceptionItem {
  order?: Order;
}

function renderExceptionIssue(row: AttentionRow, t: Dictionary): string {
  switch (row.category) {
    case "DELIVERED_ORDER_NOT_INVOICED":
      return t.overview.attentionIssues.DELIVERED_ORDER_NOT_INVOICED;
    case "INVOICE_WITHOUT_ORDER":
      return t.overview.attentionIssues.INVOICE_WITHOUT_ORDER;
    case "AMBIGUOUS_INVOICE_CANDIDATES":
      return t.overview.attentionIssues.AMBIGUOUS_INVOICE_CANDIDATES;
    case "LINKED_CUSTOMER_MISMATCH":
      return t.overview.attentionIssues.LINKED_CUSTOMER_MISMATCH;
    case "LINKED_AMOUNT_MISMATCH":
      return t.overview.attentionIssues.LINKED_AMOUNT_MISMATCH({
        orderTotal: row.order_total ? money(row.order_total) : "—",
        invoiceSubtotal: row.invoice_subtotal ? money(row.invoice_subtotal) : "—",
        invoiceTotal: row.total_amount ? money(row.total_amount) : "—",
      });
    case "INVOICE_WITHOUT_CUSTOMER_CODE":
      return t.overview.attentionIssues.INVOICE_WITHOUT_CUSTOMER_CODE;
    default:
      // The backend's detail is English; a category this build doesn't know yet still reads in the UI language.
      return t.overview.attention.unknownIssue;
  }
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
  const t = useT();

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
      <PageHeader title={t.overview.title} />

      <Section>
        {orders.loading ? (
          <Skeleton rows={1} />
        ) : orders.error ? (
          <ErrorState>{t.overview.errors.loadOrders}</ErrorState>
        ) : (
          <StatRow>
            <Stat label={t.overview.stats.activeOrders} value={activeOrders.length} />
            <Stat label={t.overview.stats.producing} value={producingCount} tone="producing" />
            <Stat label={t.overview.stats.ready} value={readyCount} tone="ready" />
            <Stat label={t.overview.stats.deliveryPending} value={deliveryCount} />
          </StatRow>
        )}
      </Section>

      <Section
        title={t.overview.attention.title}
        action={
          exceptions.data && exceptions.data.total > 0 ? (
            <span className="section-count">
              {t.overview.attention.orderIssuesCount(orderTotalCount)} · {t.overview.attention.invoiceIssuesCount(invoiceTotalCount)}
            </span>
          ) : undefined
        }
      >
        {exceptions.loading ? (
          <Skeleton />
        ) : exceptions.error ? (
          <ErrorState>{t.overview.errors.loadExceptions}</ErrorState>
        ) : orderTotalCount === 0 && invoiceTotalCount === 0 ? (
          <EmptyState>{t.overview.attention.nothingNeedsAttention}</EmptyState>
        ) : (
          <div className="attention-groups">
            <div className="attention-group">
              <div className="attention-group-head">
                <span className="attention-group-title">
                  {t.overview.attention.orderExceptions} ({orderTotalCount})
                </span>
              </div>
              {orderTotalCount === 0 ? (
                <EmptyState>{t.overview.attention.noOrderExceptions}</EmptyState>
              ) : (
                <>
                  <DataTable
                    columns={[
                      {
                        key: "reference",
                        header: t.overview.attention.columns.reference,
                        render: (row: AttentionRow) => row.order?.order_number ?? row.reference,
                      },
                      {
                        key: "customer",
                        header: t.overview.attention.columns.customer,
                        render: (row: AttentionRow) =>
                          row.customer_name ?? row.order?.customer.name ?? "—",
                      },
                      {
                        key: "issue",
                        header: t.overview.attention.columns.issue,
                        render: (row: AttentionRow) => renderExceptionIssue(row, t),
                      },
                      {
                        key: "status",
                        header: t.overview.attention.columns.status,
                        render: (row: AttentionRow) =>
                          row.order ? <StatusBadge status={row.order.status} /> : "—",
                      },
                      {
                        key: "required",
                        header: t.overview.attention.columns.required,
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
                      {t.overview.attention.showingCount(orderRows.length, orderTotalCount)}
                    </p>
                  )}
                </>
              )}
            </div>

            {invoiceTotalCount > 0 && (
              <div className="attention-group">
                <div className="attention-group-head">
                  <span className="attention-group-title">
                    {t.overview.attention.invoiceBacklog} ({invoiceTotalCount})
                  </span>
                </div>
                <DataTable
                  columns={[
                    {
                      key: "reference",
                      header: t.overview.attention.columns.reference,
                      render: (row: AttentionRow) => row.reference,
                    },
                    {
                      key: "customer",
                      header: t.overview.attention.columns.customer,
                      render: (row: AttentionRow) => row.customer_name ?? "—",
                    },
                    {
                      key: "issue",
                      header: t.overview.attention.columns.issue,
                      render: (row: AttentionRow) => renderExceptionIssue(row, t),
                    },
                    {
                      key: "date",
                      header: t.overview.attention.columns.invoiceDate,
                      render: (row: AttentionRow) =>
                        row.document_date ? isoDate(row.document_date) : "—",
                    },
                    {
                      key: "amount",
                      header: t.overview.attention.columns.amount,
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
                      ? t.overview.attention.showingCount(invoiceRows.length, invoiceTotalCount)
                      : t.overview.attention.showingAll(invoiceRows.length)}
                  </span>
                  {invoiceTotalCount > 10 && (
                    <button
                      type="button"
                      className="attention-view-all-btn"
                      onClick={() => setShowAllInvoices((prev) => !prev)}
                    >
                      {showAllInvoices ? t.overview.attention.showTen : t.overview.attention.viewAll(invoiceTotalCount)}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </Section>

      <Section title={t.overview.pipeline.title}>
        {orders.loading ? (
          <Skeleton />
        ) : orders.error ? (
          <ErrorState>{t.overview.errors.loadOrders}</ErrorState>
        ) : (
          <DataTable
            columns={[
              {
                key: "label",
                header: t.overview.pipeline.columns.status,
                render: (row: PipelineBucketDef) => t.overview.pipeline.buckets[row.key],
              },
              {
                key: "count",
                header: t.overview.pipeline.columns.orders,
                align: "right",
                render: (row: PipelineBucketDef) =>
                  activeOrders.filter((order) => row.statuses.includes(order.status)).length,
              },
            ]}
            rows={pipelineBucketDefs}
            rowKey={(row) => row.key}
          />
        )}
      </Section>

      <Section title={t.overview.commercialSnapshot}>
        {commercial.loading || receivables.loading ? (
          <Skeleton rows={1} />
        ) : commercial.error ? (
          <ErrorState>{t.overview.errors.loadAnalytics}</ErrorState>
        ) : (
          <StatRow>
            <Stat label={t.overview.stats.sales} value={money(commercial.data?.sales.total)} />
            <Stat label={t.overview.stats.purchases} value={money(commercial.data?.purchases.total)} />
            <Stat
              label={t.overview.stats.receivablesOutstanding}
              value={
                receivables.error
                  ? "—"
                  : money(receivables.data?.total_outstanding ?? null)
              }
            />
            <Stat label={t.overview.stats.salesMinusPurchases} value={money(commercial.data?.sales_minus_purchases)} />
          </StatRow>
        )}
        {!receivables.loading &&
          !receivables.error &&
          receivables.data &&
          receivables.data.total_outstanding === null &&
          receivables.data.outstanding_status === "NO_PAYMENT_SOURCE" && (
            <p className="section-note">{t.accounting.outstandingExposesNote}.</p>
          )}
      </Section>

      <Section title={t.overview.easybooksSync}>
        <SyncStatus runs={sync.data} loading={sync.loading} />
        {sync.error && <ErrorState>{t.overview.errors.loadSync}</ErrorState>}
      </Section>

      <div className="overview-footer-actions">
        <button className="secondary-button" type="button" onClick={onNavigateOrders}>
          {t.overview.actions.viewOrderBoard}
        </button>
        {canWrite && (
          <button className="primary-button" type="button" onClick={onNewOrder}>
            {t.overview.actions.newOrder}
          </button>
        )}
      </div>
    </div>
  );
}
