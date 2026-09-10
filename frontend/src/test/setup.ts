import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";

beforeEach(() => {
  try {
    localStorage.setItem("uniops.locale", "en");
  } catch {
    // ignore
  }
});

afterEach(cleanup);

// jsdom keeps one `window.location` for the whole test file, and FinanceView
// writes its filter state into the query string. Without this, a query set by
// one test would leak into the next test's initial render.
afterEach(() => {
  window.history.replaceState(null, "", window.location.pathname);
});
