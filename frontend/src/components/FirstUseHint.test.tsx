import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { FIRST_USE_HINT_KEY, FirstUseHint } from "./FirstUseHint";
import { LocaleProvider } from "../i18n";

beforeEach(() => localStorage.removeItem(FIRST_USE_HINT_KEY));

describe("FirstUseHint", () => {
  it("greets a first-time reader and names EasyBooks as the place finance is confirmed", () => {
    render(<FirstUseHint />);

    expect(screen.getByText(/UniOps brings order information/)).toBeInTheDocument();
    expect(screen.getByText(/checked directly in EasyBooks/)).toBeInTheDocument();
  });

  it("stays dismissed, so it is a first-use note and not a banner", () => {
    const { unmount } = render(<FirstUseHint />);
    fireEvent.click(screen.getByRole("button", { name: "Got it" }));
    expect(screen.queryByText(/UniOps brings order information/)).not.toBeInTheDocument();
    expect(localStorage.getItem(FIRST_USE_HINT_KEY)).not.toBeNull();

    unmount();
    render(<FirstUseHint />);
    expect(screen.queryByText(/UniOps brings order information/)).not.toBeInTheDocument();
  });

  it("reads in Vietnamese too, with no English left in it", () => {
    localStorage.setItem("uniops.locale", "vi");
    render(
      <LocaleProvider>
        <FirstUseHint />
      </LocaleProvider>,
    );

    expect(screen.getByText(/UniOps tập trung thông tin đơn hàng/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Đã hiểu" })).toBeInTheDocument();
    expect(screen.queryByText(/brings order information/)).not.toBeInTheDocument();
    localStorage.setItem("uniops.locale", "en");
  });
});
