import { type FormEvent, useEffect, useState } from "react";
import { api, UnauthorizedError } from "../api";
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

  async function loadCatalog() {
    try {
      const [customerItems, productItems] = await Promise.all([api.customers(), api.products()]);
      setCustomers(customerItems);
      setProducts(productItems);
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        onSessionLost();
        return;
      }
      setError(reason instanceof Error ? reason.message : "Could not load the catalog");
    }
  }

  useEffect(() => {
    loadCatalog();
  }, []);

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
      setError("Choose a customer before saving the order");
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
      setError(reason instanceof Error ? reason.message : "Order was not saved");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="new-order-page">
      <div className="page-heading compact">
        <div>
          <p className="eyebrow">Secretary intake</p>
          <h1>New order</h1>
          <p>Capture what the customer needs. Production planning comes next.</p>
        </div>
      </div>

      <div className="intake-layout">
        <form className="order-form" onSubmit={submit}>
          {error && <div className="message error" role="alert">{error}</div>}
          <fieldset className="form-section">
            <legend>Order details</legend>
            <div className="field-grid three">
              <label>
                <span>Customer</span>
                <select value={customerId} onChange={(event) => setCustomerId(event.target.value)} required>
                  <option value="">Choose customer</option>
                  {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}
                </select>
              </label>
              <label>
                <span>Order date</span>
                <input type="date" value={orderDate} onChange={(event) => setOrderDate(event.target.value)} required />
              </label>
              <label>
                <span>Required date</span>
                <input type="date" min={orderDate} value={requiredDate} onChange={(event) => setRequiredDate(event.target.value)} required />
              </label>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Products</legend>
            <div className="line-list">
              {lines.map((line, index) => (
                <div className="line-editor" key={index}>
                  <div className="line-index">{String(index + 1).padStart(2, "0")}</div>
                  <div className="field-grid line-fields">
                    <label className="product-field">
                      <span>Product</span>
                      <select value={line.product_id} onChange={(event) => selectProduct(index, event.target.value)}>
                        <option value="">Custom item</option>
                        {products.map((product) => <option key={product.id} value={product.id}>{product.code ? `${product.code} — ` : ""}{product.name}</option>)}
                      </select>
                    </label>
                    <label className="description-field">
                      <span>Description</span>
                      <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} required />
                    </label>
                    <label>
                      <span>Quantity</span>
                      <input inputMode="decimal" value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} placeholder="0" required />
                    </label>
                    <label>
                      <span>Unit</span>
                      <input value={line.unit} onChange={(event) => updateLine(index, { unit: event.target.value })} required />
                    </label>
                    <label>
                      <span>Agreed price</span>
                      <input inputMode="decimal" value={line.agreed_unit_price} onChange={(event) => updateLine(index, { agreed_unit_price: event.target.value })} placeholder="Optional" />
                    </label>
                    <button
                      type="button"
                      className="remove-line"
                      disabled={lines.length === 1}
                      onClick={() => setLines((items) => items.filter((_, position) => position !== index))}
                      aria-label={`Remove product line ${index + 1}`}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <button type="button" className="secondary-button" onClick={() => setLines((items) => [...items, emptyLine()])}>
              + Add product line
            </button>
          </fieldset>

          <fieldset className="form-section">
            <legend>Notes</legend>
            <label>
              <span>Production or delivery notes</span>
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} placeholder="Width, packing, delivery contact, or other instructions" />
            </label>
          </fieldset>

          <div className="form-footer">
            <p>Orders start in <strong>Waiting</strong> status.</p>
            <button className="primary-button large" disabled={saving} type="submit">
              {saving ? "Saving…" : "Save order"}
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

  async function addCustomer(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setFailure("");
    try {
      await api.createCustomer({ name: customerName });
      setCustomerName("");
      setMessage("Customer added");
      await reload();
    } catch (reason) {
      setFailure(reason instanceof Error ? reason.message : "Customer was not added");
    }
  }

  async function addProduct(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setFailure("");
    try {
      await api.createProduct(product);
      setProduct({ code: "", name: "", unit: "kg" });
      setMessage("Product added");
      await reload();
    } catch (reason) {
      setFailure(reason instanceof Error ? reason.message : "Product was not added");
    }
  }

  return (
    <aside className="catalog-panel">
      <p className="eyebrow">Quick setup</p>
      <h2>Catalog</h2>
      <p>{customers.length} customers · {products.length} products</p>
      {message && <div className="message success" role="status">{message}</div>}
      {failure && <div className="message error" role="alert">{failure}</div>}
      <details>
        <summary>Add customer</summary>
        <form onSubmit={addCustomer}>
          <label><span>Name</span><input value={customerName} onChange={(event) => setCustomerName(event.target.value)} required /></label>
          <button className="secondary-button" type="submit">Add customer</button>
        </form>
      </details>
      <details>
        <summary>Add product</summary>
        <form onSubmit={addProduct}>
          <label><span>Code</span><input value={product.code} onChange={(event) => setProduct({ ...product, code: event.target.value })} /></label>
          <label><span>Name</span><input value={product.name} onChange={(event) => setProduct({ ...product, name: event.target.value })} required /></label>
          <label><span>Unit</span><input value={product.unit} onChange={(event) => setProduct({ ...product, unit: event.target.value })} required /></label>
          <button className="secondary-button" type="submit">Add product</button>
        </form>
      </details>
    </aside>
  );
}
