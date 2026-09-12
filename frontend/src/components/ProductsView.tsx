import { useState, useTransition, type FormEvent } from "react";
import { api } from "../api";
import { useApiResource } from "../hooks";
import { useT } from "../i18n";
import type { Product } from "../types";
import { DataTable, EmptyState, ErrorState, PageHeader, Section, Skeleton, type Column } from "./primitives";

export function ProductsView({
  canWrite,
  onSessionLost,
}: {
  canWrite: boolean;
  onSessionLost: () => void;
}) {
  const t = useT();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isPending, startTransition] = useTransition();

  const productsResource = useApiResource(
    () =>
      api.products({
        search: search.trim() || undefined,
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      }),
    [search, categoryFilter, statusFilter, refreshKey],
    onSessionLost
  );

  const products = productsResource.data ?? [];

  const handleCreateProduct = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setModalError(null);
    const form = event.currentTarget;
    const data = new FormData(form);

    const name = String(data.get("name") ?? "").trim();
    const unit = String(data.get("unit") ?? "").trim();
    const sku = String(data.get("sku") ?? "").trim() || undefined;
    const category = String(data.get("category") ?? "").trim() || "general";
    const easybooksCode = String(data.get("easybooks_code") ?? "").trim() || undefined;
    const specsRaw = String(data.get("specifications") ?? "").trim();

    let specifications: Record<string, unknown> = {};
    if (specsRaw) {
      try {
        specifications = JSON.parse(specsRaw);
      } catch {
        setModalError("Specifications must be valid JSON object");
        return;
      }
    }

    startTransition(async () => {
      try {
        await api.createProduct({
          name,
          unit,
          sku,
          category,
          easybooks_code: easybooksCode,
          specifications,
        });
        setIsModalOpen(false);
        setRefreshKey((k) => k + 1);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setModalError(err.message);
        } else {
          setModalError(t.common.empty);
        }
      }
    });
  };

  const columns: Column<Product>[] = [
    {
      key: "sku",
      header: t.productsView.columns.sku,
      render: (p) => <strong className="font-mono text-brand-green">{p.sku}</strong>,
    },
    {
      key: "name",
      header: t.productsView.columns.name,
      render: (p) => (
        <div>
          <div className="font-medium">{p.name}</div>
          {p.easybooks_material_goods_id && (
            <div className="text-xs text-ink-muted">EB ID: {p.easybooks_material_goods_id.slice(0, 8)}…</div>
          )}
        </div>
      ),
    },
    {
      key: "category",
      header: t.productsView.columns.category,
      render: (p) => <span className="tag">{p.category}</span>,
    },
    {
      key: "unit",
      header: t.productsView.columns.unit,
      render: (p) => p.unit,
    },
    {
      key: "status",
      header: t.productsView.columns.status,
      render: (p) => (
        <span className={`status-badge status-${p.status}`}>
          {p.status === "active" ? t.productsView.active : t.productsView.discontinued}
        </span>
      ),
    },
    {
      key: "easybooks_code",
      header: t.productsView.columns.easybooksCode,
      render: (p) => (p.easybooks_code || p.code ? <code className="text-sm">{p.easybooks_code || p.code}</code> : "—"),
    },
    {
      key: "specifications",
      header: t.productsView.columns.specifications,
      render: (p) => {
        const specs = p.specifications || {};
        const keys = Object.keys(specs);
        if (keys.length === 0) return "—";
        return (
          <span className="text-xs text-ink-muted">
            {keys.map((k) => `${k}: ${String(specs[k])}`).join(" · ")}
          </span>
        );
      },
    },
  ];

  return (
    <div className="products-page">
      <PageHeader
        title={t.productsView.title}
        context={t.productsView.context}
        actions={
          canWrite ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                setModalError(null);
                setIsModalOpen(true);
              }}
            >
              {t.productsView.newProduct}
            </button>
          ) : undefined
        }
      />

      <Section>
        <div className="filter-bar" style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <input
            type="search"
            placeholder={t.productsView.searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input"
            style={{ minWidth: "260px" }}
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="input"
          >
            <option value="">{t.productsView.allCategories}</option>
            <option value="general">General</option>
            <option value="tissue">Tissue</option>
            <option value="industrial-roll">Industrial Roll</option>
            <option value="hand-towel">Hand Towel</option>
            <option value="napkin">Napkin</option>
            <option value="jumbo">Jumbo Roll</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input"
          >
            <option value="">{t.productsView.allStatuses}</option>
            <option value="active">{t.productsView.active}</option>
            <option value="discontinued">{t.productsView.discontinued}</option>
          </select>
        </div>

        {productsResource.loading ? (
          <Skeleton rows={5} />
        ) : productsResource.error ? (
          <ErrorState>{t.productsView.empty}</ErrorState>
        ) : products.length === 0 ? (
          <EmptyState>{t.productsView.empty}</EmptyState>
        ) : (
          <DataTable columns={columns} rows={products} rowKey={(p) => p.id} />
        )}
      </Section>

      {isModalOpen && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-card" style={{ maxWidth: "540px" }}>
            <h2>{t.productsView.createTitle}</h2>
            {modalError && <p className="form-error" role="alert">{modalError}</p>}
            <form onSubmit={handleCreateProduct}>
              <div className="form-field">
                <label htmlFor="prod-name">{t.productsView.fields.name} *</label>
                <input id="prod-name" name="name" required className="input" autoFocus />
              </div>

              <div className="form-row" style={{ display: "flex", gap: "1rem" }}>
                <div className="form-field" style={{ flex: 1 }}>
                  <label htmlFor="prod-unit">{t.productsView.fields.unit} *</label>
                  <input id="prod-unit" name="unit" required placeholder="Cuộn, Gói, Túi..." className="input" />
                </div>
                <div className="form-field" style={{ flex: 1 }}>
                  <label htmlFor="prod-category">{t.productsView.fields.category}</label>
                  <input id="prod-category" name="category" defaultValue="general" className="input" />
                </div>
              </div>

              <div className="form-row" style={{ display: "flex", gap: "1rem" }}>
                <div className="form-field" style={{ flex: 1 }}>
                  <label htmlFor="prod-sku">{t.productsView.fields.sku}</label>
                  <input id="prod-sku" name="sku" placeholder="Auto-generate UG000001" className="input" />
                  <span className="field-hint" style={{ fontSize: "0.75rem", color: "var(--ink-muted)" }}>
                    {t.productsView.fields.skuHint}
                  </span>
                </div>
                <div className="form-field" style={{ flex: 1 }}>
                  <label htmlFor="prod-eb-code">{t.productsView.fields.easybooksCode}</label>
                  <input id="prod-eb-code" name="easybooks_code" placeholder="TP.GVS..." className="input" />
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="prod-specs">{t.productsView.fields.specifications}</label>
                <textarea
                  id="prod-specs"
                  name="specifications"
                  placeholder='{"ply": 2, "weight_g": 700, "material": "virgin-pulp"}'
                  className="input"
                  rows={3}
                />
              </div>

              <div className="form-actions" style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isPending}
                >
                  {t.common.cancel}
                </button>
                <button type="submit" className="btn btn-primary" disabled={isPending}>
                  {isPending ? t.common.saving : t.common.save}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
