export type PipelinePhaseStatus = "complete" | "running" | "waiting" | "failed";

export interface PipelineStage {
  name: string;
  subhead?: string;
  status: PipelinePhaseStatus;
  detail?: string;
}

export interface PipelineVisualProps {
  title?: string;
  systemName?: string;
  stages?: PipelineStage[];
  lastSync?: string;
  freshnessStatus?: "fresh" | "stale" | "syncing" | "error";
  metrics?: { label: string; value: string | number }[];
  errorMessage?: string | null;
}

const defaultStages: PipelineStage[] = [
  { name: "Extract", subhead: "EasyBooks MSSQL", status: "complete" },
  { name: "Transform", subhead: "Schema & validation", status: "complete" },
  { name: "Load", subhead: "UniOps operational DB", status: "complete" },
];

export function PipelineVisual({
  title = "Pipeline synchronization",
  systemName = "EasyBooks",
  stages = defaultStages,
  lastSync = "09 Sep 2026 · 15:44",
  freshnessStatus = "fresh",
  metrics,
  errorMessage,
}: PipelineVisualProps) {
  const symbolFor = (status: PipelinePhaseStatus) => {
    switch (status) {
      case "complete":
        return "✓";
      case "running":
        return "●";
      case "failed":
        return "×";
      default:
        return "○";
    }
  };

  return (
    <div className="pipeline-card">
      <div className="pipeline-header">
        <div>
          <span className="pipeline-system">{systemName}</span>
          <h3 className="pipeline-title">{title}</h3>
        </div>
        <div className={`pipeline-freshness freshness-${freshnessStatus}`}>
          <span className="freshness-dot" aria-hidden="true" />
          <span className="freshness-label">
            {freshnessStatus === "fresh" && "Live & verified"}
            {freshnessStatus === "syncing" && "Syncing…"}
            {freshnessStatus === "stale" && "Update required"}
            {freshnessStatus === "error" && "Sync failed"}
          </span>
        </div>
      </div>

      <div className="pipeline-flow" aria-label="ETL Pipeline Stages">
        {stages.map((stage, index) => {
          const isLast = index === stages.length - 1;
          return (
            <div
              key={stage.name}
              className={`pipeline-step step-${stage.status}`}
            >
              <div className="step-label-group">
                <span className="step-name">{stage.name}</span>
                {stage.subhead && <span className="step-subhead">{stage.subhead}</span>}
              </div>
              <div className="step-indicator-row">
                <span className="step-node" title={`${stage.name}: ${stage.status}`}>
                  {symbolFor(stage.status)}
                </span>
                {!isLast && <div className="step-connector" aria-hidden="true" />}
              </div>
              {stage.detail && <span className="step-detail">{stage.detail}</span>}
            </div>
          );
        })}
      </div>

      {errorMessage && (
        <div className="message error pipeline-error" role="alert">
          {errorMessage}
        </div>
      )}

      <div className="pipeline-footer">
        <div className="pipeline-sync-meta">
          <span className="sync-label">Last sync</span>
          <strong className="sync-timestamp">{lastSync}</strong>
        </div>
        {metrics && metrics.length > 0 && (
          <div className="pipeline-metrics">
            {metrics.map((m) => (
              <div className="pipeline-metric-item" key={m.label}>
                <span className="metric-label">{m.label}</span>
                <strong className="metric-value">{m.value}</strong>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
