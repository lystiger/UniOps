import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.UNIOPS_E2E_PORT ?? 8931);
const BASE_URL = `http://127.0.0.1:${PORT}`;

/**
 * End-to-end configuration for UniOps.
 *
 * `e2e/serve.mjs` builds the SPA, seeds a THROWAWAY temp SQLite database from
 * the checked-in EasyBooks fixture, and serves the API plus the built frontend
 * from a single uvicorn process. The repository's uniops.db is never opened and
 * no live EasyBooks sync ever runs.
 *
 * Specs are named `*.e2e.ts`, not `*.spec.ts`, so that `npm test` (vitest,
 * jsdom) does not try to run them.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  fullyParallel: false,
  // The seeded world is a single shared database; one worker keeps it truthful.
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  outputDir: "./e2e/test-results",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "node e2e/serve.mjs",
    url: `${BASE_URL}/api/health`,
    reuseExistingServer: false,
    // Covers the frontend build, alembic, the fixture sync, and uvicorn boot.
    timeout: 180_000,
    // Without this Playwright SIGKILLs the server, and serve.mjs never gets to
    // delete its temp database. Any dir a crash does leave behind is swept by
    // the next seed.
    gracefulShutdown: { signal: "SIGTERM", timeout: 15_000 },
    stdout: "pipe",
    stderr: "pipe",
  },
});
