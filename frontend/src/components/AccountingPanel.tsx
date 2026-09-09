import { useCallback, useEffect, useState } from "react";
import { api, UnauthorizedError } from "../api";
import type { AccountingStatus, InvoiceCandidate, Order, OrderAccounting } from "../types";

const accountingMeta: Record<
  AccountingStatus,
  { label: string; symbol: string; tone: "draft" | "pending" | "accepted" }
> = {
  NOT_INVOICED: { label: "Not invoiced", symbol: "●", tone: "draft" },
  INVOICE_CANDIDATE: { label: "Invoice candidate", symbol: "●", tone: "pending" },
  INVOICED: { label: "Invoiced", symbol: "✓", tone: "accepted" },
};

const accountingLabels: Record<AccountingStatus, string> = {
  NOT_INVOICED: "Not invoiced",
  INVOICE_CANDIDATE: "Invoice candidate",
  INVOICED: "Invoiced",
};

const paymentLabels: Record<string, string> = {
  UNKNOWN: "Unknown",
  UNPAID: "Unpaid",
  PARTIALLY_PAID: "Partially paid",
  PAID: "Paid",
};

export function AccountingBadge({ status }: { status: AccountingStatus | null }) {
  if (!status) return null;
  const meta = accountingMeta[status] ?? {
    label: status,
    symbol: "●",
    tone: "draft" as const,
  };
  return (
    <span
      className={`accounting-badge accounting-${status.toLowerCase()} accounting-tone-${meta.tone}`}
    >
      <span className="accounting-symbol" aria-hidden="true">
        {meta.symbol}
      </span>
      <span>{meta.label}</span>
    </span>
  );
}

function money(value: string | null) {
  if (value === null) return "—";
  return new Intl.NumberFormat("vi-VN").format(Number(value));
}

export function AccountingPanel({
  order,
  canWrite,
  onClose,
  onChanged,
  onSessionLost = () => undefined,
}: {
  order: Order;
  canWrite: boolean;
  onClose: () => void;
  onChanged: () => void;
  onSessionLost?: () => void;
}) {
  const [accounting, setAccounting] = useState<OrderAccounting | null>(null);
  const [candidates, setCandidates] = useState<InvoiceCandidate[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [state, options] = await Promise.all([
        api.orderAccounting(order.id),
        api.invoiceCandidates(order.id),
      ]);
      setAccounting(state);
      setCandidates(options);
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(reason instanceof Error ? reason.message : "Could not load accounting");
    }
  }, [order.id, onSessionLost]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(key: string, action: () => Promise<OrderAccounting>) {
    setBusy(key);
    setError("");
    try {
      await action();
      await load();
      onChanged();
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(reason instanceof Error ? reason.message : "That did not work");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="accounting-overlay" role="dialog" aria-label={`Accounting for ${order.order_number}`}>
      <div className="accounting-panel">
        <header>
          <div>
            <p className="eyebrow">04 / FINANCE · Order to cash</p>
            <h2>{order.order_number}</h2>
          </div>
          <button className="secondary-button" type="button" onClick={onClose}>
            Close
          </button>
        </header>

        {error && <div className="message error" role="alert">{error}</div>}
        {!accounting ? (
          <p className="loading-state">Loading accounting…</p>
        ) : (
          <>
            <dl className="accounting-facts">
              <div>
                <dt>Production</dt>
                <dd>{accounting.lifecycle_status}</dd>
              </div>
              <div>
                <dt>Accounting</dt>
                <dd>{accountingLabels[accounting.accounting_status]}</dd>
              </div>
              <div>
                <dt>Payment</dt>
                <dd>{paymentLabels[accounting.payment_status] ?? accounting.payment_status}</dd>
              </div>
              <div>
                <dt>Outstanding</dt>
                <dd>{money(accounting.outstanding_amount)}</dd>
              </div>
            </dl>
            {accounting.outstanding_amount === null && (
              <p className="accounting-note">{accounting.outstanding_status}.</p>
            )}

            <h3>Linked invoices</h3>
            {accounting.invoices.length === 0 ? (
              <p className="empty-column">No invoice linked to this order.</p>
            ) : (
              <ul className="invoice-list">
                {accounting.invoices.map((invoice) => (
                  <li key={invoice.link_id}>
                    <div>
                      <strong>{invoice.invoice_number ?? invoice.sales_document_id}</strong>
                      <small>
                        {invoice.document_date ?? "no date"} · {money(invoice.total_amount)} ·{" "}
                        {invoice.link_method}
                        {invoice.created_by ? ` · by ${invoice.created_by}` : ""}
                      </small>
                    </div>
                    {canWrite && (
                      <button
                        className="secondary-button"
                        disabled={busy === invoice.link_id}
                        onClick={() =>
                          act(invoice.link_id, () => api.unlinkInvoice(order.id, invoice.link_id))
                        }
                      >
                        {busy === invoice.link_id ? "Removing…" : "Unlink"}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {candidates.length > 0 && (
              <>
                <h3>Possible invoices</h3>
                <p className="accounting-note">
                  {candidates.length > 1
                    ? "More than one invoice fits. Choose the right one; UniOps will not guess."
                    : "Confirm only if this is the right invoice."}
                </p>
                <ul className="invoice-list">
                  {candidates.map((candidate) => (
                    <li key={candidate.sales_document_id}>
                      <div>
                        <strong>{candidate.invoice_number ?? candidate.source_id}</strong>
                        <small>
                          {candidate.document_date ?? "no date"} ·{" "}
                          {money(candidate.total_amount)} · confidence {candidate.confidence}
                        </small>
                      </div>
                      {canWrite && (
                        <button
                          className="primary-button"
                          disabled={busy === candidate.sales_document_id}
                          onClick={() =>
                            act(candidate.sales_document_id, () =>
                              api.linkInvoice(order.id, candidate.sales_document_id),
                            )
                          }
                        >
                          {busy === candidate.sales_document_id ? "Linking…" : "Link"}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="accounting-note">
              Linking records the match in UniOps only. EasyBooks is never changed.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
