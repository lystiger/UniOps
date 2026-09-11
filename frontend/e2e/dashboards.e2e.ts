import { expect, test, type Page } from "@playwright/test";

import { E2E_PASSWORD, E2E_USERNAME, readSeededFacts, type SeededFacts } from "./fixtures";

/**
 * The operational data pages, end to end, against the same seeded world as
 * invoice-capture.e2e.ts: sign in, read the real commercial numbers on
 * Overview, filter Finance by date and watch the result actually change,
 * read real synchronization history on Data, then open (not link) the
 * accounting panel from the order board.
 *
 * Entirely read-only: this file must never link or unlink an invoice, since
 * invoice-capture.e2e.ts shares the same seeded database and workers: 1
 * world.
 */

let seeded: SeededFacts | null = null;
function facts(): SeededFacts {
  seeded ??= readSeededFacts();
  return seeded;
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("uniops.locale", "en"));
});

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill(E2E_USERNAME);
  await page.getByLabel("Password", { exact: true }).fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();
}

test("Overview shows real order and EasyBooks-derived commercial figures", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Overview" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  // Not a fabricated "01 / OPERATIONS" eyebrow, not a facility badge.
  await expect(page.getByText(/Hưng Yên/)).toHaveCount(0);

  const activeOrdersStat = page.locator(".stat", { hasText: "Active orders" });
  await expect(activeOrdersStat.locator(".stat-value")).toHaveText("1");

  // The commercial snapshot comes from /api/analytics/overview, not a
  // hard-coded figure: it must be a real, non-zero VND amount.
  await expect(page.getByText("Sales", { exact: true })).toBeVisible();
  const salesStat = page.locator(".stat", { hasText: "Sales" }).first();
  await expect(salesStat.locator(".stat-value")).not.toHaveText("—");
  await expect(salesStat.locator(".stat-value")).toContainText("₫");

  // Receivables outstanding is unknown at the source, never a fabricated 0 ₫.
  const receivablesStat = page.locator(".stat", { hasText: "Receivables outstanding" });
  await expect(receivablesStat.locator(".stat-value")).toHaveText("—");

  await expect(page.getByText(/Last EasyBooks sync:/)).toBeVisible();
});

test("Finance date filter changes what Sales actually shows", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Finance" }).click();
  await expect(page.getByRole("heading", { name: "Finance" })).toBeVisible();

  const documentsStat = page.locator(".stat", { hasText: "Documents" });
  await expect(documentsStat.locator(".stat-value")).toHaveText("1");
  await expect(page.getByText(facts().invoice_date.slice(0, 7))).toBeVisible(); // by-month row

  // A window that excludes every seeded document must actually change the
  // rendered result, not just the input's value.
  await page.getByLabel("From").fill("01/01/2030");
  await expect(page.getByText("No sales records for this period.")).toBeVisible();
  await expect(page.getByLabel("From")).toHaveValue("01/01/2030");
  await expect(page).toHaveURL(/from=2030-01-01/);

  // Clearing the filter brings the real data back.
  await page.getByLabel("From").fill("");
  await expect(documentsStat.locator(".stat-value")).toHaveText("1");
});

test("Data shows the real synchronization history, not a fabricated pipeline", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Data" }).click();

  await expect(page.getByRole("heading", { name: "Data" })).toBeVisible();
  await expect(page.getByText("Last successful sync")).toBeVisible();
  await expect(page.getByText("Extract")).toHaveCount(0);
  await expect(page.getByText("Transform")).toHaveCount(0);

  const runsTable = page.getByRole("table");
  await expect(runsTable.getByText("fixture")).toBeVisible();
  await expect(runsTable.getByText("Success")).toBeVisible();
});

test("Orders board still opens the accounting panel for the seeded order", async ({ page }) => {
  await signIn(page);
  const badge = page.getByRole("button", { name: `Accounting for ${facts().order_number}` });
  await badge.click();

  const panel = page.getByRole("dialog", { name: `Accounting for ${facts().order_number}` });
  await expect(panel.getByRole("heading", { name: facts().order_number })).toBeVisible();
  await panel.getByRole("button", { name: "Close" }).click();
  await expect(panel).toHaveCount(0);
});

test("DateRangeFilter displays unambiguously in en-US and vi-VN locales", async ({ browser }) => {
  for (const locale of ["en-US", "vi-VN"]) {
    const context = await browser.newContext({ locale });
    const page = await context.newPage();
    await page.addInitScript(() => localStorage.setItem("uniops.locale", "en"));
    await signIn(page);
    await page.getByRole("button", { name: "Finance" }).click();
    await expect(page.getByRole("heading", { name: "Finance" })).toBeVisible();

    await page.getByLabel("From").fill("01/06/2026");
    await page.getByLabel("To").fill("30/06/2026");

    // The fields themselves read day-first in both browser locales, not only the trigger.
    await expect(page.getByLabel("From")).toHaveValue("01/06/2026");
    await expect(page.getByLabel("To")).toHaveValue("30/06/2026");

    // The unambiguous DD/MM/YYYY text is displayed in the calendar trigger:
    await expect(page.locator(".dual-calendar-trigger")).toContainText("01/06/2026 – 30/06/2026");

    // Capture screenshot
    await page.locator(".date-range-bar").screenshot({
      path: `../../output/playwright/date-filter-${locale}.png`,
    });
    await context.close();
  }
});
