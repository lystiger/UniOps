import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { E2E_PASSWORD, E2E_USERNAME, readSeededFacts, type SeededFacts } from "./fixtures";

let seeded: SeededFacts | null = null;
function facts(): SeededFacts {
  seeded ??= readSeededFacts();
  return seeded;
}

function saveScreenshot(sourceRelPath: string, buffer: Buffer) {
  const rootOut = path.resolve("../../output/playwright/i18n", path.basename(sourceRelPath));
  const srcOut = path.resolve("../output/playwright/i18n", path.basename(sourceRelPath));
  fs.mkdirSync(path.dirname(rootOut), { recursive: true });
  fs.mkdirSync(path.dirname(srcOut), { recursive: true });
  fs.writeFileSync(rootOut, buffer);
  fs.writeFileSync(srcOut, buffer);
}

test.describe("i18n locale flow & translations", () => {
  test("1. fresh browser with no stored preference shows Vietnamese sign-in screen and html[lang='vi']", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "vi");
    await expect(page.getByRole("heading", { name: "UniOps" })).toBeVisible();
    await expect(page.getByText("Đăng nhập để vào bàn điều phối đơn hàng & xưởng sản xuất.")).toBeVisible();
    await expect(page.getByLabel("Tên đăng nhập")).toBeVisible();
    await expect(page.getByLabel("Mật khẩu", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Đăng nhập" })).toBeVisible();

    const switcher = page.locator(".sign-in-language-switcher");
    await expect(switcher).toBeVisible();
    await expect(switcher.getByRole("button", { name: "Tiếng Việt" })).toBeVisible();
    await expect(switcher.getByRole("button", { name: "English" })).toBeVisible();
  });

  test("2. sign in using Vietnamese labels, then see Vietnamese navigation", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Tên đăng nhập").fill(E2E_USERNAME);
    await page.getByLabel("Mật khẩu", { exact: true }).fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Đăng nhập" }).click();

    await expect(page.getByRole("heading", { name: "Bảng đơn hàng" })).toBeVisible();
    const nav = page.getByRole("navigation");
    await expect(nav.getByRole("button", { name: "Tổng quan" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Đơn hàng", exact: true })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Tài chính" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Dữ liệu" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Tạo đơn hàng" })).toBeVisible();
  });

  test("3. switch to English from settings menu; page stays and text changes without reload", async ({
    page,
  }) => {
    // Start in Vietnamese
    await page.addInitScript(() => localStorage.setItem("uniops.locale", "vi"));
    await page.goto("/");
    await page.getByLabel("Tên đăng nhập").fill(E2E_USERNAME);
    await page.getByLabel("Mật khẩu", { exact: true }).fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByRole("heading", { name: "Bảng đơn hàng" })).toBeVisible();

    // Open settings menu
    await page.getByRole("button", { name: "Cài đặt" }).click();
    const settingsDialog = page.getByRole("dialog", { name: "Cài đặt tài khoản" });
    await expect(settingsDialog).toBeVisible();
    await expect(settingsDialog.getByText("Ngôn ngữ")).toBeVisible();

    // Click English
    await settingsDialog.getByRole("button", { name: "English" }).click();

    // Text changes immediately without page reload
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("dialog", { name: "Account Settings" })).toBeVisible();

    // Close settings dialog
    await page.keyboard.press("Escape");
    await expect(settingsDialog).toHaveCount(0);

    // Main page is now in English
    await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();
    const nav = page.getByRole("navigation");
    await expect(nav.getByRole("button", { name: "Overview" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Orders", exact: true })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Finance" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Data" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "New order" })).toBeVisible();
  });

  test("4. reload: English persists from localStorage", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("uniops.locale", "en"));
    await page.goto("/");
    await page.getByLabel("Username").fill(E2E_USERNAME);
    await page.getByLabel("Password", { exact: true }).fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();

    // Reload the page
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();
    await expect(page.getByRole("navigation").getByRole("button", { name: "Overview" })).toBeVisible();
  });

  test("5. switch back to Vietnamese from sign-in screen after signing out", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("uniops.locale", "en"));
    await page.goto("/");
    await page.getByLabel("Username").fill(E2E_USERNAME);
    await page.getByLabel("Password", { exact: true }).fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();

    // Open settings and sign out
    await page.getByRole("button", { name: "Settings" }).click();
    await page.getByRole("button", { name: "Sign out" }).click();

    // On sign-in screen, currently in English
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
    await expect(page.getByLabel("Username")).toBeVisible();

    // Switch to Vietnamese
    await page.locator(".sign-in-language-switcher").getByRole("button", { name: "Tiếng Việt" }).click();

    // Screen updates immediately to Vietnamese
    await expect(page.locator("html")).toHaveAttribute("lang", "vi");
    await expect(page.getByRole("button", { name: "Đăng nhập" })).toBeVisible();
    await expect(page.getByLabel("Tên đăng nhập")).toBeVisible();
    await expect(page.getByLabel("Mật khẩu", { exact: true })).toBeVisible();
  });

  test("6. Vietnamese error path: ORDER_HAS_LINKED_INVOICES on order cancellation", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("uniops.locale", "vi"));
    await page.goto("/");
    await page.getByLabel("Tên đăng nhập").fill(E2E_USERNAME);
    await page.getByLabel("Mật khẩu", { exact: true }).fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByRole("heading", { name: "Bảng đơn hàng" })).toBeVisible();

    // 1. Open accounting panel and link candidate invoice
    const acctBadge = page.getByRole("button", {
      name: new RegExp(`Kế toán cho.*${facts().order_number}`),
    });
    await acctBadge.click();
    const panel = page.getByRole("dialog", {
      name: new RegExp(`Kế toán cho.*${facts().order_number}`),
    });
    await expect(panel).toBeVisible();

    // Link invoice
    await panel.getByRole("button", { name: "Liên kết", exact: true }).click();
    await expect(panel.getByRole("button", { name: "Hủy liên kết" })).toBeVisible();
    await panel.getByRole("button", { name: "Đóng" }).click();
    await expect(panel).toHaveCount(0);

    // 2. Try to cancel the order while it has a linked invoice
    page.once("dialog", async (dialog) => {
      expect(dialog.message()).toContain(facts().order_number);
      await dialog.accept();
    });

    await page.getByRole("button", { name: `Hủy đơn hàng ${facts().order_number}` }).click();

    // 3. Assert Vietnamese error message appears
    const errorBanner = page.locator(".message.error[role='alert']");
    await expect(errorBanner).toBeVisible();
    await expect(errorBanner).toContainText(
      "Không thể hủy đơn hàng đã liên kết hóa đơn; vui lòng hủy liên kết tất cả hóa đơn trước.",
    );

    // 4. Clean up: unlink invoice to leave database in pristine state
    await acctBadge.click();
    await expect(panel).toBeVisible();
    await panel.getByRole("button", { name: "Hủy liên kết" }).click();
    await expect(panel.getByRole("button", { name: "Liên kết", exact: true })).toBeVisible();
    await panel.getByRole("button", { name: "Đóng" }).click();
    await expect(panel).toHaveCount(0);
  });
});

test.describe("Task 6: layout verification screenshots in both languages", () => {
  for (const locale of ["vi", "en"] as const) {
    test(`captures screenshots for ${locale}`, async ({ page }) => {
      await page.addInitScript((loc) => localStorage.setItem("uniops.locale", loc), locale);

      // 1. Sign-in screen
      await page.goto("/");
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      const signinPng = await page.screenshot();
      saveScreenshot(`signin-${locale}.png`, signinPng);

      // Sign in
      const isVi = locale === "vi";
      await page.getByLabel(isVi ? "Tên đăng nhập" : "Username").fill(E2E_USERNAME);
      await page.getByLabel(isVi ? "Mật khẩu" : "Password", { exact: true }).fill(E2E_PASSWORD);
      await page.getByRole("button", { name: isVi ? "Đăng nhập" : "Sign in" }).click();
      await expect(page.getByRole("heading", { name: isVi ? "Bảng đơn hàng" : "Order board" })).toBeVisible();

      // 2. Orders board with cards
      const ordersPng = await page.screenshot();
      saveScreenshot(`orders-${locale}.png`, ordersPng);

      // 3. New order drawer
      await page.getByRole("navigation").getByRole("button", { name: isVi ? "Tạo đơn hàng" : "New order" }).click();
      await expect(page.getByRole("heading", { name: isVi ? "Tạo đơn hàng" : "New order" })).toBeVisible();
      const newOrderPng = await page.screenshot();
      saveScreenshot(`neworder-${locale}.png`, newOrderPng);

      // Back to orders board
      await page.getByRole("navigation").getByRole("button", { name: isVi ? "Đơn hàng" : "Orders", exact: true }).click();
      await expect(page.getByRole("heading", { name: isVi ? "Bảng đơn hàng" : "Order board" })).toBeVisible();

      // 4. Accounting panel with candidates
      const badge = page.getByRole("button", {
        name: new RegExp(isVi ? `Kế toán cho.*${facts().order_number}` : `Accounting for.*${facts().order_number}`),
      });
      await badge.click();
      const acctPanel = page.getByRole("dialog", {
        name: new RegExp(isVi ? `Kế toán cho.*${facts().order_number}` : `Accounting for.*${facts().order_number}`),
      });
      await expect(acctPanel).toBeVisible();
      const acctPng = await page.screenshot();
      saveScreenshot(`accounting-${locale}.png`, acctPng);
      await acctPanel.getByRole("button", { name: isVi ? "Đóng" : "Close" }).click();

      // 5. Settings menu with language switcher open
      await page.getByRole("button", { name: isVi ? "Cài đặt" : "Settings" }).click();
      const settingsDialog = page.getByRole("dialog", {
        name: isVi ? "Cài đặt tài khoản" : "Account Settings",
      });
      await expect(settingsDialog).toBeVisible();
      const settingsPng = await page.screenshot();
      saveScreenshot(`settings-${locale}.png`, settingsPng);
      await page.keyboard.press("Escape");

      // 6. Overview
      await page.getByRole("button", { name: isVi ? "Tổng quan" : "Overview" }).click();
      await expect(page.getByRole("heading", { name: isVi ? "Tổng quan" : "Overview", exact: true })).toBeVisible();
      const overviewPng = await page.screenshot();
      saveScreenshot(`overview-${locale}.png`, overviewPng);

      // 7. Finance with date filter open
      await page.getByRole("button", { name: isVi ? "Tài chính" : "Finance" }).click();
      await expect(page.getByRole("heading", { name: isVi ? "Tài chính" : "Finance" })).toBeVisible();
      await page.locator(".dual-calendar-trigger").click();
      await expect(page.locator(".dual-calendar-popover")).toBeVisible();
      const financePng = await page.screenshot();
      saveScreenshot(`finance-${locale}.png`, financePng);

      // 8. Data page
      await page.getByRole("button", { name: isVi ? "Dữ liệu" : "Data" }).click();
      await expect(page.getByRole("heading", { name: isVi ? "Dữ liệu" : "Data" })).toBeVisible();
      const dataPng = await page.screenshot();
      saveScreenshot(`data-${locale}.png`, dataPng);
    });
  }
});
