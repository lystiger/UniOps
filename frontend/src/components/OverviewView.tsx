import { useEffect, useState } from "react";
import { api, UnauthorizedError } from "../api";
import type { Order } from "../types";
import { PipelineVisual } from "./PipelineVisual";

export function OverviewView({
  onNavigateOrders,
  onNewOrder,
  canWrite,
  onSessionLost,
}: {
  onNavigateOrders: () => void;
  onNewOrder: () => void;
  canWrite: boolean;
  onSessionLost: () => void;
}) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .orders("")
      .then((res) => setOrders(res.items.filter((o) => o.status !== "CANCELLED")))
      .catch((err) => {
        if (err instanceof UnauthorizedError) onSessionLost();
      })
      .finally(() => setLoading(false));
  }, [onSessionLost]);

  const producingCount = orders.filter((o) => o.status === "IN_PRODUCTION").length;
  const readyCount = orders.filter((o) => o.status === "READY").length;
  const waitingCount = orders.filter((o) => ["DRAFT", "CONFIRMED", "SCHEDULED"].includes(o.status)).length;
  const deliveryCount = orders.filter((o) => ["DELIVERY_PENDING", "DELIVERED"].includes(o.status)).length;

  return (
    <div className="overview-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">01 / OPERATIONS · Executive snapshot</p>
          <h1>Production overview</h1>
          <p className="heading-sub">Tổng quan sản xuất &amp; điều hành nhà máy Hưng Yên</p>
          <p className="heading-meta">UniGreen Internal Operating System · Shift 07:00–18:00</p>
        </div>
        <div className="board-actions">
          <button className="secondary-button" type="button" onClick={onNavigateOrders}>
            View order board →
          </button>
          {canWrite && (
            <button className="primary-button" type="button" onClick={onNewOrder}>
              + New order
            </button>
          )}
        </div>
      </div>

      <div className="overview-kpi-grid">
        <div className="kpi-card">
          <span className="kpi-eyebrow">ACTIVE ORDERS</span>
          <strong className="kpi-value">{loading ? "—" : orders.length}</strong>
          <span className="kpi-caption">Total unclosed in pipeline</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-eyebrow">PRODUCING NOW</span>
          <strong className="kpi-value highlight-producing">{loading ? "—" : producingCount}</strong>
          <span className="kpi-caption">Active on conversion line</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-eyebrow">READY FOR DISPATCH</span>
          <strong className="kpi-value highlight-ready">{loading ? "—" : readyCount}</strong>
          <span className="kpi-caption">Awaiting logistics pickup</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-eyebrow">FACILITY STATUS</span>
          <div className="kpi-status-row">
            <span className="live-dot" aria-hidden="true" />
            <strong className="kpi-status-text">Hưng Yên · LIVE</strong>
          </div>
          <span className="kpi-caption">Converting &amp; slitting active</span>
        </div>
      </div>

      <div className="overview-sections-grid">
        <div className="overview-pipeline-section">
          <p className="eyebrow">DATA FRESHNESS &amp; INTEGRATION</p>
          <PipelineVisual
            systemName="EasyBooks"
            title="Accounting extraction pipeline"
            lastSync="Today · Synced on demand"
            freshnessStatus="fresh"
            metrics={[
              { label: "Active Orders", value: orders.length },
              { label: "Waiting", value: waitingCount },
              { label: "In Production", value: producingCount },
              { label: "Ready", value: readyCount },
              { label: "In Dispatch", value: deliveryCount },
            ]}
          />
        </div>

        <div className="overview-facility-card">
          <p className="eyebrow">01 / PRODUCTION SITE</p>
          <h3>Hưng Yên Conversion Plant</h3>
          <p className="facility-desc">
            Parent jumbo roll conversion facility. Converting parent rolls to finished napkins,
            toilet tissue, and coreless rolls according to custom customer specifications.
          </p>
          <dl className="spec-table">
            <div>
              <dt>Primary line</dt>
              <dd>High-speed rewinder &amp; slitter</dd>
            </div>
            <div>
              <dt>Paper grammage</dt>
              <dd>13–18 gsm virgin &amp; recycled tissue</dd>
            </div>
            <div>
              <dt>Operating window</dt>
              <dd>07:00 – 18:00 Mon–Sat</dd>
            </div>
            <div>
              <dt>Direct integration</dt>
              <dd>EasyBooks accounting sync</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
