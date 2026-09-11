import type { ReactNode } from "react";
import { latestSyncRuns, syncStatusTone, timestamp } from "../format";
import type { SyncRun } from "../types";

/**
 * Small reusable primitives shared by every data page.
 *
 * Deliberately few: a page is built from these, not from a bespoke card for
 * every metric. See CLAUDE / design notes — no MetricCard, no FinanceCard.
 */

// --- PageHeader -------------------------------------------------------------

export function PageHeader({
  title,
  context,
  actions,
}: {
  title: string;
  /** Date, filter state, or other short operational context. Not a subtitle. */
  context?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {context && <p className="page-context">{context}</p>}
      </div>
      {actions && <div className="board-actions">{actions}</div>}
    </div>
  );
}

// --- Section ------------------------------------------------------------

export function Section({
  title,
  action,
  children,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section">
      {(title || action) && (
        <div className="section-head">
          {title && <h2>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

// --- Stat / StatRow -------------------------------------------------------

export function StatRow({ children }: { children: ReactNode }) {
  return <div className="stat-row">{children}</div>;
}

export function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: ReactNode;
  tone?: "producing" | "ready" | "overdue" | "warning";
}) {
  return (
    <div className="stat">
      <span className="stat-value" data-tone={tone}>
        {value}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

// --- DataTable --------------------------------------------------------------

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  isRowClickable,
  rowLabel,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  isRowClickable?: (row: T) => boolean;
  rowLabel?: (row: T) => string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} style={column.align === "right" ? { textAlign: "right" } : undefined}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const clickable = Boolean(onRowClick && (!isRowClickable || isRowClickable(row)));
            return (
              <tr
                key={rowKey(row)}
                className={clickable ? "clickable" : undefined}
                onClick={clickable ? () => onRowClick?.(row) : undefined}
                role={clickable ? "button" : undefined}
                tabIndex={clickable ? 0 : undefined}
                aria-label={clickable && rowLabel ? rowLabel(row) : undefined}
                onKeyDown={
                  clickable
                    ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onRowClick?.(row);
                        }
                      }
                    : undefined
                }
              >
                {columns.map((column) => (
                  <td key={column.key} style={column.align === "right" ? { textAlign: "right" } : undefined}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// --- FilterBar / date range --------------------------------------------------

export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="filter-bar">{children}</div>;
}

export { DateRangeFilter, type DateRangeFilterProps } from "./DateRangeFilter";

// --- Status -----------------------------------------------------------------

export type StatusTone = "neutral" | "pending" | "success" | "rejected";

/** A short status word led by a colored dot, never color-only: the label always
 * reads on its own, which is what a screen reader or a grayscale print gets. */
export function Status({ label, tone }: { label: string; tone: StatusTone }) {
  return (
    <span className="status-indicator" data-tone={tone}>
      <span className="status-dot" data-tone={tone} aria-hidden="true" />
      {label}
    </span>
  );
}

// --- EmptyState ---------------------------------------------------------

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="empty-state">{children}</p>;
}

/** A data section's load state: distinguishes loading, error, and unavailable
 * from a genuinely empty result, per the app's error-state contract. */
export function ErrorState({ children }: { children: ReactNode }) {
  return (
    <div className="message error" role="alert">
      {children}
    </div>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div className="skeleton-row" key={index} />
      ))}
    </div>
  );
}

// --- SyncStatus ---------------------------------------------------------

import { useT } from "../i18n";

/** Compact "last sync" line used on Overview and Finance. The Data page shows
 * the fuller picture; this is the one fact everywhere else needs. */
export function SyncStatus({ runs, loading }: { runs: SyncRun[] | null; loading: boolean }) {
  const t = useT();
  if (loading) {
    return <span className="sync-status">{t.sync.checking}</span>;
  }
  if (!runs || runs.length === 0) {
    return <span className="sync-status">{t.sync.noSyncRunYet}</span>;
  }
  const { lastSuccess, lastAttempt } = latestSyncRuns(runs);
  if (!lastSuccess) {
    return (
      <span className="sync-status">
        {t.sync.lastSyncAttempt(timestamp(lastAttempt?.started_at))} —{" "}
        <Status label={t.sync.status[lastAttempt!.status]} tone={syncStatusTone[lastAttempt!.status]} />
      </span>
    );
  }
  return (
    <span className="sync-status">
      {t.sync.lastSync(timestamp(lastSuccess.started_at))}{" "}
      <Status label={t.sync.status[lastSuccess.status]} tone={syncStatusTone[lastSuccess.status]} />
    </span>
  );
}
