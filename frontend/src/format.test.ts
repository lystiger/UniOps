import { describe, expect, it } from "vitest";
import { parseDisplayDate, quantity } from "./format";

describe("quantity", () => {
  it("drops storage padding and groups thousands the vi-VN way", () => {
    expect(quantity("1000.0000")).toBe("1.000");
    expect(quantity("12.5000")).toBe("12,5");
    expect(quantity("0.1250")).toBe("0,125");
    expect(quantity(null)).toBe("—");
  });
});

describe("parseDisplayDate", () => {
  it("reads day-first dates in the forms people type", () => {
    expect(parseDisplayDate("31/12/2026")).toBe("2026-12-31");
    expect(parseDisplayDate("1/6/2026")).toBe("2026-06-01");
    expect(parseDisplayDate("01.06.2026")).toBe("2026-06-01");
    expect(parseDisplayDate("01-06-2026")).toBe("2026-06-01");
    expect(parseDisplayDate(" 01062026 ")).toBe("2026-06-01");
  });

  it("rejects anything that is not a real calendar day", () => {
    for (const text of ["31/02/2026", "29/02/2025", "13/13/2026", "00/01/2026", "2026-06-01", "1/6/26", ""]) {
      expect(parseDisplayDate(text)).toBeNull();
    }
    expect(parseDisplayDate("29/02/2024")).toBe("2024-02-29");
  });
});
