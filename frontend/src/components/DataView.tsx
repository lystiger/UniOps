import { PipelineVisual } from "./PipelineVisual";

export function DataView() {
  return (
    <div className="data-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">05 / DATA · Pipeline &amp; synchronization</p>
          <h1>Data &amp; synchronization pipelines</h1>
          <p className="heading-sub">Đồng bộ dữ liệu kế toán và luồng tích hợp nhà máy</p>
          <p className="heading-meta">UniGreen Operational Data Platform · Hưng Yên site</p>
        </div>
      </div>

      <div className="data-pipeline-container">
        <PipelineVisual
          systemName="EasyBooks"
          title="EasyBooks Enterprise Extraction Pipeline"
          stages={[
            { name: "Extract", subhead: "MSSQL Read replica", status: "complete", detail: "Invoices, customers, catalog" },
            { name: "Transform", subhead: "Schema & decimal validation", status: "complete", detail: "Currency & tax normalizer" },
            { name: "Load", subhead: "UniOps operational DB", status: "complete", detail: "Freshness verified" },
          ]}
          lastSync="09 Sep 2026 · 15:44"
          freshnessStatus="fresh"
          metrics={[
            { label: "Target", value: "UniOps Primary" },
            { label: "Reconciliation", value: "Strict 1:1" },
            { label: "Failures", value: "0" },
          ]}
        />

        <div className="pipeline-principles-card">
          <p className="eyebrow">INTEGRATION CONSTRAINTS</p>
          <h3>Operational Data Rules</h3>
          <div className="principles-grid">
            <div className="principle-item">
              <span className="principle-code">01</span>
              <div>
                <strong>UniOps is operational, not accounting</strong>
                <p>Orders, production scheduling, slitting, cutting, packaging belong in UniOps.</p>
              </div>
            </div>
            <div className="principle-item">
              <span className="principle-code">02</span>
              <div>
                <strong>EasyBooks is accounting SoR</strong>
                <p>Tax codes, ledger books, VAT invoices are maintained in EasyBooks exclusively.</p>
              </div>
            </div>
            <div className="principle-item">
              <span className="principle-code">03</span>
              <div>
                <strong>No blind auto-linking</strong>
                <p>If more than one invoice matches an order amount, human verification is required.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
