import { useCallback, useEffect, useState } from "react";
import { api, UnauthorizedError } from "../api";
import { isoDate, money, number } from "../format";
import { useApiResource } from "../hooks";
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

function monthTable(rows: MonthlyAmount[]) {
  if (rows.length === 0) return <EmptyState>No documents with a date in this period.</EmptyState>;
  return (
    <DataTable
      columns={[
        { key: "month", header: "Month", render: (row: MonthlyAmount) => row.month },
        { key: "count", header: "Documents", align: "right", render: (row: MonthlyAmount) => number(row.document_count) },
        { key: "amount", header: "Amount", align: "right", render: (row: MonthlyAmount) => money(row.amount) },
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
      <PageHeader title="Finance" />

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

      <Section title="Summary">
        {overview.loading || receivables.loading ? (
          <Skeleton rows={1} />
        ) : overview.error ? (
          <ErrorState>Could not load EasyBooks analytics.</ErrorState>
        ) : (
          <StatRow>
            <Stat label="Sales" value={money(overview.data?.sales.total)} />
            <Stat label="Purchases" value={money(overview.data?.purchases.total)} />
            <Stat
              label="Receivables outstanding"
              value={receivables.error ? "—" : money(receivables.data?.total_outstanding ?? null)}
            />
            <Stat label="Sales − purchases" value={money(overview.data?.sales_minus_purchases)} />
          </StatRow>
        )}
      </Section>

      <div className="tabs" role="tablist" aria-label="Finance data">
        {(["sales", "purchases", "receivables"] as Tab[]).map((value) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            className={tab === value ? "tab-item active" : "tab-item"}
            type="button"
            onClick={() => setTab(value)}
          >
            {value === "sales" ? "Sales" : value === "purchases" ? "Purchases" : "Receivables"}
          </button>
        ))}
      </div>

      {tab === "sales" && (
        <Section>
          {sales.loading ? (
            <Skeleton />
          ) : sales.error ? (
            <ErrorState>Could not load EasyBooks sales data.</ErrorState>
          ) : sales.data && sales.data.document_count === 0 ? (
            <EmptyState>No sales records for this period.</EmptyState>
          ) : (
            <>
              <StatRow>
                <Stat label="Documents" value={number(sales.data?.document_count)} />
                <Stat label="Customers" value={number(sales.data?.customer_count)} />
                <Stat label="Total" value={money(sales.data?.total)} />
                <Stat label="VAT" value={money(sales.data?.vat_amount)} />
              </StatRow>
              {sales.data && sales.data.undated_document_count > 0 && (
                <p className="section-note">
                  {sales.data.undated_document_count} document(s) have no date in EasyBooks and are
                  excluded from the monthly breakdown and any date filter.
                </p>
              )}
              {sales.data && monthTable(sales.data.by_month)}
            </>
          )}
        </Section>
      )}

      {tab === "purchases" && (
        <Section>
          {purchases.loading ? (
            <Skeleton />
          ) : purchases.error ? (
            <ErrorState>Could not load EasyBooks purchase data.</ErrorState>
          ) : purchases.data && purchases.data.document_count === 0 ? (
            <EmptyState>No purchase records for this period.</EmptyState>
          ) : (
            <>
              <StatRow>
                <Stat label="Documents" value={number(purchases.data?.document_count)} />
                <Stat label="Suppliers" value={number(purchases.data?.supplier_count)} />
                <Stat label="Total" value={money(purchases.data?.total)} />
                <Stat label="VAT" value={money(purchases.data?.vat_amount)} />
              </StatRow>
              {purchases.data && purchases.data.undated_document_count > 0 && (
                <p className="section-note">
                  {purchases.data.undated_document_count} document(s) have no date in EasyBooks and are
                  excluded from the monthly breakdown and any date filter.
                </p>
              )}
              {purchases.data && monthTable(purchases.data.by_month)}
            </>
          )}
        </Section>
      )}

      {tab === "receivables" && (
        <Section>
          {receivables.loading ? (
            <Skeleton />
          ) : receivables.error ? (
            <ErrorState>Could not load EasyBooks receivables data.</ErrorState>
          ) : receivables.data && receivables.data.invoice_count === 0 ? (
            <EmptyState>No invoices for this period.</EmptyState>
          ) : (
            <>
              <StatRow>
                <Stat label="Invoiced" value={money(receivables.data?.total_invoiced)} />
                <Stat label="Invoices" value={number(receivables.data?.invoice_count)} />
                <Stat label="Linked to an order" value={number(receivables.data?.linked_invoice_count)} />
                <Stat label="Unlinked" value={number(receivables.data?.unlinked_invoice_count)} />
              </StatRow>
              {receivables.data && receivables.data.total_outstanding === null && (
                <p className="section-note">
                  Outstanding balance: {receivables.data.outstanding_status}.
                </p>
              )}
              {receivables.data && (
                <DataTable
                  columns={[
                    { key: "customer", header: "Customer", render: (row: CustomerReceivable) => row.customer_name ?? row.customer_code },
                    { key: "invoices", header: "Invoices", align: "right", render: (row: CustomerReceivable) => number(row.invoice_count) },
                    { key: "invoiced", header: "Invoiced", align: "right", render: (row: CustomerReceivable) => money(row.total_invoiced) },
                    { key: "oldest", header: "Oldest invoice", render: (row: CustomerReceivable) => isoDate(row.oldest_invoice_date) },
                    {
                      key: "outstanding",
                      header: "Outstanding",
                      align: "right",
                      render: (row: CustomerReceivable) =>
                        row.outstanding_amount === null ? "Unavailable" : money(row.outstanding_amount),
                    },
                  ]}
                  rows={receivables.data.customers}
                  rowKey={(row) => row.customer_code}
                  onRowClick={(row) => row.customer_id && setDrilldownId(row.customer_id)}
                  rowLabel={(row) => `Invoices for ${row.customer_name ?? row.customer_code}`}
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

  const load = useCallback(async () => {
    try {
      setDetail(await api.customerReceivable(customerId));
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(reason instanceof Error ? reason.message : "Could not load this customer's invoices");
    }
  }, [customerId, onSessionLost]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="accounting-overlay" role="dialog" aria-label={detail ? `Invoices for ${detail.customer_name}` : "Invoices"}>
      <div className="accounting-panel">
        <header>
          <div>
            <h2>{detail?.customer_name ?? "Loading…"}</h2>
          </div>
          <button className="secondary-button" type="button" onClick={onClose}>
            Close
          </button>
        </header>
        {error && <ErrorState>{error}</ErrorState>}
        {!detail ? (
          <p className="loading-state">Loading invoices…</p>
        ) : (
          <>
            <dl className="accounting-facts">
              <div>
                <dt>Invoices</dt>
                <dd>{number(detail.invoice_count)}</dd>
              </div>
              <div>
                <dt>Total invoiced</dt>
                <dd>{money(detail.total_invoiced)}</dd>
              </div>
              <div>
                <dt>Outstanding</dt>
                <dd>{detail.total_outstanding === null ? "—" : money(detail.total_outstanding)}</dd>
              </div>
            </dl>
            {detail.total_outstanding === null && (
              <p className="accounting-note">{detail.outstanding_status}.</p>
            )}
            {detail.invoices.length === 0 ? (
              <EmptyState>No invoices for this customer.</EmptyState>
            ) : (
              <DataTable
                columns={[
                  { key: "invoice", header: "Invoice", render: (row) => row.invoice_number ?? row.sales_document_id },
                  { key: "date", header: "Date", render: (row) => isoDate(row.document_date) },
                  { key: "amount", header: "Amount", align: "right", render: (row) => money(row.total_amount) },
                  {
                    key: "outstanding",
                    header: "Outstanding",
                    align: "right",
                    render: (row) => (row.outstanding_amount === null ? "Unavailable" : money(row.outstanding_amount)),
                  },
                  { key: "order", header: "Linked order", render: (row) => row.linked_order_numbers.join(", ") || "—" },
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
