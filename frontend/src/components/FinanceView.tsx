import { useCallback, useEffect, useState } from "react";
import { api, formatApiError, UnauthorizedError } from "../api";
import { isoDate, money, number } from "../format";
import { useApiResource } from "../hooks";
import { useT } from "../i18n";
import type { Dictionary } from "../i18n/types";
import {
  DataTable,
  DateRangeFilter,
  EmptyState,
  ErrorState,
  FilterBar,
  PageHeader,
  Section,
  Skeleton,
  Stat,
  StatRow,
  SyncStatus,
} from "./primitives";
import type { CustomerReceivable, CustomerReceivableDetail, MonthlyAmount } from "../types";

type Tab = "sales" | "purchases" | "receivables";

/** Reads/writes `?from=&to=&tab=` so a shared link or a back-navigation keeps
 * the same filter, without pulling in a router for one page. */
function readQuery() {
  const params = new URLSearchParams(window.location.search);
  return {
    fromDate: params.get("from") ?? "",
    toDate: params.get("to") ?? "",
    tab: (params.get("tab") as Tab | null) ?? "sales",
  };
}

function writeQuery(next: { fromDate: string; toDate: string; tab: Tab }) {
  const params = new URLSearchParams(window.location.search);
  if (next.fromDate) params.set("from", next.fromDate);
  else params.delete("from");
  if (next.toDate) params.set("to", next.toDate);
  else params.delete("to");
  params.set("tab", next.tab);
  const query = params.toString();
  window.history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
}

function MonthTable({ rows, t }: { rows: MonthlyAmount[]; t: Dictionary }) {
  if (rows.length === 0) return <EmptyState>{t.finance.noDocumentsDatedInPeriod}</EmptyState>;
  return (
    <DataTable
      columns={[
        { key: "month", header: t.finance.columns.month, render: (row: MonthlyAmount) => row.month },
        {
          key: "count",
          header: t.finance.columns.documents,
          align: "right",
          render: (row: MonthlyAmount) => number(row.document_count),
        },
        {
          key: "amount",
          header: t.finance.columns.amount,
          align: "right",
          render: (row: MonthlyAmount) => money(row.amount),
        },
      ]}
      rows={rows}
      rowKey={(row) => row.month}
    />
  );
}

export function FinanceView({ onSessionLost }: { onSessionLost: () => void }) {
  const initial = readQuery();
  const [tab, setTab] = useState<Tab>(initial.tab);
  const [fromDate, setFromDate] = useState(initial.fromDate);
  const [toDate, setToDate] = useState(initial.toDate);
  const [drilldownId, setDrilldownId] = useState<string | null>(null);
  const t = useT();

  useEffect(() => {
    writeQuery({ fromDate, toDate, tab });
  }, [fromDate, toDate, tab]);

  const window_ = { from_date: fromDate || undefined, to_date: toDate || undefined };

  const overview = useApiResource(() => api.analyticsOverview(window_), [fromDate, toDate], onSessionLost);
  const sales = useApiResource(() => api.analyticsSales(window_), [fromDate, toDate], onSessionLost);
  const purchases = useApiResource(() => api.analyticsPurchases(window_), [fromDate, toDate], onSessionLost);
  const receivables = useApiResource(() => api.analyticsReceivables(window_), [fromDate, toDate], onSessionLost);
  const sync = useApiResource(() => api.syncRuns(5), [], onSessionLost);

  return (
    <div className="finance-page">
      <PageHeader title={t.finance.title} />

      <FilterBar>
        <DateRangeFilter
          fromDate={fromDate}
          toDate={toDate}
          onChange={(next) => {
            setFromDate(next.fromDate);
            setToDate(next.toDate);
          }}
        />
        <SyncStatus runs={sync.data} loading={sync.loading} />
      </FilterBar>

      <Section title={t.finance.summary}>
        {overview.loading || receivables.loading ? (
          <Skeleton rows={1} />
        ) : overview.error ? (
          <ErrorState>{t.finance.errors.loadAnalytics}</ErrorState>
        ) : (
          <StatRow>
            <Stat label={t.finance.stats.sales} value={money(overview.data?.sales.total)} />
            <Stat label={t.finance.stats.purchases} value={money(overview.data?.purchases.total)} />
            <Stat
              label={t.finance.receivablesOutstanding}
              value={receivables.error ? "—" : money(receivables.data?.total_outstanding ?? null)}
            />
            <Stat label={t.finance.salesMinusPurchases} value={money(overview.data?.sales_minus_purchases)} />
          </StatRow>
        )}
      </Section>

      <div className="tabs" role="tablist" aria-label={t.finance.title}>
        {(["sales", "purchases", "receivables"] as Tab[]).map((value) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            className={tab === value ? "tab-item active" : "tab-item"}
            type="button"
            onClick={() => setTab(value)}
          >
            {value === "sales"
              ? t.finance.tabs.sales
              : value === "purchases"
                ? t.finance.tabs.purchases
                : t.finance.tabs.receivables}
          </button>
        ))}
      </div>

      {tab === "sales" && (
        <Section>
          {sales.loading ? (
            <Skeleton />
          ) : sales.error ? (
            <ErrorState>{t.finance.errors.loadSales}</ErrorState>
          ) : sales.data && sales.data.document_count === 0 ? (
            <EmptyState>{t.finance.noSalesRecords}</EmptyState>
          ) : (
            <>
              <StatRow>
                <Stat label={t.finance.stats.documents} value={number(sales.data?.document_count)} />
                <Stat label={t.finance.stats.customers} value={number(sales.data?.customer_count)} />
                <Stat label={t.finance.stats.total} value={money(sales.data?.total)} />
                <Stat label={t.finance.stats.vat} value={money(sales.data?.vat_amount)} />
              </StatRow>
              {sales.data && sales.data.undated_document_count > 0 && (
                <p className="section-note">
                  {t.finance.undatedDocumentsNote(sales.data.undated_document_count)}
                </p>
              )}
              {sales.data && <MonthTable rows={sales.data.by_month} t={t} />}
            </>
          )}
        </Section>
      )}

      {tab === "purchases" && (
        <Section>
          {purchases.loading ? (
            <Skeleton />
          ) : purchases.error ? (
            <ErrorState>{t.finance.errors.loadPurchases}</ErrorState>
          ) : purchases.data && purchases.data.document_count === 0 ? (
            <EmptyState>{t.finance.noPurchaseRecords}</EmptyState>
          ) : (
            <>
              <StatRow>
                <Stat label={t.finance.stats.documents} value={number(purchases.data?.document_count)} />
                <Stat label={t.finance.stats.suppliers} value={number(purchases.data?.supplier_count)} />
                <Stat label={t.finance.stats.total} value={money(purchases.data?.total)} />
                <Stat label={t.finance.stats.vat} value={money(purchases.data?.vat_amount)} />
              </StatRow>
              {purchases.data && purchases.data.undated_document_count > 0 && (
                <p className="section-note">
                  {t.finance.undatedDocumentsNote(purchases.data.undated_document_count)}
                </p>
              )}
              {purchases.data && <MonthTable rows={purchases.data.by_month} t={t} />}
            </>
          )}
        </Section>
      )}

      {tab === "receivables" && (
        <Section>
          {receivables.loading ? (
            <Skeleton />
          ) : receivables.error ? (
            <ErrorState>{t.finance.errors.loadReceivables}</ErrorState>
          ) : receivables.data && receivables.data.invoice_count === 0 ? (
            <EmptyState>{t.finance.noInvoicesPeriod}</EmptyState>
          ) : (
            <>
              <StatRow>
                <Stat label={t.finance.stats.invoiced} value={money(receivables.data?.total_invoiced)} />
                <Stat label={t.finance.stats.invoices} value={number(receivables.data?.invoice_count)} />
                <Stat label={t.finance.stats.linkedToOrder} value={number(receivables.data?.linked_invoice_count)} />
                <Stat label={t.finance.stats.unlinked} value={number(receivables.data?.unlinked_invoice_count)} />
              </StatRow>
              {receivables.data && receivables.data.total_outstanding === null && (
                <p className="section-note">
                  {t.finance.outstandingBalanceNote(
                    receivables.data.outstanding_status?.startsWith("EasyBooks exposes no paid or outstanding amount")
                      ? t.finance.outstandingExposesNote
                      : receivables.data.outstanding_status,
                  )}
                </p>
              )}
              {receivables.data && (
                <DataTable
                  columns={[
                    {
                      key: "customer",
                      header: t.finance.columns.customer,
                      render: (row: CustomerReceivable) => row.customer_name ?? row.customer_code,
                    },
                    {
                      key: "invoices",
                      header: t.finance.columns.invoices,
                      align: "right",
                      render: (row: CustomerReceivable) => number(row.invoice_count),
                    },
                    {
                      key: "invoiced",
                      header: t.finance.columns.invoiced,
                      align: "right",
                      render: (row: CustomerReceivable) => money(row.total_invoiced),
                    },
                    {
                      key: "oldest",
                      header: t.finance.columns.oldestInvoice,
                      render: (row: CustomerReceivable) => isoDate(row.oldest_invoice_date),
                    },
                    {
                      key: "outstanding",
                      header: t.finance.columns.outstanding,
                      align: "right",
                      render: (row: CustomerReceivable) =>
                        row.outstanding_amount === null ? t.finance.unavailable : money(row.outstanding_amount),
                    },
                  ]}
                  rows={receivables.data.customers}
                  rowKey={(row) => row.customer_code}
                  onRowClick={(row) => setDrilldownId(row.customer_id!)}
                  isRowClickable={(row) => row.customer_id !== null}
                  rowLabel={(row) => t.finance.invoicesForCustomerRowAria(row.customer_name ?? row.customer_code)}
                />
              )}
            </>
          )}
        </Section>
      )}

      {drilldownId && (
        <CustomerReceivableDrawer
          customerId={drilldownId}
          onClose={() => setDrilldownId(null)}
          onSessionLost={onSessionLost}
        />
      )}
    </div>
  );
}

/** One customer's invoices: what {@link CustomerReceivable} rows drill into. */
function CustomerReceivableDrawer({
  customerId,
  onClose,
  onSessionLost,
}: {
  customerId: string;
  onClose: () => void;
  onSessionLost: () => void;
}) {
  const [detail, setDetail] = useState<CustomerReceivableDetail | null>(null);
  const [error, setError] = useState("");
  const t = useT();

  const load = useCallback(async () => {
    try {
      setDetail(await api.customerReceivable(customerId));
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(formatApiError(reason, t).message);
    }
  }, [customerId, onSessionLost, t]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div
      className="accounting-overlay"
      role="dialog"
      aria-label={detail ? t.finance.customerInvoicesAria(detail.customer_name) : t.finance.stats.invoices}
    >
      <div className="accounting-panel">
        <header>
          <div>
            <h2>{detail?.customer_name ?? t.common.loading}</h2>
          </div>
          <button className="secondary-button" type="button" onClick={onClose}>
            {t.common.close}
          </button>
        </header>
        {error && <ErrorState>{error}</ErrorState>}
        {!detail ? (
          <p className="loading-state">{t.finance.loadingInvoices}</p>
        ) : (
          <>
            <dl className="accounting-facts">
              <div>
                <dt>{t.finance.stats.invoices}</dt>
                <dd>{number(detail.invoice_count)}</dd>
              </div>
              <div>
                <dt>{t.finance.columns.invoiced}</dt>
                <dd>{money(detail.total_invoiced)}</dd>
              </div>
              <div>
                <dt>{t.finance.columns.outstanding}</dt>
                <dd>{detail.total_outstanding === null ? "—" : money(detail.total_outstanding)}</dd>
              </div>
            </dl>
            {detail.total_outstanding === null && (
              <p className="accounting-note">
                {detail.outstanding_status?.startsWith("EasyBooks exposes no paid or outstanding amount")
                  ? t.finance.outstandingExposesNote
                  : detail.outstanding_status}.
              </p>
            )}
            {detail.invoices.length === 0 ? (
              <EmptyState>{t.finance.noInvoicesForCustomer}</EmptyState>
            ) : (
              <DataTable
                columns={[
                  { key: "invoice", header: t.finance.stats.invoices, render: (row) => row.invoice_number ?? row.sales_document_id },
                  { key: "date", header: t.finance.columns.date, render: (row) => isoDate(row.document_date) },
                  { key: "amount", header: t.finance.columns.amount, align: "right", render: (row) => money(row.total_amount) },
                  {
                    key: "outstanding",
                    header: t.finance.columns.outstanding,
                    align: "right",
                    render: (row) => (row.outstanding_amount === null ? t.finance.unavailable : money(row.outstanding_amount)),
                  },
                  { key: "order", header: t.finance.columns.linkedOrder, render: (row) => row.linked_order_numbers.join(", ") || "—" },
                ]}
                rows={detail.invoices}
                rowKey={(row) => row.sales_document_id}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
