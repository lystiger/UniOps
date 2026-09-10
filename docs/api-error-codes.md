# UniOps API Error Codes Reference

This document catalogs machine-readable error codes returned by the UniOps API. Handled API exceptions return a structured JSON response body with `detail`, `code`, and `params`:

```json
{
  "detail": "cannot cancel an order with linked invoices; unlink all invoices first",
  "code": "ORDER_HAS_LINKED_INVOICES",
  "params": {}
}
```

- **`detail`**: English explanation string preserved for backward compatibility with API consumers, server logs, and tests.
- **`code`**: Stable uppercase snake_case string used by the frontend to select localized messages.
- **`params`**: Key-value dictionary containing contextual parameters for dynamic interpolation.

---

## Error Codes Catalog

| Code | HTTP Status | Meaning | Parameters |
|---|---|---|---|
| `AUTH_REQUIRED` | 401 Unauthorized | Authentication is required to access the endpoint. | `{}` |
| `INVALID_CREDENTIALS` | 401 Unauthorized | Incorrect username or password. | `{}` |
| `ACCOUNT_DISABLED` | 401 Unauthorized | User account has been deactivated. | `{}` |
| `PERMISSION_DENIED` | 403 Forbidden | User role does not permit this action. | `{"role": "<role>"}` |
| `INVALID_CURRENT_PASSWORD` | 403 Forbidden | Current password verification failed. | `{}` |
| `ORDER_NOT_FOUND` | 404 Not Found | Specified order was not found. | `{"order_id": "<id>"}` |
| `ORDER_LINE_NOT_FOUND` | 404 Not Found | Specified order line item was not found. | `{}` |
| `CUSTOMER_NOT_FOUND` | 404 / 422 | Customer was not found. | `{"customer_id": "<id>"}` |
| `PRODUCT_NOT_FOUND` | 422 Unprocessable | Product referenced by order line does not exist. | `{}` |
| `SALES_DOCUMENT_NOT_FOUND` | 404 Not Found | EasyBooks sales document not found. | `{}` |
| `LINK_NOT_FOUND` | 404 Not Found | Order-to-invoice link relationship not found. | `{}` |
| `ORDER_HAS_LINKED_INVOICES` | 409 Conflict | Cannot cancel an order with linked invoices. | `{}` |
| `CUSTOMER_CODE_EXISTS` | 409 Conflict | Customer source code already exists in catalog. | `{}` |
| `PRODUCT_CODE_EXISTS` | 409 Conflict | Product code already exists in catalog. | `{}` |
| `INVOICE_ALREADY_LINKED` | 409 Conflict | Invoice is already linked to this order. | `{}` |
| `CANNOT_LINK_CANCELLED_ORDER` | 409 Conflict | Invoices cannot be linked to cancelled orders. | `{}` |
| `REQUIRED_DATE_BEFORE_ORDER_DATE` | 422 Unprocessable | Required delivery date is before order date. | `{}` |
| `DUPLICATE_LINE_POSITION` | 422 Unprocessable | Multiple order lines have duplicate positions. | `{}` |
| `CANNOT_UPDATE_ORDER_STATUS` | 422 Unprocessable | Order is closed or cancelled and cannot be edited. | `{"status": "<status>"}` |
| `INVALID_STATUS_TRANSITION` | 422 Unprocessable | Requested order status transition is disallowed. | `{"from": "<status>", "to": "<status>"}` |
| `CANNOT_EDIT_CLOSED_OR_CANCELLED_ORDER` | 422 Unprocessable | Lines cannot be edited on closed/cancelled order. | `{}` |
| `LINE_POSITION_EXISTS` | 422 Unprocessable | Order line position already occupied. | `{}` |
| `ORDER_REQUIRES_AT_LEAST_ONE_LINE` | 422 Unprocessable | Cannot delete the only line on an order. | `{}` |
| `INVALID_DATE_WINDOW` | 422 Unprocessable | Start date (`from_date`) is after end date (`to_date`). | `{"from_date": "...", "to_date": "..."}` |
| `WEAK_PASSWORD` | 422 Unprocessable | Password does not meet minimum length requirement. | `{"min_length": <int>}` |
| `REQUEST_INVALID` | 422 Unprocessable | Pydantic schema validation failure on request payload. | `{}` |
| `USER_EXISTS` | Internal / CLI | Username is already taken during user creation. | `{"username": "<name>"}` |
| `USER_NOT_FOUND` | Internal / CLI | Username does not exist during password or role change. | `{"username": "<name>"}` |
| `USERNAME_REQUIRED` | Internal / CLI | Username cannot be blank. | `{}` |

