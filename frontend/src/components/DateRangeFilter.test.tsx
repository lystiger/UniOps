import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DateRangeFilter } from "./DateRangeFilter";

describe("DateRangeFilter", () => {
  it("renders inputs for From and To and updates via change event", () => {
    const onChange = vi.fn();
    render(<DateRangeFilter fromDate="2026-08-01" toDate="2026-08-31" onChange={onChange} />);

    const fromInput = screen.getByLabelText("From");
    const toInput = screen.getByLabelText("To");

    expect(fromInput).toHaveValue("2026-08-01");
    expect(toInput).toHaveValue("2026-08-31");

    fireEvent.change(fromInput, { target: { value: "2026-08-10" } });
    expect(onChange).toHaveBeenCalledWith({ fromDate: "2026-08-10", toDate: "2026-08-31" });
  });

  it("toggles dual calendar popover on trigger button click", () => {
    render(<DateRangeFilter fromDate="" toDate="" onChange={vi.fn()} />);

    const trigger = screen.getByRole("button", { name: "Open dual calendar range picker" });
    expect(screen.queryByRole("dialog", { name: "Date range calendar" })).not.toBeInTheDocument();

    fireEvent.click(trigger);
    expect(screen.getByRole("dialog", { name: "Date range calendar" })).toBeInTheDocument();

    // Close when clicking trigger again
    fireEvent.click(trigger);
    expect(screen.queryByRole("dialog", { name: "Date range calendar" })).not.toBeInTheDocument();
  });

  it("applies quick presets like This Month, Last Month, Last 3 Months, Last Year, and Clear", () => {
    const onChange = vi.fn();
    render(<DateRangeFilter fromDate="" toDate="" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Open dual calendar range picker" }));

    // Apply This Month
    fireEvent.click(screen.getByRole("button", { name: "This Month" }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ fromDate: expect.any(String), toDate: expect.any(String) })
    );

    // Apply Last Year
    fireEvent.click(screen.getByRole("button", { name: "Last Year" }));
    const prevYear = new Date().getFullYear() - 1;
    expect(onChange).toHaveBeenCalledWith({
      fromDate: `${prevYear}-01-01`,
      toDate: `${prevYear}-12-31`,
    });

    // Clear preset
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(onChange).toHaveBeenCalledWith({ fromDate: "", toDate: "" });
  });

  it("allows picking range start and end dates from the grid", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <DateRangeFilter fromDate="" toDate="" onChange={onChange} />
    );

    fireEvent.click(screen.getByRole("button", { name: "Open dual calendar range picker" }));

    // Click a day for start date
    const day1 = screen.getByRole("button", { name: "2026-09-10" });
    fireEvent.click(day1);

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ fromDate: expect.any(String), toDate: "" })
    );

    // Re-render with selected fromDate
    const startStr = onChange.mock.calls[0][0].fromDate;
    rerender(<DateRangeFilter fromDate={startStr} toDate="" onChange={onChange} />);

    // Click a second day to complete range
    const days = screen.getAllByRole("button", { name: /2026-/i });
    const targetDay = days.find((btn) => btn.getAttribute("aria-label")! > startStr);
    if (targetDay) {
      fireEvent.click(targetDay);
      expect(onChange).toHaveBeenCalledWith({
        fromDate: startStr,
        toDate: targetDay.getAttribute("aria-label"),
      });
    }
  });

  it("closes popover when pressing Escape", () => {
    render(<DateRangeFilter fromDate="" toDate="" onChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Open dual calendar range picker" }));
    expect(screen.getByRole("dialog", { name: "Date range calendar" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Date range calendar" })).not.toBeInTheDocument();
  });
});
