import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountMenu } from "./AccountMenu";
import type { User } from "../types";

const adminUser: User = {
  id: "user-admin",
  username: "admin",
  full_name: "Operations Director",
  role: "ADMIN",
  is_active: true,
  last_login_at: null,
};

afterEach(() => vi.restoreAllMocks());

describe("AccountMenu", () => {
  it("renders the settings trigger button and toggles the settings menu", () => {
    render(<AccountMenu user={adminUser} onSignedOut={vi.fn()} />);

    const trigger = screen.getByRole("button", { name: "Settings" });
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    const dialog = screen.getByRole("dialog", { name: "Account Settings" });
    expect(dialog).not.toHaveClass("open");

    // Open settings menu
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(dialog).toHaveClass("open");

    // Holds user info and Status: Admin
    expect(screen.getByText("Operations Director")).toBeInTheDocument();
    expect(screen.getByText("@admin")).toBeInTheDocument();
    expect(screen.getByText("Status:")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();

    // Holds Change password and Sign out
    expect(screen.getByRole("button", { name: /Change password/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign out/i })).toBeInTheDocument();

    // Close settings menu
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(dialog).not.toHaveClass("open");
  });

  it("closes the dropdown when pressing Escape", () => {
    render(<AccountMenu user={adminUser} onSignedOut={vi.fn()} />);

    const trigger = screen.getByRole("button", { name: "Settings" });
    fireEvent.click(trigger);

    const dialog = screen.getByRole("dialog", { name: "Account Settings" });
    expect(dialog).toHaveClass("open");

    fireEvent.keyDown(document, { key: "Escape" });
    expect(dialog).not.toHaveClass("open");
  });

  it("calls sign-out API and triggers onSignedOut callback", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 })
    );
    const onSignedOut = vi.fn();
    render(<AccountMenu user={adminUser} onSignedOut={onSignedOut} />);

    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    fireEvent.click(screen.getByRole("button", { name: /Sign out/i }));

    await waitFor(() => expect(onSignedOut).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("allows toggling the change password form and submitting new password", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 })
    );
    render(<AccountMenu user={adminUser} onSignedOut={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    fireEvent.click(screen.getByRole("button", { name: /Change password/i }));

    expect(screen.getByLabelText("Current password")).toBeInTheDocument();
    expect(screen.getByLabelText("New password")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "old-password-12" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-34" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/auth/change-password",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            current_password: "old-password-12",
            new_password: "new-password-34",
          }),
        })
      );
    });
  });
});
