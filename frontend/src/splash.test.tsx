import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { SPLASH_MIN_MS, SPLASH_SEEN_KEY, hasSeenSplash } from "./splash";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

function routeSessionCheck(answer: () => Promise<Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    return url.startsWith("/api/auth/me") ? answer() : new Response("{}", { status: 404 });
  });
}

const noSession = async () => json({ detail: "sign in to use UniOps" }, 401);

beforeEach(() => {
  localStorage.setItem("uniops.locale", "en");
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.removeItem(SPLASH_SEEN_KEY);
});

describe("first-open splash", () => {
  it("shows the splash on a first open, remembers it, and holds it for the minimum time", async () => {
    localStorage.removeItem(SPLASH_SEEN_KEY);
    routeSessionCheck(noSession);

    const { container } = render(<App />);

    expect(container.querySelector(".loading-state-screen")).not.toBeNull();
    expect(hasSeenSplash()).toBe(true);

    // The session answered at once, yet the splash does not flash away.
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(container.querySelector(".loading-state-screen")).not.toBeNull();

    expect(
      await screen.findByRole("button", { name: "Sign in" }, { timeout: SPLASH_MIN_MS + 1000 }),
    ).toBeInTheDocument();
  });

  it("never shows the splash on a later open", async () => {
    localStorage.setItem(SPLASH_SEEN_KEY, "1");
    routeSessionCheck(noSession);

    const { container } = render(<App />);

    expect(container.querySelector(".loading-state-screen")).toBeNull();
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows only a quiet note, after a short delay, when a later session check is slow", async () => {
    localStorage.setItem(SPLASH_SEEN_KEY, "1");
    routeSessionCheck(() => new Promise<Response>(() => undefined));

    const { container } = render(<App />);

    expect(screen.queryByText("Verifying your session…")).not.toBeInTheDocument();
    expect(await screen.findByText("Verifying your session…")).toBeInTheDocument();
    expect(container.querySelector(".loading-state-screen")).toBeNull();
  });

  it("skips the splash when storage cannot be read", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage disabled");
    });
    routeSessionCheck(() => new Promise<Response>(() => undefined));

    const { container } = render(<App />);

    expect(hasSeenSplash()).toBe(true);
    expect(container.querySelector(".loading-state-screen")).toBeNull();
  });
});
