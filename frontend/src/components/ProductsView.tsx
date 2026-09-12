import { useState, type FormEvent } from "react";
import { api, formatApiError } from "../api";
import { useApiResource } from "../hooks";
import { useT } from "../i18n";
import type { Product, ProductStatus } from "../types";
import {
  DataTable,
  EmptyState,
  ErrorState,
  FilterBar,
  PageHeader,
  Section,
  Skeleton,
  Status,
  type Column,
} from "./primitives";

/** The canonical product list. UniOps owns every product's identity and SKU;
 * this page is where that identity is created and discontinued. */
export function ProductsView({
  canWrite,
  onSessionLost,
}: {
  canWrite: boolean;
  onSessionLost: () => void;
}) {
  const t = useT();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ProductStatus | "">("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");

  const products = useApiResource(
    () => api.products({ search: search.trim() || undefined, status: statusFilter || undefined }),
    [search, statusFilter, refreshKey],
    onSessionLost,
  );

  async function run(action: () => Promise<string>) {
    setSaving(true);
    setMessage("");
    setFailure("");
    try {
      setMessage(await action());
      setRefreshKey((key) => key + 1);
    } catch (reason) {
      setFailure(formatApiError(reason, t).message);
    } finally {
      setSaving(false);
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const specsRaw = String(data.get("specifications") ?? "").trim();
    let specifications: Record<string, unknown> = {};
    if (specsRaw) {
      try {
        const parsed: unknown = JSON.parse(specsRaw);
        if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new Error();
        specifications = parsed as Record<string, unknown>;
      } catch {
        setFailure(t.productsView.specificationsInvalid);
        return;
      }
    }
    void run(async () => {
      const product = await api.createProduct({
        name: String(data.get("name") ?? "").trim(),
        unit: String(data.get("unit") ?? "").trim(),
        category: String(data.get("category") ?? ""),
        code: String(data.get("code") ?? ""),
        specifications,
      });
      form.reset();
      setCreating(false);
      return t.productsView.created(product.sku);
    });
  }

  function toggleStatus(product: Product) {
    const status: ProductStatus = product.status === "active" ? "discontinued" : "active";
    void run(async () => {
      await api.updateProduct(product.id, { status });
      return `${product.sku}: ${status === "active" ? t.productsView.active : t.productsView.discontinued}`;
    });
  }

  const columns: Column<Product>[] = [
    { key: "sku", header: t.productsView.columns.sku, render: (p) => <strong className="font-mono">{p.sku}</strong> },
    { key: "name", header: t.productsView.columns.name, render: (p) => p.name },
    { key: "category", header: t.productsView.columns.category, render: (p) => p.category },
    { key: "unit", header: t.productsView.columns.unit, render: (p) => p.unit },
    {
      key: "code",
      header: t.productsView.columns.easybooksCode,
      render: (p) => (p.code ? <span className="font-mono">{p.code}</span> : "—"),
    },
    {
      key: "specifications",
      header: t.productsView.columns.specifications,
      render: (p) => {
        const entries = Object.entries(p.specifications ?? {});
        return entries.length ? entries.map(([key, value]) => `${key}: ${String(value)}`).join(" · ") : "—";
      },
    },
    {
      key: "status",
      header: t.productsView.columns.status,
      render: (p) => (
        <Status
          label={p.status === "active" ? t.productsView.active : t.productsView.discontinued}
          tone={p.status === "active" ? "success" : "neutral"}
        />
      ),
    },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: t.productsView.columns.actions,
      render: (p) => (
        <button type="button" className="secondary-button" disabled={saving} onClick={() => toggleStatus(p)}>
          {p.status === "active" ? t.productsView.discontinue : t.productsView.reactivate}
        </button>
      ),
    });
  }

  const rows = products.data ?? [];

  return (
    <section className="products-page">
      <PageHeader
        title={t.productsView.title}
        context={t.productsView.context}
        actions={
          canWrite ? (
            <button type="button" className="primary-button" onClick={() => setCreating((open) => !open)}>
              {t.productsView.newProduct}
            </button>
          ) : undefined
        }
      />

      {message && <div className="message success" role="status">{message}</div>}
      {failure && <div className="message error" role="alert">{failure}</div>}

      {canWrite && creating && (
        <Section title={t.productsView.createTitle}>
          <form className="order-form" onSubmit={create}>
            <p className="section-note">{t.productsView.skuAssigned}</p>
            <div className="field-grid three">
              <label>
                <span>{t.productsView.fields.name}</span>
                <input name="name" required maxLength={255} />
              </label>
              <label>
                <span>{t.productsView.fields.unit}</span>
                <input name="unit" required maxLength={50} />
              </label>
              <label>
                <span>{t.productsView.fields.category}</span>
                <input name="category" defaultValue="general" maxLength={100} />
              </label>
              <label>
                <span>{t.productsView.fields.easybooksCode}</span>
                <input name="code" maxLength={100} />
              </label>
              <label>
                <span>{t.productsView.fields.specifications}</span>
                <textarea name="specifications" rows={2} placeholder='{"ply": 2, "roll_length_m": 200}' />
              </label>
            </div>
            <div className="form-footer">
              <button type="button" className="secondary-button" onClick={() => setCreating(false)}>
                {t.common.cancel}
              </button>
              <button type="submit" className="primary-button" disabled={saving}>
                {saving ? t.common.saving : t.common.save}
              </button>
            </div>
          </form>
        </Section>
      )}

      <Section>
        <FilterBar>
          <input
            type="search"
            className="search-box"
            aria-label={t.productsView.searchPlaceholder}
            placeholder={t.productsView.searchPlaceholder}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <select
            aria-label={t.productsView.columns.status}
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as ProductStatus | "")}
          >
            <option value="">{t.productsView.allStatuses}</option>
            <option value="active">{t.productsView.active}</option>
            <option value="discontinued">{t.productsView.discontinued}</option>
          </select>
        </FilterBar>

        {products.loading ? (
          <Skeleton rows={5} />
        ) : products.error ? (
          <ErrorState>{t.productsView.loadFailed}</ErrorState>
        ) : rows.length === 0 ? (
          <EmptyState>{t.productsView.empty}</EmptyState>
        ) : (
          <DataTable columns={columns} rows={rows} rowKey={(p) => p.id} />
        )}
      </Section>
    </section>
  );
}
