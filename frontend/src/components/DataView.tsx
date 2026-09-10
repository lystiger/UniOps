import { api } from "../api";
import { duration, latestSyncRuns, number, syncStatusLabel, syncStatusTone, timestamp } from "../format";
import { useApiResource } from "../hooks";
import { DataTable, EmptyState, ErrorState, PageHeader, Section, Skeleton, Status } from "./primitives";
import type { SyncRun } from "../types";

export function DataView({ onSessionLost }: { onSessionLost: () => void }) {
  const sync = useApiResource(() => api.syncRuns(20), [], onSessionLost);
  const runs = sync.data ?? [];
  const { lastSuccess, lastAttempt } = latestSyncRuns(runs);

  return (
    <div className="data-page">
      <PageHeader title="Data" context="EasyBooks synchronization" />

      <Section>
        {sync.loading ? (
          <Skeleton rows={1} />
        ) : sync.error ? (
          <ErrorState>Could not load synchronization history.</ErrorState>
        ) : runs.length === 0 ? (
          <EmptyState>No EasyBooks synchronization has run yet.</EmptyState>
        ) : (
          <dl className="accounting-facts">
            <div>
              <dt>Last successful sync</dt>
              <dd>{lastSuccess ? timestamp(lastSuccess.started_at) : "—"}</dd>
            </div>
            <div>
              <dt>Last attempt</dt>
              <dd>{lastAttempt ? timestamp(lastAttempt.started_at) : "—"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                {lastAttempt ? (
                  <Status label={syncStatusLabel[lastAttempt.status]} tone={syncStatusTone[lastAttempt.status]} />
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt>Rows processed</dt>
              <dd>{lastAttempt ? number(lastAttempt.documents_seen) : "—"}</dd>
            </div>
          </dl>
        )}
      </Section>

      <Section title="Recent synchronization runs">
        {sync.loading ? (
          <Skeleton />
        ) : sync.error ? (
          <ErrorState>Could not load synchronization history.</ErrorState>
        ) : runs.length === 0 ? (
          <EmptyState>No synchronization runs recorded.</EmptyState>
        ) : (
          <DataTable
            columns={[
              { key: "time", header: "Time", render: (row: SyncRun) => timestamp(row.started_at) },
              { key: "mode", header: "Mode", render: (row: SyncRun) => row.mode },
              {
                key: "status",
                header: "Status",
                render: (row: SyncRun) => <Status label={syncStatusLabel[row.status]} tone={syncStatusTone[row.status]} />,
              },
              { key: "rows", header: "Rows", align: "right", render: (row: SyncRun) => number(row.documents_seen) },
              {
                key: "duration",
                header: "Duration / error",
                render: (row: SyncRun) =>
                  row.status === "FAILED" && row.error_summary
                    ? row.error_summary
                    : duration(row.started_at, row.finished_at),
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
