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

export interface Order {
  id: string;
  order_number: string;
  customer: Customer;
  status: OrderStatus;
  order_date: string;
  required_date: string;
  notes: string | null;
  lines: OrderLine[];
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

