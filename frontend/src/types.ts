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

