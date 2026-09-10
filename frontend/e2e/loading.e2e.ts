import { expect, test, type Page } from "@playwright/test";

/**
 * The branded splash covers a browser's first open only, and it has to be
 * readable with animations switched off (Windows "Animation effects" off,
 * Remote Desktop). It used to render there as a bare green square, because
 * every part of it started at opacity 0 and only an animation revealed it.
 */
const SPLASH_PARTS = [
  ".loading-logo-cup",
  ".loading-logo-leaf",
  ".loading-wordmark",
  ".loading-status",
  ".loading-quote",
];

// Never answer the session check, so whatever covers it stays on screen.
async function holdSessionCheck(page: Page) {
  await page.route("**/api/auth/me", () => undefined);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("uniops.locale", "en"));
});

test.describe("with reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("the first-open splash is fully visible", async ({ page }) => {
    await holdSessionCheck(page);
    await page.goto("/");
    await expect(page.locator(".loading-state-screen")).toBeVisible();
    for (const selector of SPLASH_PARTS) {
      // toBeVisible() counts opacity: 0 as visible, so check the computed value.
      await expect(page.locator(selector)).toHaveCSS("opacity", "1");
    }
  });
});

test("with motion, the first-open splash settles fully visible", async ({ page }) => {
  await holdSessionCheck(page);
  await page.goto("/");
  for (const selector of SPLASH_PARTS) {
    await expect(page.locator(selector)).toHaveCSS("opacity", "1");
  }
});

test("a reload after the first open skips the splash", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".loading-state-screen")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();

  await holdSessionCheck(page);
  await page.reload();

  await expect(page.locator(".session-check-pending")).toBeAttached();
  await expect(page.locator(".session-check-note")).toBeVisible();
  await expect(page.locator(".loading-state-screen")).toHaveCount(0);
});
