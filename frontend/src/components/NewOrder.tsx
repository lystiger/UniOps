import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api, formatApiError, UnauthorizedError } from "../api";
import { useT } from "../i18n";
import type { Customer, NewOrderLine, Product } from "../types";

const ignoreSessionLoss = () => undefined;

const emptyLine = (): NewOrderLine => ({
  product_id: "",
  description: "",
  quantity: "",
  unit: "kg",
  agreed_unit_price: "",
  notes: "",
});

function localDate(offsetDays = 0) {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

export function NewOrder({
  onCreated,
  onSessionLost = ignoreSessionLoss,
}: {
  onCreated: () => void;
  onSessionLost?: () => void;
}) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [orderDate, setOrderDate] = useState(localDate());
  const [requiredDate, setRequiredDate] = useState(localDate(3));
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<NewOrderLine[]>([emptyLine()]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const t = useT();

  const loadCatalog = useCallback(async () => {
    try {
      const [customerItems, productItems] = await Promise.all([api.customers(), api.products()]);
      setCustomers(customerItems);
      setProducts(productItems);
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(formatApiError(reason, t).message);
    }
  }, [onSessionLost, t]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  function updateLine(index: number, change: Partial<NewOrderLine>) {
    setLines((items) => items.map((line, position) => position === index ? { ...line, ...change } : line));
  }

  function selectProduct(index: number, productId: string) {
    const product = products.find((item) => item.id === productId);
    updateLine(index, {
      product_id: productId,
      description: product?.name ?? "",
      unit: product?.unit ?? "kg",
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!customerId) {
      setError(t.newOrder.errors.chooseCustomerFirst);
      return;
    }
    setSaving(true);
    try {
      await api.createOrder({
        customer_id: customerId,
        order_date: orderDate,
        required_date: requiredDate,
        notes,
        lines,
      });
      onCreated();
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(formatApiError(reason, t).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="new-order-page">
      <div className="page-heading compact">
        <div>
          <h1>{t.newOrder.title}</h1>
        </div>
      </div>

      <div className="intake-layout">
        <form className="order-form" onSubmit={submit}>
          {error && <div className="message error" role="alert">{error}</div>}
          <fieldset className="form-section">
            <legend>{t.newOrder.orderDetails}</legend>
            <div className="field-grid three">
              <label>
                <span>{t.newOrder.customer}</span>
                <select value={customerId} onChange={(event) => setCustomerId(event.target.value)} required>
                  <option value="">{t.newOrder.chooseCustomer}</option>
                  {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}
                </select>
              </label>
              <label>
                <span>{t.newOrder.orderDate}</span>
                <input type="date" value={orderDate} onChange={(event) => setOrderDate(event.target.value)} required />
              </label>
              <label>
                <span>{t.newOrder.requiredDate}</span>
                <input type="date" min={orderDate} value={requiredDate} onChange={(event) => setRequiredDate(event.target.value)} required />
              </label>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>{t.newOrder.products}</legend>
            <div className="line-list">
              {lines.map((line, index) => (
                <div className="line-editor" key={index}>
                  <div className="line-index">{String(index + 1).padStart(2, "0")}</div>
                  <div className="field-grid line-fields">
                    <label className="product-field">
                      <span>{t.newOrder.product}</span>
                      <select value={line.product_id} onChange={(event) => selectProduct(index, event.target.value)}>
                        <option value="">{t.newOrder.customItem}</option>
                        {products.map((product) => <option key={product.id} value={product.id}>{product.code ? `${product.code} — ` : ""}{product.name}</option>)}
                      </select>
                    </label>
                    <label className="description-field">
                      <span>{t.newOrder.description}</span>
                      <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} required />
                    </label>
                    <label>
                      <span>{t.newOrder.quantity}</span>
                      <input inputMode="decimal" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} placeholder="0" required />
                    </label>
                    <label>
                      <span>{t.newOrder.unit}</span>
                      <input value={line.unit} onChange={(event) => updateLine(index, { unit: event.target.value })} required />
                    </label>
                    <label>
                      <span>{t.newOrder.agreedPrice}</span>
                      <input inputMode="decimal" value={line.agreed_unit_price} onChange={(event) => updateLine(index, { agreed_unit_price: event.target.value })} placeholder={t.newOrder.optional} />
                    </label>
                    <button
                      type="button"
                      className="remove-line"
                      disabled={lines.length === 1}
                      onClick={() => setLines((items) => items.filter((_, position) => position !== index))}
                      aria-label={t.newOrder.removeLineAria(index + 1)}
                    >
                      {t.newOrder.removeLine}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <button type="button" className="secondary-button" onClick={() => setLines((items) => [...items, emptyLine()])}>
              {t.newOrder.addProductLine}
            </button>
          </fieldset>

          <fieldset className="form-section">
            <legend>{t.newOrder.notes}</legend>
            <label>
              <span>{t.newOrder.productionDeliveryNotes}</span>
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} placeholder={t.newOrder.notesPlaceholder} />
            </label>
          </fieldset>

          <div className="form-footer">
            <p>{t.newOrder.orderStatusNotice} <strong>{t.orders.status.DRAFT}</strong>.</p>
            <button className="primary-button large" disabled={saving} type="submit">
              {saving ? t.newOrder.savingOrder : t.newOrder.saveOrder}
            </button>
          </div>
        </form>

        <QuickCatalog customers={customers} products={products} reload={loadCatalog} />
      </div>
    </section>
  );
}

function QuickCatalog({ customers, products, reload }: { customers: Customer[]; products: Product[]; reload: () => Promise<void> }) {
  const [customerName, setCustomerName] = useState("");
  const [product, setProduct] = useState({ code: "", name: "", unit: "kg" });
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");
  const t = useT();

  async function addCustomer(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setFailure("");
    try {
      await api.createCustomer({ name: customerName });
      setCustomerName("");
      setMessage(t.newOrder.customerAdded);
      await reload();
    } catch (reason) {
      setFailure(formatApiError(reason, t).message);
    }
  }

  async function addProduct(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setFailure("");
    try {
      await api.createProduct(product);
      setProduct({ code: "", name: "", unit: "kg" });
      setMessage(t.newOrder.productAdded);
      await reload();
    } catch (reason) {
      setFailure(formatApiError(reason, t).message);
    }
  }

  return (
    <aside className="catalog-panel">
      <h2>{t.newOrder.catalog}</h2>
      <p>{t.newOrder.catalogSummary(customers.length, products.length)}</p>
      {message && <div className="message success" role="status">{message}</div>}
      {failure && <div className="message error" role="alert">{failure}</div>}
      <details>
        <summary>{t.newOrder.addCustomer}</summary>
        <form onSubmit={addCustomer}>
          <label><span>{t.newOrder.customerName}</span><input value={customerName} onChange={(event) => setCustomerName(event.target.value)} required /></label>
          <button className="secondary-button" type="submit">{t.newOrder.addCustomer}</button>
        </form>
      </details>
      <details>
        <summary>{t.newOrder.addProduct}</summary>
        <form onSubmit={addProduct}>
          <label><span>{t.newOrder.productCode}</span><input value={product.code} onChange={(event) => setProduct({ ...product, code: event.target.value })} /></label>
          <label><span>{t.newOrder.productName}</span><input value={product.name} onChange={(event) => setProduct({ ...product, name: event.target.value })} required /></label>
          <label><span>{t.newOrder.productUnit}</span><input value={product.unit} onChange={(event) => setProduct({ ...product, unit: event.target.value })} required /></label>
          <button className="secondary-button" type="submit">{t.newOrder.addProduct}</button>
        </form>
      </details>
    </aside>
  );
}
