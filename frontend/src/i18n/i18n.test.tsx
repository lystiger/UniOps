import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, formatApiError } from "../api";
import { AccountMenu } from "../components/AccountMenu";
import { AccountingPanel } from "../components/AccountingPanel";
import { DataView } from "../components/DataView";
import { FinanceView } from "../components/FinanceView";
import { Login } from "../components/Login";
import { NewOrder } from "../components/NewOrder";
import { OrderBoard } from "../components/OrderBoard";
import { OverviewView } from "../components/OverviewView";
import { en } from "./en";
import { LanguageSwitcher, LocaleProvider, useLocale, useT } from "./index";
import { vi as viDict } from "./vi";
import type {
  AccountingStatus,
  ExceptionCategory,
  Order,
  OrderStatus,
  PaymentStatus,
  Role,
  SyncRunStatus,
  User,
} from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

const sampleParams = {
  count: 5,
  overdueCount: 2,
  orderNumber: "ORD-001",
  orderTotal: "100.000 ₫",
  invoiceSubtotal: "100.000 ₫",
  invoiceTotal: "100.000 ₫",
  n: 3,
  total: 10,
  showing: 5,
  name: "Cust A",
  user: "admin",
  m: 2,
  s: 14,
  role: "ADMIN",
  order_id: "ord-1",
  customer_id: "c-1",
  status: "CONFIRMED",
  from: "DRAFT",
  to: "CONFIRMED",
  from_date: "2026-01-01",
  to_date: "2026-01-02",
  min_length: 8,
  username: "user1",
  index: 1,
};

describe("i18n infrastructure", () => {
  describe("Dictionary parity", () => {
    it("has identical keys and non-empty values at every level between vi and en", () => {
      function compareObjects(
        objA: Record<string, unknown>,
        objB: Record<string, unknown>,
        path = "",
      ) {
        const keysA = Object.keys(objA).sort();
        const keysB = Object.keys(objB).sort();
        expect(keysA, `Mismatched keys at ${path || "root"}`).toEqual(keysB);

        for (const key of keysA) {
          const valA = objA[key];
          const valB = objB[key];
          const currentPath = path ? `${path}.${key}` : key;

          expect(typeof valA, `Type mismatch at ${currentPath}`).toBe(typeof valB);

          if (typeof valA === "string") {
            expect((valA as string).trim().length, `Empty string at vi.${currentPath}`).toBeGreaterThan(0);
            expect(((valB as unknown) as string).trim().length, `Empty string at en.${currentPath}`).toBeGreaterThan(0);
          } else if (typeof valA === "function") {
            const resA = (valA as (p: unknown) => unknown)(sampleParams);
            const resB = (valB as (p: unknown) => unknown)(sampleParams);
            expect(typeof resA, `Function at vi.${currentPath} did not return string`).toBe("string");
            expect(typeof resB, `Function at en.${currentPath} did not return string`).toBe("string");
            expect((resA as string).trim().length, `Empty result at vi.${currentPath}`).toBeGreaterThan(0);
            expect((resB as string).trim().length, `Empty result at en.${currentPath}`).toBeGreaterThan(0);
          } else if (typeof valA === "object" && valA !== null) {
            compareObjects(
              valA as Record<string, unknown>,
              valB as Record<string, unknown>,
              currentPath,
            );
          }
        }
      }

      compareObjects(viDict as unknown as Record<string, unknown>, en as unknown as Record<string, unknown>);
    });
  });

  describe("Enum coverage", () => {
    it("covers every OrderStatus", () => {
      const statuses: OrderStatus[] = [
        "DRAFT",
        "CONFIRMED",
        "SCHEDULED",
        "IN_PRODUCTION",
        "READY",
        "DELIVERY_PENDING",
        "DELIVERED",
        "INVOICED",
        "CLOSED",
        "CANCELLED",
      ];
      for (const s of statuses) {
        expect(viDict.orders.status[s]).toBeTruthy();
        expect(en.orders.status[s]).toBeTruthy();
      }
    });

    it("covers every AccountingStatus", () => {
      const statuses: AccountingStatus[] = ["NOT_INVOICED", "INVOICE_CANDIDATE", "INVOICED"];
      for (const s of statuses) {
        expect(viDict.accounting.status[s]).toBeTruthy();
        expect(en.accounting.status[s]).toBeTruthy();
      }
    });

    it("covers every PaymentStatus", () => {
      const statuses: PaymentStatus[] = ["UNKNOWN", "UNPAID", "PARTIALLY_PAID", "PAID"];
      for (const s of statuses) {
        expect(viDict.accounting.paymentStatus[s]).toBeTruthy();
        expect(en.accounting.paymentStatus[s]).toBeTruthy();
      }
    });

    it("covers every SyncRunStatus", () => {
      const statuses: SyncRunStatus[] = ["RUNNING", "SUCCEEDED", "PARTIAL", "FAILED"];
      for (const s of statuses) {
        expect(viDict.sync.status[s]).toBeTruthy();
        expect(en.sync.status[s]).toBeTruthy();
      }
    });

    it("covers every Role", () => {
      const roles: Role[] = ["ADMIN", "OFFICE", "FACTORY_READ"];
      for (const r of roles) {
        expect(viDict.roles[r]).toBeTruthy();
        expect(en.roles[r]).toBeTruthy();
      }
    });

    it("covers every ExceptionCategory", () => {
      const categories: ExceptionCategory[] = [
        "DELIVERED_ORDER_NOT_INVOICED",
        "INVOICE_WITHOUT_ORDER",
        "AMBIGUOUS_INVOICE_CANDIDATES",
        "LINKED_CUSTOMER_MISMATCH",
        "LINKED_AMOUNT_MISMATCH",
        "INVOICE_WITHOUT_CUSTOMER_CODE",
      ];
      for (const c of categories) {
        expect(viDict.overview.attentionIssues[c]).toBeTruthy();
        expect(en.overview.attentionIssues[c]).toBeTruthy();
      }
    });

    it("covers every documented backend error code", () => {
      const codes = [
        "AUTH_REQUIRED",
        "INVALID_CREDENTIALS",
        "ACCOUNT_DISABLED",
        "PERMISSION_DENIED",
        "INVALID_CURRENT_PASSWORD",
        "ORDER_NOT_FOUND",
        "ORDER_LINE_NOT_FOUND",
        "CUSTOMER_NOT_FOUND",
        "PRODUCT_NOT_FOUND",
        "SALES_DOCUMENT_NOT_FOUND",
        "LINK_NOT_FOUND",
        "ORDER_HAS_LINKED_INVOICES",
        "CUSTOMER_CODE_EXISTS",
        "PRODUCT_CODE_EXISTS",
        "INVOICE_ALREADY_LINKED",
        "CANNOT_LINK_CANCELLED_ORDER",
        "REQUIRED_DATE_BEFORE_ORDER_DATE",
        "DUPLICATE_LINE_POSITION",
        "CANNOT_UPDATE_ORDER_STATUS",
        "INVALID_STATUS_TRANSITION",
        "CANNOT_EDIT_CLOSED_OR_CANCELLED_ORDER",
        "LINE_POSITION_EXISTS",
        "ORDER_REQUIRES_AT_LEAST_ONE_LINE",
        "INVALID_DATE_WINDOW",
        "WEAK_PASSWORD",
        "REQUEST_INVALID",
        "USER_EXISTS",
        "USER_NOT_FOUND",
        "USERNAME_REQUIRED",
        "generic",
        "networkError",
      ];
      for (const code of codes) {
        expect(viDict.errors[code as keyof typeof viDict.errors]).toBeTruthy();
        expect(en.errors[code as keyof typeof en.errors]).toBeTruthy();
      }
    });
  });

  describe("Locale behaviour", () => {
    function TestConsumer() {
      const { locale, setLocale } = useLocale();
      const t = useT();
      return (
        <div>
          <span data-testid="locale">{locale}</span>
          <span data-testid="text">{t.nav.overview}</span>
          <button data-testid="switch-en" onClick={() => setLocale("en")}>EN</button>
          <button data-testid="switch-vi" onClick={() => setLocale("vi")}>VI</button>
        </div>
      );
    }

    it("defaults to vi with no stored preference and sets document.documentElement.lang", () => {
      localStorage.removeItem("uniops.locale");
      render(
        <LocaleProvider>
          <TestConsumer />
        </LocaleProvider>,
      );

      expect(screen.getByTestId("locale")).toHaveTextContent("vi");
      expect(screen.getByTestId("text")).toHaveTextContent("Tổng quan");
      expect(document.documentElement.lang).toBe("vi");
    });

    it("honours stored preference and updates document.documentElement.lang", () => {
      localStorage.setItem("uniops.locale", "en");
      render(
        <LocaleProvider>
          <TestConsumer />
        </LocaleProvider>,
      );

      expect(screen.getByTestId("locale")).toHaveTextContent("en");
      expect(screen.getByTestId("text")).toHaveTextContent("Overview");
      expect(document.documentElement.lang).toBe("en");
    });

    it("falls back to vi when localStorage access throws", () => {
      const getItemSpy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
        throw new Error("SecurityError: storage disabled");
      });
      render(
        <LocaleProvider>
          <TestConsumer />
        </LocaleProvider>,
      );

      expect(screen.getByTestId("locale")).toHaveTextContent("vi");
      expect(screen.getByTestId("text")).toHaveTextContent("Tổng quan");
      expect(document.documentElement.lang).toBe("vi");
      getItemSpy.mockRestore();
    });

    it("switches locale immediately, persists in localStorage, and updates document.documentElement.lang", () => {
      localStorage.removeItem("uniops.locale");
      render(
        <LocaleProvider>
          <TestConsumer />
        </LocaleProvider>,
      );

      expect(screen.getByTestId("locale")).toHaveTextContent("vi");
      expect(document.documentElement.lang).toBe("vi");

      fireEvent.click(screen.getByTestId("switch-en"));

      expect(screen.getByTestId("locale")).toHaveTextContent("en");
      expect(screen.getByTestId("text")).toHaveTextContent("Overview");
      expect(document.documentElement.lang).toBe("en");
      expect(localStorage.getItem("uniops.locale")).toBe("en");

      fireEvent.click(screen.getByTestId("switch-vi"));
      expect(screen.getByTestId("locale")).toHaveTextContent("vi");
      expect(screen.getByTestId("text")).toHaveTextContent("Tổng quan");
      expect(document.documentElement.lang).toBe("vi");
      expect(localStorage.getItem("uniops.locale")).toBe("vi");
    });
  });

  describe("Error rendering", () => {
    it("renders Vietnamese text for known ApiError code", () => {
      const err = new ApiError(409, "cannot cancel an order with linked invoices; unlink all invoices first", "ORDER_HAS_LINKED_INVOICES");
      const res = formatApiError(err, viDict, "vi");
      expect(res.message).toBe("Không thể hủy đơn hàng đã liên kết hóa đơn; vui lòng hủy liên kết tất cả hóa đơn trước.");
      expect(res.detail).toBe("cannot cancel an order with linked invoices; unlink all invoices first");
    });

    it("renders parameters into localized error message", () => {
      const err = new ApiError(422, "disallowed transition", "INVALID_STATUS_TRANSITION", { from: "DELIVERED", to: "CANCELLED" });
      const res = formatApiError(err, viDict, "vi");
      expect(res.message).toBe('Không thể chuyển trạng thái từ "DELIVERED" sang "CANCELLED".');
    });

    it("renders generic message for unknown or missing code in Vietnamese, keeping detail in detail field only", () => {
      const err = new ApiError(500, "Internal database error occurred", "UNEXPECTED_CODE");
      const res = formatApiError(err, viDict, "vi");
      expect(res.message).toBe("Đã có lỗi xảy ra. Vui lòng thử lại sau.");
      expect(res.detail).toBe("Internal database error occurred");
      expect(res.message).not.toContain("database error");
    });

    it("renders network error for NETWORK_ERROR code", () => {
      const err = new ApiError(0, "Cannot reach the server", "NETWORK_ERROR");
      const res = formatApiError(err, viDict, "vi");
      expect(res.message).toBe("Không thể kết nối đến máy chủ. Vui lòng kiểm tra đường truyền.");
    });
  });
});

describe("Vietnamese view English leakage checks", () => {
  beforeEach(() => {
    localStorage.setItem("uniops.locale", "vi");
  });

  const mockUser: User = {
    id: "user-1",
    username: "testuser",
    full_name: "Nguyễn Văn A",
    role: "ADMIN",
    is_active: true,
    last_login_at: null,
  };

  const mockOrder: Order = {
    id: "ord-1",
    order_number: "ORD-101",
    customer: {
      id: "cust-1",
      name: "Công ty Bao bì Á Châu",
      tax_code: "0102030405",
      easybooks_accounting_object_code: "KH001",
    },
    status: "IN_PRODUCTION",
    order_date: "2026-08-01",
    required_date: "2026-08-15",
    notes: null,
    lines: [
      {
        id: "line-1",
        product_id: "prod-1",
        product: { id: "prod-1", code: "P01", name: "Hộp carton 3 lớp", unit: "chiếc", easybooks_material_goods_id: null },
        position: 1,
        description: "Hộp carton 3 lớp",
        quantity: "500",
        unit: "chiếc",
        agreed_unit_price: "10000",
        notes: null,
      },
    ],
    accounting_status: "INVOICE_CANDIDATE",
  };

  it("Login view renders in Vietnamese without leaking English UI strings", () => {
    render(
      <LocaleProvider>
        <Login onSignedIn={vi.fn()} />
      </LocaleProvider>,
    );

    expect(screen.getByRole("heading", { name: "UniOps" })).toBeInTheDocument();
    expect(screen.getByText("Đăng nhập để vào bàn điều phối đơn hàng & xưởng sản xuất.")).toBeInTheDocument();
    expect(screen.getByLabelText("Tên đăng nhập")).toBeInTheDocument();
    expect(screen.getByLabelText("Mật khẩu")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Đăng nhập" })).toBeInTheDocument();

    expect(screen.queryByText("Sign in to reach the order desk & factory operations.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("AccountMenu view renders in Vietnamese without leaking English UI strings", () => {
    render(
      <LocaleProvider>
        <AccountMenu user={mockUser} onSignedOut={vi.fn()} />
      </LocaleProvider>,
    );

    const trigger = screen.getByRole("button", { name: "Cài đặt" });
    fireEvent.click(trigger);

    expect(screen.getByText("Quản trị viên")).toBeInTheDocument();
    expect(screen.getByText("Đổi mật khẩu")).toBeInTheDocument();
    expect(screen.getByText("Đăng xuất")).toBeInTheDocument();
    expect(screen.getByText("Ngôn ngữ")).toBeInTheDocument();

    expect(screen.queryByText("Change password")).not.toBeInTheDocument();
    expect(screen.queryByText("Sign out")).not.toBeInTheDocument();
  });

  it("OrderBoard view renders in Vietnamese without leaking English UI strings", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [mockOrder], total: 1 }), { status: 200 }),
    );

    render(
      <LocaleProvider>
        <OrderBoard refreshKey={0} onNewOrder={vi.fn()} />
      </LocaleProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Bảng đơn hàng" })).toBeInTheDocument();
    expect(await screen.findByText("Tiếp nhận")).toBeInTheDocument();
    expect(screen.getByText("Đã lên lịch")).toBeInTheDocument();
    expect(screen.getByText("Sản xuất")).toBeInTheDocument();
    expect(screen.getByText("Sẵn sàng giao")).toBeInTheDocument();
    expect(screen.getByText("Giao hàng / Đã giao")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Đơn hàng hoặc khách hàng")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Tạo đơn hàng" })).toBeInTheDocument();

    expect(screen.queryByText("Order board")).not.toBeInTheDocument();
    expect(screen.queryByText("Producing")).not.toBeInTheDocument();
  });

  it("NewOrder view renders in Vietnamese without leaking English UI strings", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));

    render(
      <LocaleProvider>
        <NewOrder onCreated={vi.fn()} />
      </LocaleProvider>,
    );

    expect(screen.getByRole("heading", { name: "Tạo đơn hàng mới" })).toBeInTheDocument();
    expect(screen.getByText("Thông tin đơn hàng")).toBeInTheDocument();
    expect(screen.getByText("Danh mục sản phẩm")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lưu đơn hàng" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Thêm dòng sản phẩm" })).toBeInTheDocument();

    expect(screen.queryByText("New order")).not.toBeInTheDocument();
    expect(screen.queryByText("Order details")).not.toBeInTheDocument();
  });

  it("OverviewView renders in Vietnamese without leaking English UI strings", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ as_of: "2026-08-01", total: 0, groups: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        from_date: null,
        to_date: null,
        sales: { document_count: 0, customer_count: 0, total: "0", vat_amount: "0", undated_document_count: 0, by_month: [] },
        purchases: { document_count: 0, supplier_count: 0, total: "0", vat_amount: "0", undated_document_count: 0, by_month: [] },
        sales_minus_purchases: "0",
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        as_of: "2026-08-01",
        from_date: null,
        to_date: null,
        total_invoiced: "0",
        invoice_count: 0,
        linked_invoice_count: 0,
        unlinked_invoice_count: 0,
        total_outstanding: null,
        total_overdue: null,
        unpaid_invoice_count: null,
        overdue_invoice_count: null,
        outstanding_status: "Chưa có thông tin công nợ",
        due_status: "",
        customers: [],
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));

    render(
      <LocaleProvider>
        <OverviewView onNavigateOrders={vi.fn()} onNewOrder={vi.fn()} canWrite={true} onSessionLost={vi.fn()} />
      </LocaleProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Tổng quan" })).toBeInTheDocument();
    expect(screen.getByText("Cần xử lý")).toBeInTheDocument();
    expect(screen.getByText("Tiến độ sản xuất")).toBeInTheDocument();
    expect(screen.getByText("Tổng quan thương mại")).toBeInTheDocument();
    expect(screen.getByText("Đồng bộ EasyBooks")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Xem bảng đơn hàng" })).toBeInTheDocument();

    expect(screen.queryByText("Production pipeline")).not.toBeInTheDocument();
    expect(screen.queryByText("Needs attention")).not.toBeInTheDocument();
  });

  it("AccountingPanel renders in Vietnamese without leaking English UI strings", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            order_id: mockOrder.id,
            order_number: mockOrder.order_number,
            lifecycle_status: "DRAFT",
            order_total: "5000000",
            accounting_status: "NOT_INVOICED",
            payment_status: "UNKNOWN",
            outstanding_amount: null,
            outstanding_status: "Chưa có thông tin công nợ",
            invoices: [],
            candidate_count: 0,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));

    render(
      <LocaleProvider>
        <AccountingPanel order={mockOrder} canWrite={true} onClose={vi.fn()} onChanged={vi.fn()} />
      </LocaleProvider>,
    );

    expect(await screen.findByText("Chưa liên kết hóa đơn")).toBeInTheDocument();
    expect(screen.getByText("Chưa có thông tin")).toBeInTheDocument();
    expect(screen.getByText("Công nợ chưa thu")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Đóng" })).toBeInTheDocument();
    expect(screen.queryByText("Not invoiced")).not.toBeInTheDocument();
  });

  it("DataView renders in Vietnamese without leaking English UI strings", async () => {
    const mockRun = {
      id: "run-1",
      started_at: "2026-08-01T10:00:00Z",
      completed_at: "2026-08-01T10:02:00Z",
      status: "SUCCEEDED" as const,
      mode: "FIXTURE",
      documents_seen: 10,
      rows_written: 10,
      reconciliation_warnings: 0,
      error_message: null,
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([mockRun]), { status: 200 }),
    );

    render(
      <LocaleProvider>
        <DataView onSessionLost={vi.fn()} />
      </LocaleProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Dữ liệu" })).toBeInTheDocument();
    expect(screen.getByText("Lần đồng bộ thành công gần nhất")).toBeInTheDocument();
    expect(screen.getByText("Các đợt đồng bộ gần đây")).toBeInTheDocument();
    expect(screen.queryByText("Last successful sync")).not.toBeInTheDocument();
  });

  it("FinanceView renders in Vietnamese without leaking English UI strings", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/analytics/overview")) {
        return new Response(
          JSON.stringify({
            from_date: null,
            to_date: null,
            sales: { document_count: 0, customer_count: 0, total: "0", vat_amount: "0", undated_document_count: 0, by_month: [] },
            purchases: { document_count: 0, supplier_count: 0, total: "0", vat_amount: "0", undated_document_count: 0, by_month: [] },
            sales_minus_purchases: "0",
          }),
          { status: 200 },
        );
      }
      if (url.includes("/api/analytics/sales")) {
        return new Response(
          JSON.stringify({ document_count: 0, customer_count: 0, total: "0", vat_amount: "0", undated_document_count: 0, by_month: [] }),
          { status: 200 },
        );
      }
      if (url.includes("/api/analytics/purchases")) {
        return new Response(
          JSON.stringify({ document_count: 0, supplier_count: 0, total: "0", vat_amount: "0", undated_document_count: 0, by_month: [] }),
          { status: 200 },
        );
      }
      if (url.includes("/api/analytics/receivables")) {
        return new Response(
          JSON.stringify({
            as_of: "2026-08-01",
            from_date: null,
            to_date: null,
            total_invoiced: "0",
            invoice_count: 0,
            linked_invoice_count: 0,
            unlinked_invoice_count: 0,
            total_outstanding: null,
            total_overdue: null,
            unpaid_invoice_count: null,
            overdue_invoice_count: null,
            outstanding_status: "Chưa có thông tin công nợ",
            due_status: "",
            customers: [],
          }),
          { status: 200 },
        );
      }
      if (url.includes("/api/sync-runs")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });

    render(
      <LocaleProvider>
        <FinanceView onSessionLost={vi.fn()} />
      </LocaleProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Tài chính" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Doanh số bán hàng" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Chi mua hàng" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Công nợ phải thu" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Sales" })).not.toBeInTheDocument();
  });

  it("LanguageSwitcher renders accessible button labels", () => {
    render(
      <LocaleProvider>
        <LanguageSwitcher />
      </LocaleProvider>,
    );
    expect(screen.getByRole("button", { name: "Tiếng Việt" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "English" })).toBeInTheDocument();
  });
});

