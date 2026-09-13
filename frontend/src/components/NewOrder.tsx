import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api, formatApiError, UnauthorizedError } from "../api";
import { useT } from "../i18n";
import type { Customer, NewOrderLine, Product } from "../types";
import { DateInput } from "./DateInput";

const ignoreSessionLoss = () => undefined;

/** A field label carrying its "*" or its "(không bắt buộc)".
 *
 * The pilot could not tell which fields were mandatory. Both markers are
 * `aria-hidden`: the control's own `required` attribute is what a screen reader
 * announces, so the accessible name stays the field's name and is never doubled.
 * The "*" is explained once by the form's legend, so it is not colour-only. */
function FieldLabel({ text, required = false }: { text: string; required?: boolean }) {
  const t = useT();
  return (
    <span>
      {text}
      {required ? (
        <span className="field-required" aria-hidden="true">
          *
        </span>
      ) : (
        <>
          {" "}
          <span className="field-optional" aria-hidden="true">
            ({t.common.optional.toLowerCase()})
          </span>
        </>
      )}
    </span>
  );
}

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
    // The API rejects quantity <= 0 as a generic REQUEST_INVALID. Saying which
    // field is wrong is the whole difference between a fixable form and a wall.
    if (lines.some((line) => !(Number(line.quantity) > 0))) {
      setError(t.newOrder.errors.quantityInvalid);
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
          <p className="form-required-legend">{t.newOrder.requiredLegend}</p>
          <fieldset className="form-section">
            <legend>{t.newOrder.orderDetails}</legend>
            <div className="field-grid three">
              <label>
                <FieldLabel text={t.newOrder.customer} required />
                <select value={customerId} onChange={(event) => setCustomerId(event.target.value)} required>
                  <option value="">{t.newOrder.chooseCustomer}</option>
                  {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}
                </select>
              </label>
              <label>
                <FieldLabel text={t.newOrder.orderDate} required />
                <DateInput value={orderDate} onChange={setOrderDate} required />
              </label>
              <label>
                <FieldLabel text={t.newOrder.requiredDate} required />
                <DateInput min={orderDate} value={requiredDate} onChange={setRequiredDate} required />
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
                      <FieldLabel text={t.newOrder.product} />
                      <select value={line.product_id} onChange={(event) => selectProduct(index, event.target.value)}>
                        <option value="">{t.newOrder.customItem}</option>
                        {products.map((product) => <option key={product.id} value={product.id}>{product.code ? `${product.code} — ` : ""}{product.name}</option>)}
                      </select>
                    </label>
                    <label className="description-field">
                      <FieldLabel text={t.newOrder.description} required />
                      <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} required />
                      <span className="field-help">{t.newOrder.descriptionHelp}</span>
                    </label>
                    <label>
                      <FieldLabel text={t.newOrder.quantity} required />
                      <input inputMode="decimal" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} placeholder="0" required />
                      <span className="field-help">{t.newOrder.quantityHelp}</span>
                    </label>
                    <label>
                      <FieldLabel text={t.newOrder.unit} required />
                      <input value={line.unit} onChange={(event) => updateLine(index, { unit: event.target.value })} required />
                      <span className="field-help">{t.newOrder.unitHelp}</span>
                    </label>
                    <label>
                      <FieldLabel text={t.newOrder.agreedPrice} />
                      <input inputMode="decimal" value={line.agreed_unit_price} onChange={(event) => updateLine(index, { agreed_unit_price: event.target.value })} placeholder="0" />
                      <span className="field-help">{t.newOrder.agreedPriceHelp}</span>
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
              <FieldLabel text={t.newOrder.productionDeliveryNotes} />
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
          <label><FieldLabel text={t.newOrder.customerName} required /><input value={customerName} onChange={(event) => setCustomerName(event.target.value)} required /></label>
          <button className="secondary-button" type="submit">{t.newOrder.addCustomer}</button>
        </form>
      </details>
      <details>
        <summary>{t.newOrder.addProduct}</summary>
        <form onSubmit={addProduct}>
          <label><FieldLabel text={t.newOrder.productCode} /><input value={product.code} onChange={(event) => setProduct({ ...product, code: event.target.value })} /></label>
          <label><FieldLabel text={t.newOrder.productName} required /><input value={product.name} onChange={(event) => setProduct({ ...product, name: event.target.value })} required /></label>
          <label><FieldLabel text={t.newOrder.productUnit} required /><input value={product.unit} onChange={(event) => setProduct({ ...product, unit: event.target.value })} required /></label>
          <button className="secondary-button" type="submit">{t.newOrder.addProduct}</button>
        </form>
      </details>
    </aside>
  );
}
