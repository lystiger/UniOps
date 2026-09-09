import { PipelineVisual } from "./PipelineVisual";

export function FinanceView({
  onNavigateOrders,
}: {
  onNavigateOrders: () => void;
}) {
  return (
    <div className="finance-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">04 / FINANCE · EasyBooks ledger</p>
          <h1>Financial ledger &amp; reconciliation</h1>
          <p className="heading-sub">Dữ liệu kế toán &amp; đối soát hóa đơn EasyBooks</p>
          <p className="heading-meta">System of Record: EasyBooks MSSQL · Read-only link from UniOps</p>
        </div>
        <div className="board-actions">
          <button className="secondary-button" type="button" onClick={onNavigateOrders}>
            Reconcile on orders board →
          </button>
        </div>
      </div>

      <div className="finance-policy-notice">
        <div className="policy-rule" />
        <div>
          <strong>Accounting System of Record principle:</strong>
          <p>
            EasyBooks remains the sole financial authority. UniOps maintains read-only links
            between sales documents and factory production orders. UniOps never mutates or creates
            entries in EasyBooks directly.
          </p>
        </div>
      </div>

      <div className="overview-sections-grid">
        <div className="finance-pipeline-card">
          <p className="eyebrow">04 / LEDGER PIPELINE</p>
          <PipelineVisual
            systemName="EasyBooks"
            title="Sales invoices &amp; receipt extraction"
            lastSync="Today · Read-only sync"
            freshnessStatus="fresh"
            metrics={[
              { label: "Sync Mode", value: "Incremental" },
              { label: "Protocol", value: "MSSQL Read" },
              { label: "Ledger State", value: "Reconciled" },
            ]}
          />
        </div>

        <div className="finance-guide-card">
          <p className="eyebrow">RECONCILIATION PROTOCOL</p>
          <h3>Invoice Candidate Matching</h3>
          <ul className="guide-steps">
            <li>
              <span className="step-num">01</span>
              <div>
                <strong>Order fulfillment completion</strong>
                <p>Orders reaching DELIVERED status qualify for invoice candidate matching.</p>
              </div>
            </li>
            <li>
              <span className="step-num">02</span>
              <div>
                <strong>Candidate discovery</strong>
                <p>UniOps scans EasyBooks sales documents matching customer code and monetary total.</p>
              </div>
            </li>
            <li>
              <span className="step-num">03</span>
              <div>
                <strong>Manual operator confirmation</strong>
                <p>When multiple candidates exist, UniOps never guesses. The operator confirms the match.</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
