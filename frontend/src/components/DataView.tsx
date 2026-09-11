import type { ReactNode } from "react";
import { api } from "../api";
import { duration, isoDate, latestSyncRuns, number, relativeTime, syncStatusTone, timestamp } from "../format";
import { useApiResource } from "../hooks";
import { useLocale, useT } from "../i18n";
import type { Dictionary } from "../i18n/types";
import { DataTable, EmptyState, ErrorState, PageHeader, Section, Skeleton, Stat, StatRow, Status } from "./primitives";
import type { SyncRun } from "../types";

function modeLabel(mode: string, t: Dictionary): string {
  switch (mode.toLowerCase()) {
    case "fixture":
      return t.data.modes.fixture;
    case "live":
      return t.data.modes.live;
    case "live-headers":
      return t.data.modes.liveHeaders;
    default:
      return mode;
  }
}

function period(run: SyncRun): string {
  if (!run.from_date && !run.to_date) return "—";
  return `${isoDate(run.from_date)} – ${isoDate(run.to_date)}`;
}

/** A table count where zero recedes, so the figures that matter are what the eye lands on. */
function count(value: number, emphasis?: "alert" | "warn"): ReactNode {
  if (value === 0) return <span className="num-zero">0</span>;
  if (emphasis && value > 0) return <span className={`num-${emphasis}`}>{number(value)}</span>;
  return number(value);
}

export function DataView({ onSessionLost }: { onSessionLost: () => void }) {
  const sync = useApiResource(() => api.syncRuns(20), [], onSessionLost);
  const runs = sync.data ?? [];
  const { lastSuccess, lastAttempt } = latestSyncRuns(runs);
  const { locale } = useLocale();
  const t = useT();

  const when = (run: SyncRun) => (
    <>
      {timestamp(run.started_at)} <span className="sync-health-ago">({relativeTime(run.started_at, locale).toLocaleLowerCase(locale)})</span>
    </>
  );

  return (
    <div className="data-page">
      <PageHeader title={t.data.title} context={t.data.context} />

      <Section>
        {sync.loading ? (
          <Skeleton rows={2} />
        ) : sync.error ? (
          <ErrorState>{t.data.errors.loadHistory}</ErrorState>
        ) : !lastAttempt ? (
          <EmptyState>{t.data.empty}</EmptyState>
        ) : (
          <>
            <div className="sync-health">
              <p className="sync-health-title">
                <span className="status-dot" data-tone={syncStatusTone[lastAttempt.status]} aria-hidden="true" />
                {t.data.health[lastAttempt.status]}
              </p>
              <dl className="sync-health-facts">
                <div>
                  <dt>{t.data.facts.lastSuccess}</dt>
                  <dd>{lastSuccess ? when(lastSuccess) : t.data.facts.neverSucceeded}</dd>
                </div>
                {lastAttempt !== lastSuccess && (
                  <div>
                    <dt>{t.data.facts.lastAttempt}</dt>
                    <dd>{when(lastAttempt)}</dd>
                  </div>
                )}
                <div>
                  <dt>{t.data.columns.mode}</dt>
                  <dd>
                    {modeLabel(lastAttempt.mode, t)}
                    {lastAttempt.finished_at && (
                      <span className="sync-health-ago">
                        {" "}
                        · {duration(lastAttempt.started_at, lastAttempt.finished_at, locale)}
                      </span>
                    )}
                  </dd>
                </div>
              </dl>
              {lastAttempt.error_summary && <p className="sync-health-error">{lastAttempt.error_summary}</p>}
            </div>

            <StatRow>
              <Stat label={t.data.counts.seen} value={number(lastAttempt.documents_seen)} />
              <Stat label={t.data.counts.created} value={number(lastAttempt.documents_created)} />
              <Stat label={t.data.counts.updated} value={number(lastAttempt.documents_updated)} />
              <Stat label={t.data.counts.unchanged} value={number(lastAttempt.documents_unchanged)} />
              <Stat
                label={t.data.counts.failed}
                value={number(lastAttempt.documents_failed)}
                tone={lastAttempt.documents_failed > 0 ? "overdue" : undefined}
              />
              <Stat
                label={t.data.counts.warnings}
                value={number(lastAttempt.reconciliation_warnings)}
                tone={lastAttempt.reconciliation_warnings > 0 ? "warning" : undefined}
              />
            </StatRow>
          </>
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
              { key: "started", header: t.data.columns.started, render: (row: SyncRun) => timestamp(row.started_at) },
              { key: "mode", header: t.data.columns.mode, render: (row: SyncRun) => modeLabel(row.mode, t) },
              { key: "period", header: t.data.columns.period, render: period },
              {
                key: "status",
                header: t.data.columns.status,
                render: (row: SyncRun) => (
                  <>
                    <Status label={t.sync.status[row.status]} tone={syncStatusTone[row.status]} />
                    {row.error_summary && <div className="sync-run-error">{row.error_summary}</div>}
                  </>
                ),
              },
              {
                key: "documents",
                header: t.data.columns.documents,
                align: "right",
                render: (row: SyncRun) => count(row.documents_seen),
              },
              {
                key: "created",
                header: t.data.columns.created,
                align: "right",
                render: (row: SyncRun) => count(row.documents_created),
              },
              {
                key: "updated",
                header: t.data.columns.updated,
                align: "right",
                render: (row: SyncRun) => count(row.documents_updated),
              },
              {
                key: "failed",
                header: t.data.columns.failed,
                align: "right",
                render: (row: SyncRun) => count(row.documents_failed, "alert"),
              },
              {
                key: "warnings",
                header: t.data.columns.warnings,
                align: "right",
                render: (row: SyncRun) => count(row.reconciliation_warnings, "warn"),
              },
              {
                key: "duration",
                header: t.data.columns.duration,
                align: "right",
                render: (row: SyncRun) => duration(row.started_at, row.finished_at, locale),
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
