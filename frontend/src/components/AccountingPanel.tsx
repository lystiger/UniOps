import { useCallback, useEffect, useRef, useState } from "react";
import { api, formatApiError, UnauthorizedError } from "../api";
import { isoDate, money } from "../format";
import { useT } from "../i18n";
import type { AccountingStatus, InvoiceCandidate, Order, OrderAccounting } from "../types";

const statusToneMeta: Record<AccountingStatus, { symbol: string; tone: "draft" | "pending" | "accepted" }> = {
  NOT_INVOICED: { symbol: "●", tone: "draft" },
  INVOICE_CANDIDATE: { symbol: "●", tone: "pending" },
  INVOICED: { symbol: "✓", tone: "accepted" },
};

export function AccountingBadge({ status }: { status: AccountingStatus | null }) {
  const t = useT();
  if (!status) return null;
  const meta = statusToneMeta[status] ?? {
    symbol: "●",
    tone: "draft" as const,
  };
  const label = t.accounting.status[status] ?? status;
  return (
    <span
      className={`accounting-badge accounting-${status.toLowerCase()} accounting-tone-${meta.tone}`}
    >
      <span className="accounting-symbol" aria-hidden="true">
        {meta.symbol}
      </span>
      <span>{label}</span>
    </span>
  );
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
  const t = useT();

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
      setError(formatApiError(reason, t).message);
    }
  }, [order.id, onSessionLost, t]);

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
      setError(formatApiError(reason, t).message);
    } finally {
      setBusy("");
    }
  }

  // The dimmed full-screen backdrop reads as dismissible, and the settings menu
  // and date picker already close on Escape and outside click, so this does too.
  // Only a press that starts on the backdrop counts: a text selection dragged
  // out of the panel ends its click on the backdrop and must not close it.
  const pressStartedOnBackdrop = useRef(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="accounting-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={t.accounting.dialogAria(order.order_number)}
      onMouseDown={(event) => {
        pressStartedOnBackdrop.current = event.target === event.currentTarget;
      }}
      onClick={(event) => {
        if (pressStartedOnBackdrop.current && event.target === event.currentTarget) onClose();
      }}
    >
      <div className="accounting-panel">
        <header>
          <div>
            <h2>{order.order_number}</h2>
          </div>
          <button className="secondary-button" type="button" onClick={onClose}>
            {t.common.close}
          </button>
        </header>

        {error && <div className="message error" role="alert">{error}</div>}
        {!accounting ? (
          <p className="loading-state">{t.accounting.loading}</p>
        ) : (
          <>
            <dl className="accounting-facts">
              <div>
                <dt>{t.accounting.facts.production}</dt>
                <dd>{accounting.lifecycle_status}</dd>
              </div>
              <div>
                <dt>{t.accounting.facts.accounting}</dt>
                <dd>{t.accounting.status[accounting.accounting_status] ?? accounting.accounting_status}</dd>
              </div>
              <div>
                <dt>{t.accounting.facts.payment}</dt>
                <dd>{t.accounting.paymentStatus[accounting.payment_status] ?? accounting.payment_status}</dd>
              </div>
              <div>
                <dt>{t.accounting.facts.outstanding}</dt>
                <dd>{money(accounting.outstanding_amount)}</dd>
              </div>
            </dl>
            {accounting.outstanding_amount === null && (
              <p className="accounting-note">
                {accounting.outstanding_status?.startsWith("EasyBooks exposes no paid or outstanding amount")
                  ? t.accounting.outstandingExposesNote
                  : accounting.outstanding_status}.
              </p>
            )}

            <h3>{t.accounting.linkedInvoices}</h3>
            {accounting.invoices.length === 0 ? (
              <p className="empty-column">{t.accounting.noInvoiceLinked}</p>
            ) : (
              <ul className="invoice-list">
                {accounting.invoices.map((invoice) => (
                  <li key={invoice.link_id}>
                    <div>
                      <strong>{invoice.invoice_number ?? invoice.sales_document_id}</strong>
                      <small>
                        {invoice.document_date ? isoDate(invoice.document_date) : t.accounting.noDate} ·{" "}
                        {money(invoice.total_amount)} · {invoice.link_method}
                        {invoice.created_by ? ` · ${t.accounting.byUser(invoice.created_by)}` : ""}
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
                        {busy === invoice.link_id ? t.accounting.actions.removing : t.accounting.actions.unlink}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {candidates.length > 0 && (
              <>
                <h3>{t.accounting.possibleInvoices}</h3>
                <p className="accounting-note">
                  {candidates.length > 1
                    ? t.accounting.multipleCandidatesNote
                    : t.accounting.singleCandidateNote}
                </p>
                <ul className="invoice-list">
                  {candidates.map((candidate) => (
                    <li key={candidate.sales_document_id}>
                      <div>
                        <strong>{candidate.invoice_number ?? candidate.source_id}</strong>
                        <small>
                          {candidate.document_date ? isoDate(candidate.document_date) : t.accounting.noDate} ·{" "}
                          {money(candidate.total_amount)} · {t.accounting.confidence} {candidate.confidence}
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
                          {busy === candidate.sales_document_id ? t.accounting.actions.linking : t.accounting.actions.link}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="accounting-note">
              {t.accounting.linkNote}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
