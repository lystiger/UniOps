import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DAILY_QUOTES, quoteOfTheDay } from "../quotes";
import { LoadingScreen } from "./LoadingScreen";

describe("LoadingScreen", () => {
  it("shows today's quote with its author", () => {
    render(<LoadingScreen />);

    const quote = quoteOfTheDay();
    expect(screen.getByText(new RegExp(quote.text))).toBeInTheDocument();
    expect(screen.getByText(`— ${quote.author}`)).toBeInTheDocument();
  });

  it("still shows the session-check status", () => {
    render(<LoadingScreen />);

    expect(screen.getByText("Verifying your session…")).toBeInTheDocument();
  });
});

describe("quoteOfTheDay", () => {
  it("is stable within the same day and drawn from the pool", () => {
    const now = new Date();
    const first = quoteOfTheDay(now);
    const later = quoteOfTheDay(new Date(now.getTime() + 60_000));
    expect(later).toEqual(first);
    expect(DAILY_QUOTES).toContainEqual(first);
  });

  it("only cycles across a 4-5 quote pool", () => {
    expect(DAILY_QUOTES.length).toBeGreaterThanOrEqual(4);
    expect(DAILY_QUOTES.length).toBeLessThanOrEqual(5);
  });
});
