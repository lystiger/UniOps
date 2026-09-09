import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Login } from "./Login";

afterEach(() => vi.restoreAllMocks());

describe("Login", () => {
  it("reports the server's reason and clears the password", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "username or password is not correct" }), {
        status: 401,
      }),
    );
    const onSignedIn = vi.fn();
    render(<Login onSignedIn={onSignedIn} />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "office" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("username or password is not correct");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it("sends the credentials to the sign-in route", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "user-1", username: "office", role: "OFFICE" }), {
        status: 200,
      }),
    );
    const onSignedIn = vi.fn();
    render(<Login onSignedIn={onSignedIn} />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "office" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "office-password-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await vi.waitFor(() => expect(onSignedIn).toHaveBeenCalledOnce());
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/auth/login");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      username: "office",
      password: "office-password-01",
    });
  });
});
