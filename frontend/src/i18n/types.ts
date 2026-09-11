import type {
  AccountingStatus,
  ExceptionCategory,
  LinkMethod,
  OrderStatus,
  PaymentStatus,
  Role,
  SyncRunStatus,
} from "../types";

export type Locale = "vi" | "en";

export interface ErrorInterpolations {
  role?: string;
  order_id?: string;
  customer_id?: string;
  status?: string;
  from?: string;
  to?: string;
  from_date?: string;
  to_date?: string;
  min_length?: number | string;
  username?: string;
}

export type ErrorDict = {
  AUTH_REQUIRED: string;
  INVALID_CREDENTIALS: string;
  ACCOUNT_DISABLED: string;
  PERMISSION_DENIED: (p: { role: string }) => string;
  INVALID_CURRENT_PASSWORD: string;
  ORDER_NOT_FOUND: (p: { order_id?: string }) => string;
  ORDER_LINE_NOT_FOUND: string;
  CUSTOMER_NOT_FOUND: (p: { customer_id?: string }) => string;
  PRODUCT_NOT_FOUND: string;
  SALES_DOCUMENT_NOT_FOUND: string;
  LINK_NOT_FOUND: string;
  ORDER_HAS_LINKED_INVOICES: string;
  CUSTOMER_CODE_EXISTS: string;
  PRODUCT_CODE_EXISTS: string;
  INVOICE_ALREADY_LINKED: string;
  CANNOT_LINK_CANCELLED_ORDER: string;
  REQUIRED_DATE_BEFORE_ORDER_DATE: string;
  DUPLICATE_LINE_POSITION: string;
  CANNOT_UPDATE_ORDER_STATUS: (p: { status?: string }) => string;
  INVALID_STATUS_TRANSITION: (p: { from?: string; to?: string }) => string;
  CANNOT_EDIT_CLOSED_OR_CANCELLED_ORDER: string;
  LINE_POSITION_EXISTS: string;
  ORDER_REQUIRES_AT_LEAST_ONE_LINE: string;
  INVALID_DATE_WINDOW: (p: { from_date?: string; to_date?: string }) => string;
  WEAK_PASSWORD: (p: { min_length?: number | string }) => string;
  REQUEST_INVALID: string;
  USER_EXISTS: (p: { username?: string }) => string;
  USER_NOT_FOUND: (p: { username?: string }) => string;
  USERNAME_REQUIRED: string;
  generic: string;
  networkError: string;
};

export interface Dictionary {
  languageName: string;
  nav: {
    overview: string;
    orders: string;
    finance: string;
    data: string;
    newOrder: string;
    primaryNavAria: string;
  };
  roles: Record<Role, string> & {
    statusPrefix: string;
  };
  orders: {
    title: string;
    status: Record<OrderStatus, string>;
    columns: {
      waitingConfirmed: string;
      scheduled: string;
      producing: string;
      ready: string;
      deliveryDelivered: string;
    };
    actions: {
      confirm: string;
      schedule: string;
      startProduction: string;
      markReady: string;
      sendToDelivery: string;
      markDelivered: string;
      markInvoiced: string;
      closeOrder: string;
      cancelOrder: string;
      cancelOrderAria: (orderNumber: string) => string;
      confirmCancel: (params: { orderNumber: string }) => string;
      updating: string;
      newOrderBtn: string;
    };
    searchPlaceholder: string;
    searchLabel: string;
    loading: string;
    emptyColumn: string;
    activeOrdersSummary: (params: { count: number; overdueCount: number }) => string;
    overdueDelivery: string;
    requiredLabel: string;
    accountingAria: (orderNumber: string) => string;
    noLines: string;
    moreLines: (count: number) => string;
    boardAria: string;
  };
  accounting: {
    status: Record<AccountingStatus, string>;
    paymentStatus: Record<PaymentStatus, string>;
    dialogAria: (orderNumber: string) => string;
    loading: string;
    facts: {
      production: string;
      accounting: string;
      payment: string;
      outstanding: string;
    };
    linkedInvoices: string;
    noInvoiceLinked: string;
    possibleInvoices: string;
    singleCandidateNote: string;
    multipleCandidatesNote: string;
    linkNote: string;
    outstandingExposesNote: string;
    noDate: string;
    byUser: (user: string) => string;
    confidence: string;
    linkMethod: Record<LinkMethod, string>;
    actions: {
      link: string;
      linking: string;
      unlink: string;
      removing: string;
    };
  };
  overview: {
    title: string;
    stats: {
      activeOrders: string;
      producing: string;
      ready: string;
      deliveryPending: string;
      sales: string;
      purchases: string;
      receivablesOutstanding: string;
      salesMinusPurchases: string;
    };
    attention: {
      title: string;
      orderIssuesCount: (n: number) => string;
      invoiceIssuesCount: (n: number) => string;
      nothingNeedsAttention: string;
      orderExceptions: string;
      noOrderExceptions: string;
      invoiceBacklog: string;
      showingCount: (showing: number, total: number) => string;
      showingAll: (total: number) => string;
      viewAll: (total: number) => string;
      showTen: string;
      /** Issue text for a category this build doesn't know yet. */
      unknownIssue: string;
      columns: {
        reference: string;
        customer: string;
        issue: string;
        status: string;
        required: string;
        invoiceDate: string;
        amount: string;
      };
    };
    attentionIssues: Record<
      Exclude<ExceptionCategory, "LINKED_AMOUNT_MISMATCH">,
      string
    > & {
      LINKED_AMOUNT_MISMATCH: (params: {
        orderTotal: string;
        invoiceSubtotal: string;
        invoiceTotal: string;
      }) => string;
    };
    pipeline: {
      title: string;
      columns: {
        status: string;
        orders: string;
      };
      buckets: {
        waiting: string;
        scheduled: string;
        producing: string;
        ready: string;
        deliveryPending: string;
        invoicedClosed: string;
      };
    };
    commercialSnapshot: string;
    easybooksSync: string;
    actions: {
      viewOrderBoard: string;
      newOrder: string;
    };
    errors: {
      loadOrders: string;
      loadExceptions: string;
      loadAnalytics: string;
      loadSync: string;
    };
  };
  finance: {
    title: string;
    tabs: {
      sales: string;
      purchases: string;
      receivables: string;
    };
    summary: string;
    salesMinusPurchases: string;
    receivablesOutstanding: string;
    stats: {
      sales: string;
      purchases: string;
      documents: string;
      customers: string;
      suppliers: string;
      total: string;
      vat: string;
      invoiced: string;
      invoices: string;
      linkedToOrder: string;
      unlinked: string;
      outstanding: string;
    };
    columns: {
      month: string;
      documents: string;
      amount: string;
      customer: string;
      invoices: string;
      invoiced: string;
      oldestInvoice: string;
      outstanding: string;
      date: string;
      linkedOrder: string;
    };
    undatedDocumentsNote: (count: number) => string;
    outstandingBalanceNote: (status: string) => string;
    outstandingExposesNote: string;
    noSalesRecords: string;
    noPurchaseRecords: string;
    noInvoicesPeriod: string;
    noDocumentsDatedInPeriod: string;
    noInvoicesForCustomer: string;
    unavailable: string;
    customerInvoicesAria: (name: string) => string;
    customerInvoicesTitle: (name: string) => string;
    loadingInvoices: string;
    invoicesForCustomerRowAria: (name: string) => string;
    errors: {
      loadAnalytics: string;
      loadSales: string;
      loadPurchases: string;
      loadReceivables: string;
      loadCustomerInvoices: string;
    };
  };
  data: {
    title: string;
    context: string;
    /** Headline for the most recent run, keyed by its status. */
    health: Record<SyncRunStatus, string>;
    facts: {
      lastSuccess: string;
      lastAttempt: string;
      neverSucceeded: string;
    };
    counts: {
      seen: string;
      created: string;
      updated: string;
      unchanged: string;
      failed: string;
      warnings: string;
    };
    modes: {
      fixture: string;
      live: string;
      liveHeaders: string;
    };
    recentRuns: string;
    columns: {
      started: string;
      mode: string;
      period: string;
      status: string;
      documents: string;
      created: string;
      updated: string;
      failed: string;
      warnings: string;
      duration: string;
    };
    empty: string;
    noRunsYet: string;
    /** A failed sync in words; EasyBooks' raw error text sits behind `technicalDetails`. */
    syncError: {
      documentsFailed: (n: number) => string;
      stopped: string;
      technicalDetails: string;
    };
    errors: {
      loadHistory: string;
    };
  };
  dateFilter: {
    from: string;
    to: string;
    calendar: string;
    presets: string;
    thisMonth: string;
    lastMonth: string;
    last3Months: string;
    lastYear: string;
    clear: string;
    reset: string;
    done: string;
    selected: string;
    pickEndDate: string;
    promptStart: string;
    prevMonthAria: string;
    nextMonthAria: string;
    calendarDialogAria: string;
    triggerAria: string;
  };
  newOrder: {
    title: string;
    orderDetails: string;
    customer: string;
    chooseCustomer: string;
    orderDate: string;
    requiredDate: string;
    products: string;
    product: string;
    customItem: string;
    description: string;
    quantity: string;
    unit: string;
    agreedPrice: string;
    optional: string;
    removeLineAria: (index: number) => string;
    removeLine: string;
    addProductLine: string;
    notes: string;
    productionDeliveryNotes: string;
    notesPlaceholder: string;
    orderStatusNotice: string;
    saveOrder: string;
    savingOrder: string;
    catalog: string;
    catalogSummary: (customers: number, products: number) => string;
    addCustomer: string;
    addProduct: string;
    customerName: string;
    productCode: string;
    productName: string;
    productUnit: string;
    customerAdded: string;
    productAdded: string;
    errors: {
      chooseCustomerFirst: string;
      loadCatalog: string;
      orderNotSaved: string;
      customerNotAdded: string;
      productNotAdded: string;
    };
  };
  auth: {
    signIn: string;
    signingIn: string;
    username: string;
    password: string;
    showPassword: string;
    hidePassword: string;
    settingsTitle: string;
    settingsAria: string;
    changePassword: string;
    signOut: string;
    signingOut: string;
    currentPassword: string;
    newPassword: string;
    changePasswordNotice: string;
    verifyingSession: string;
    language: string;
    passwordNotChanged: string;
  };
  sync: {
    status: Record<SyncRunStatus, string>;
    checking: string;
    noSyncRunYet: string;
    lastSyncAttempt: (time: string) => string;
    lastSync: (time: string) => string;
  };
  common: {
    save: string;
    saving: string;
    cancel: string;
    close: string;
    search: string;
    loading: string;
    empty: string;
    required: string;
    status: string;
  };
  durationUnits: {
    minutes: (m: number) => string;
    seconds: (s: number) => string;
    minutesSeconds: (m: number, s: number) => string;
  };
  errors: ErrorDict;
}
