export type Role = "ADMIN" | "OFFICE" | "FACTORY_READ";

export interface User {
  id: string;
  username: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}

/** Roles that may create or change anything. FACTORY_READ may only look. */
export const WRITE_ROLES: Role[] = ["ADMIN", "OFFICE"];

export function canWrite(role: Role): boolean {
  return WRITE_ROLES.includes(role);
}

export type OrderStatus =
  | "DRAFT"
  | "CONFIRMED"
  | "SCHEDULED"
  | "IN_PRODUCTION"
  | "READY"
  | "DELIVERY_PENDING"
  | "DELIVERED"
  | "INVOICED"
  | "CLOSED"
  | "CANCELLED";

export interface Customer {
  id: string;
  name: string;
  tax_code: string | null;
  easybooks_accounting_object_code: string | null;
}

export interface Product {
  id: string;
  code: string | null;
  name: string;
  unit: string;
  easybooks_material_goods_id: string | null;
}

export interface OrderLine {
  id: string;
  product_id: string | null;
  product: Product | null;
  position: number;
  description: string;
  quantity: string;
  unit: string;
  agreed_unit_price: string | null;
  notes: string | null;
}

/** Derived from EasyBooks data on every request. Never stored on the order. */
export type AccountingStatus = "NOT_INVOICED" | "INVOICE_CANDIDATE" | "INVOICED";
export type PaymentStatus = "UNKNOWN" | "UNPAID" | "PARTIALLY_PAID" | "PAID";
export type DueStatus = "UNKNOWN" | "DUE" | "OVERDUE";

export interface Order {
  id: string;
  order_number: string;
  customer: Customer;
  status: OrderStatus;
  order_date: string;
  required_date: string;
  notes: string | null;
  lines: OrderLine[];
  accounting_status: AccountingStatus | null;
}

export interface LinkedInvoice {
  link_id: string;
  sales_document_id: string;
  invoice_number: string | null;
  invoice_series: string | null;
  document_date: string | null;
  total_amount: string;
  link_method: string;
  confidence: string | null;
  created_by: string | null;
  payment_status: PaymentStatus;
  due_date: string | null;
  due_status: DueStatus;
}

export interface OrderAccounting {
  order_id: string;
  order_number: string;
  lifecycle_status: string;
  order_total: string | null;
  accounting_status: AccountingStatus;
  payment_status: PaymentStatus;
  outstanding_amount: string | null;
  /** Says in words why outstanding is null, so null is never read as "nothing owed". */
  outstanding_status: string;
  invoices: LinkedInvoice[];
  candidate_count: number;
}

export interface InvoiceCandidate {
  sales_document_id: string;
  source_id: string;
  invoice_number: string | null;
  document_date: string | null;
  total_amount: string;
  confidence: string;
  evidence: Record<string, unknown>;
}

export interface OrderList {
  items: Order[];
  total: number;
}

export interface NewOrderLine {
  product_id: string;
  description: string;
  quantity: string;
  unit: string;
  agreed_unit_price: string;
  notes: string;
}

// --- Analytics (read-only, derived from EasyBooks data on request) --------

export interface MonthlyAmount {
  month: string;
  amount: string;
  document_count: number;
}

export interface SalesSummary {
  document_count: number;
  customer_count: number;
  total: string;
  vat_amount: string;
  undated_document_count: number;
  by_month: MonthlyAmount[];
}

export interface PurchaseSummary {
  document_count: number;
  supplier_count: number;
  total: string;
  vat_amount: string;
  undated_document_count: number;
  by_month: MonthlyAmount[];
}

export interface CommercialOverview {
  from_date: string | null;
  to_date: string | null;
  sales: SalesSummary;
  purchases: PurchaseSummary;
  /** Gross commercial flow. Not profit: purchases in a period are not the cost
   * of the goods sold in that period. */
  sales_minus_purchases: string;
}

export interface CustomerReceivable {
  customer_id: string | null;
  customer_code: string;
  customer_name: string | null;
  invoice_count: number;
  total_invoiced: string;
  oldest_invoice_date: string | null;
  newest_invoice_date: string | null;
  /** Null, not zero: zero would assert the customer owes nothing. */
  outstanding_amount: string | null;
  overdue_amount: string | null;
}

export interface Receivables {
  as_of: string;
  from_date: string | null;
  to_date: string | null;
  total_invoiced: string;
  invoice_count: number;
  linked_invoice_count: number;
  unlinked_invoice_count: number;
  total_outstanding: string | null;
  total_overdue: string | null;
  unpaid_invoice_count: number | null;
  overdue_invoice_count: number | null;
  /** Says in words why the figures above are null. */
  outstanding_status: string;
  due_status: string;
  customers: CustomerReceivable[];
}

export interface CustomerInvoice {
  sales_document_id: string;
  invoice_number: string | null;
  invoice_series: string | null;
  document_date: string | null;
  total_amount: string;
  vat_amount: string;
  paid_amount: string | null;
  outstanding_amount: string | null;
  payment_status: PaymentStatus;
  due_date: string | null;
  due_status: DueStatus;
  linked_order_numbers: string[];
}

export interface CustomerReceivableDetail {
  customer_id: string;
  customer_name: string;
  customer_code: string | null;
  as_of: string;
  invoice_count: number;
  total_invoiced: string;
  oldest_invoice_date: string | null;
  total_outstanding: string | null;
  overdue_amount: string | null;
  outstanding_status: string;
  due_status: string;
  invoices: CustomerInvoice[];
}

// --- Synchronization (EasyBooks ingestion history, read-only) -------------

export type SyncRunStatus = "RUNNING" | "SUCCEEDED" | "PARTIAL" | "FAILED";

export interface SyncRun {
  id: string;
  mode: string;
  from_date: string | null;
  to_date: string | null;
  started_at: string;
  finished_at: string | null;
  status: SyncRunStatus;
  documents_seen: number;
  documents_created: number;
  documents_updated: number;
  documents_unchanged: number;
  documents_failed: number;
  reconciliation_warnings: number;
  error_summary: string | null;
}

// --- Operational exceptions ("what needs attention") ----------------------

export type ExceptionCategory =
  | "DELIVERED_ORDER_NOT_INVOICED"
  | "INVOICE_WITHOUT_ORDER"
  | "AMBIGUOUS_INVOICE_CANDIDATES"
  | "LINKED_CUSTOMER_MISMATCH"
  | "LINKED_AMOUNT_MISMATCH"
  | "INVOICE_WITHOUT_CUSTOMER_CODE";

export interface ExceptionItem {
  category: ExceptionCategory;
  reference: string;
  detail: string;
  customer_name: string | null;
  document_date: string | null;
  total_amount: string | null;
  order_id: string | null;
  sales_document_id: string | null;
}

export interface ExceptionGroup {
  category: ExceptionCategory;
  count: number;
  items: ExceptionItem[];
}

export interface ExceptionReport {
  as_of: string;
  total: number;
  groups: ExceptionGroup[];
}

export interface DateWindow {
  from_date?: string;
  to_date?: string;
}

