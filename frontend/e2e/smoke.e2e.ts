import { expect, test } from "@playwright/test";

import { E2E_PASSWORD, E2E_USERNAME } from "./fixtures";

/**
 * Harness proof only. The real user-flow specs live in their own files.
 */
test("the API is up and reports its version", async ({ request }) => {
  const response = await request.get("/api/health");
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toMatchObject({ status: "ok" });
});

test("the app loads and shows the sign-in screen", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "UniOps" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expect(page.getByLabel("Username")).toBeVisible();
  // Exact: a non-exact match also catches the "Show password" toggle button,
  // which is a real distinct control, not the field.
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
});

test("the seeded office account can sign in", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill(E2E_USERNAME);
  await page.getByLabel("Password", { exact: true }).fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  // The board, not the absence of the button: the button relabels itself to
  // "Signing in…" the moment it is clicked, so it goes as soon as the request
  // leaves, whether or not a session ever came back.
  await expect(page.getByRole("heading", { name: "Order board" })).toBeVisible();
});
