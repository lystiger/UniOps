import { api } from "../api";
import { duration, latestSyncRuns, number, syncStatusTone, timestamp } from "../format";
import { useApiResource } from "../hooks";
import { useLocale, useT } from "../i18n";
import { DataTable, EmptyState, ErrorState, PageHeader, Section, Skeleton, Status } from "./primitives";
import type { SyncRun } from "../types";

export function DataView({ onSessionLost }: { onSessionLost: () => void }) {
  const sync = useApiResource(() => api.syncRuns(20), [], onSessionLost);
  const runs = sync.data ?? [];
  const { lastSuccess, lastAttempt } = latestSyncRuns(runs);
  const { locale } = useLocale();
  const t = useT();

  return (
    <div className="data-page">
      <PageHeader title={t.data.title} context={t.data.context} />

      <Section>
        {sync.loading ? (
          <Skeleton rows={1} />
        ) : sync.error ? (
          <ErrorState>{t.data.errors.loadHistory}</ErrorState>
        ) : runs.length === 0 ? (
          <EmptyState>{t.data.empty}</EmptyState>
        ) : (
          <dl className="accounting-facts">
            <div>
              <dt>{t.data.facts.lastSuccess}</dt>
              <dd>{lastSuccess ? timestamp(lastSuccess.started_at) : "—"}</dd>
            </div>
            <div>
              <dt>{t.data.facts.lastAttempt}</dt>
              <dd>{lastAttempt ? timestamp(lastAttempt.started_at) : "—"}</dd>
            </div>
            <div>
              <dt>{t.data.facts.status}</dt>
              <dd>
                {lastAttempt ? (
                  <Status label={t.sync.status[lastAttempt.status]} tone={syncStatusTone[lastAttempt.status]} />
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt>{t.data.facts.rowsProcessed}</dt>
              <dd>{lastAttempt ? number(lastAttempt.documents_seen) : "—"}</dd>
            </div>
          </dl>
        )}
      </Section>

      <Section title={t.data.recentRuns}>
        {sync.loading ? (
          <Skeleton />
        ) : sync.error ? (
          <ErrorState>{t.data.errors.loadHistory}</ErrorState>
        ) : runs.length === 0 ? (
          <EmptyState>{t.data.noRunsYet}</EmptyState>
        ) : (
          <DataTable
            columns={[
              { key: "time", header: t.data.columns.time, render: (row: SyncRun) => timestamp(row.started_at) },
              { key: "mode", header: t.data.columns.mode, render: (row: SyncRun) => row.mode },
              {
                key: "status",
                header: t.data.columns.status,
                render: (row: SyncRun) => <Status label={t.sync.status[row.status]} tone={syncStatusTone[row.status]} />,
              },
              { key: "rows", header: t.data.columns.rows, align: "right", render: (row: SyncRun) => number(row.documents_seen) },
              {
                key: "warnings",
                header: t.data.columns.warnings,
                align: "right",
                render: (row: SyncRun) => (row.reconciliation_warnings > 0 ? `${number(row.reconciliation_warnings)}` : "0"),
              },
              {
                key: "duration",
                header: t.data.columns.durationDetails,
                render: (row: SyncRun) =>
                  row.error_summary
                    ? `${duration(row.started_at, row.finished_at, locale)} (${row.error_summary})`
                    : duration(row.started_at, row.finished_at, locale),
              },
            ]}
            rows={runs}
            rowKey={(row) => row.id}
          />
        )}
      </Section>
    </div>
  );
}
