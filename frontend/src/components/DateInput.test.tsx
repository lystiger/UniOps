import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { LocaleProvider } from "../i18n";
import { DateInput } from "./DateInput";

describe("DateInput", () => {
  it("shows an ISO value day-first and hands back ISO for a typed day-first date", () => {
    const onChange = vi.fn();
    render(
      <label>
        Due
        <DateInput value="2026-06-01" onChange={onChange} />
      </label>,
    );
    const input = screen.getByLabelText("Due");
    expect(input).toHaveValue("01/06/2026");

    // 3 April, never 4 March.
    fireEvent.change(input, { target: { value: "3/4/2026" } });
    expect(onChange).toHaveBeenLastCalledWith("2026-04-03");
  });

  it("never hands back an impossible date, and flags it once the field is left", () => {
    const onChange = vi.fn();
    render(
      <label>
        Due
        <DateInput value="" onChange={onChange} />
      </label>,
    );
    const input = screen.getByLabelText("Due") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "31/02/2026" } });
    expect(onChange).not.toHaveBeenCalled();
    expect(input).not.toHaveAttribute("aria-invalid");

    fireEvent.blur(input);
    expect(input).toHaveAttribute("aria-invalid", "true");
    // A form holding this field refuses to submit rather than send the last good date.
    expect(input.validity.valid).toBe(false);
  });

  it("holds back a date outside its min", () => {
    const onChange = vi.fn();
    render(
      <label>
        Due
        <DateInput value="" min="2026-06-10" onChange={onChange} />
      </label>,
    );
    const input = screen.getByLabelText("Due");

    fireEvent.change(input, { target: { value: "09/06/2026" } });
    expect(onChange).not.toHaveBeenCalled();

    fireEvent.change(input, { target: { value: "10/06/2026" } });
    expect(onChange).toHaveBeenLastCalledWith("2026-06-10");
  });

  it("follows a value set from outside, such as a preset or a reset", () => {
    function Harness() {
      const [value, setValue] = useState("2026-06-01");
      return (
        <>
          <label>
            Due
            <DateInput value={value} onChange={setValue} />
          </label>
          <button type="button" onClick={() => setValue("")}>
            Reset
          </button>
        </>
      );
    }
    render(<Harness />);
    expect(screen.getByLabelText("Due")).toHaveValue("01/06/2026");

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.getByLabelText("Due")).toHaveValue("");
  });

  it("asks for the date in Vietnamese on the Vietnamese screen", () => {
    localStorage.setItem("uniops.locale", "vi");
    render(
      <LocaleProvider>
        <label>
          Hạn giao
          <DateInput value="" onChange={vi.fn()} />
        </label>
      </LocaleProvider>,
    );
    expect(screen.getByLabelText("Hạn giao")).toHaveAttribute("placeholder", "ngày/tháng/năm");
    localStorage.removeItem("uniops.locale");
  });
});
