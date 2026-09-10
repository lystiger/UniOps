import { expect, test, type Locator, type Page } from "@playwright/test";

import { E2E_PASSWORD, E2E_USERNAME, readSeededFacts, type SeededFacts } from "./fixtures";

/**
 * The order-to-cash capture flow, end to end: sign in, find the seeded order on
 * the board, see the EasyBooks invoice offered as its one candidate, confirm the
 * link, and check that UniOps now reports the order as invoiced.
 *
 * The invoice comes from the checked-in EasyBooks fixture that the harness
 * ingested; no live EasyBooks call happens here, and linking writes only to the
 * throwaway UniOps database.
 *
 * These tests share one seeded world and run in file order (workers: 1). The
 * link the middle test makes is removed again by the last one, so the file
 * leaves the world as it found it.
 */

/**
 * Read lazily and once. Playwright loads this file before it starts the
 * webServer, and .facts.json does not exist until the seed inside it has run.
 */
let seeded: SeededFacts | null = null;
function facts(): SeededFacts {
  seeded ??= readSeededFacts();
  return seeded;
}

/** Mirrors AccountingPanel's own money() so a subtotal shown as a total fails. */
function money(value: string) {
  return new Intl.NumberFormat("vi-VN").format(Number(value));
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill(E2E_USERNAME);
  await page.getByLabel("Password", { exact: true }).fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  // Wait for the board, not for the button to go: the button relabels itself to
  // "Signing in…" the moment it is clicked, so its absence says only that the
  // request left, not that the session cookie came back.
  await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();
}

/** The board's accounting badge for the seeded order, which also opens the panel. */
function boardBadge(page: Page) {
  return page.getByRole("button", { name: `Accounting for ${facts().order_number}` });
}

async function openAccounting(page: Page) {
  await boardBadge(page).click();
  const panel = page.getByRole("dialog", { name: `Accounting for ${facts().order_number}` });
  await expect(panel.getByRole("heading", { name: facts().order_number })).toBeVisible();
  return panel;
}

/** The <dd> of one row of the panel's summary list, by its <dt>. */
function fact(page: Page, panel: Locator, term: string) {
  return panel
    .locator(".accounting-facts > div")
    .filter({ has: page.locator("dt", { hasText: new RegExp(`^${term}$`) }) })
    .locator("dd");
}

/** An offered invoice: the row carrying a Link button. "Unlink" does not match. */
function candidateRow(page: Page, panel: Locator) {
  return panel
    .locator("li")
    .filter({ has: page.getByRole("button", { name: "Link", exact: true }) });
}

/** A confirmed invoice: the row carrying an Unlink button. */
function linkedRow(page: Page, panel: Locator) {
  return panel.locator("li").filter({ has: page.getByRole("button", { name: "Unlink" }) });
}

test("the seeded order reaches the board as an invoice candidate", async ({ page }) => {
  await signIn(page);
  await expect(boardBadge(page)).toContainText("Invoice candidate");
});

test("the panel offers the fixture invoice, and only that one", async ({ page }) => {
  await signIn(page);
  const panel = await openAccounting(page);

  await expect(fact(page, panel, "Accounting")).toHaveText("Invoice candidate");
  await expect(panel.getByText("No invoice linked to this order.")).toBeVisible();

  await expect(panel.getByRole("heading", { name: "Possible invoices" })).toBeVisible();
  // One candidate, so the panel asks for confirmation instead of warning about
  // ambiguity. Two candidates would change this line and must not go unnoticed.
  await expect(panel.getByText("Confirm only if this is the right invoice.")).toBeVisible();

  const rows = candidateRow(page, panel);
  await expect(rows).toHaveCount(1);
  await expect(rows).toContainText(facts().invoice_number);
  await expect(rows).toContainText(facts().invoice_date.split("-").reverse().join("/"));
  await expect(rows).toContainText(money(facts().invoice_total));
  await expect(rows).toContainText(`confidence ${facts().candidate_confidence}`);
});

test("linking the candidate captures the invoice against the order", async ({ page }) => {
  await signIn(page);
  const panel = await openAccounting(page);

  await candidateRow(page, panel).getByRole("button", { name: "Link", exact: true }).click();

  await expect(fact(page, panel, "Accounting")).toHaveText("Invoiced");
  const linked = linkedRow(page, panel);
  await expect(linked).toHaveCount(1);
  await expect(linked).toContainText(facts().invoice_number);
  await expect(linked).toContainText(money(facts().invoice_total));
  // The seeded evidence is strong enough that the link records how it was
  // matched rather than falling back to MANUAL.
  await expect(linked).toContainText("CUSTOMER_DATE_AMOUNT");
  await expect(linked).toContainText(`by ${E2E_USERNAME}`);

  // A linked order is no longer a candidate for anything.
  await expect(panel.getByRole("heading", { name: "Possible invoices" })).toHaveCount(0);
  await expect(panel.getByText("Linking records the match in UniOps only. EasyBooks is never changed.")).toBeVisible();

  await panel.getByRole("button", { name: "Close" }).click();
  await expect(boardBadge(page)).toContainText("Invoiced");
});

test("the captured link is stored, not just shown", async ({ page }) => {
  await signIn(page);
  await expect(boardBadge(page)).toContainText("Invoiced");

  const panel = await openAccounting(page);
  await expect(fact(page, panel, "Accounting")).toHaveText("Invoiced");
  await expect(linkedRow(page, panel)).toContainText(facts().invoice_number);

  // Nothing observed in EasyBooks says this invoice was paid, and UniOps reports
  // that as unknown rather than as nothing owed.
  await expect(fact(page, panel, "Payment")).toHaveText("Unknown");
  await expect(fact(page, panel, "Outstanding")).toHaveText("—");
});

test("the API agrees with the panel", async ({ page }) => {
  await signIn(page);

  // page.request, not the standalone `request` fixture: the session cookie the
  // sign-in set lives in the page's context, and a bare fixture has none.
  const response = await page.request.get(`/api/orders/${facts().order_id}/accounting`);
  expect(response.status(), await response.text()).toBe(200);
  const accounting = await response.json();
  expect(accounting).toMatchObject({
    order_number: facts().order_number,
    accounting_status: "INVOICED",
    candidate_count: 0,
  });
  expect(accounting.invoices).toHaveLength(1);
  expect(accounting.invoices[0]).toMatchObject({
    source_id: facts().invoice_source_id,
    invoice_number: facts().invoice_number,
    invoice_series: facts().invoice_series,
    document_date: facts().invoice_date,
    created_by: E2E_USERNAME,
  });
});

test("unlinking returns the order to a candidate", async ({ page }) => {
  await signIn(page);
  const panel = await openAccounting(page);

  await linkedRow(page, panel).getByRole("button", { name: "Unlink" }).click();

  await expect(fact(page, panel, "Accounting")).toHaveText("Invoice candidate");
  await expect(panel.getByText("No invoice linked to this order.")).toBeVisible();
  await expect(candidateRow(page, panel)).toHaveCount(1);

  await panel.getByRole("button", { name: "Close" }).click();
  await expect(boardBadge(page)).toContainText("Invoice candidate");
});
