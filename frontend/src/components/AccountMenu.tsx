import { type FormEvent, useState } from "react";
import { api } from "../api";
import type { Role, User } from "../types";

const roleLabels: Record<Role, string> = {
  ADMIN: "Admin",
  OFFICE: "Office",
  FACTORY_READ: "Factory · read only",
};

export function AccountMenu({ user, onSignedOut }: { user: User; onSignedOut: () => void }) {
  const [changing, setChanging] = useState(false);

  return (
    <div className="account-menu">
      <span className="account-identity">
        <strong>{user.full_name ?? user.username}</strong>
        <small>{roleLabels[user.role]}</small>
      </span>
      <button className="nav-item" type="button" onClick={() => setChanging((open) => !open)}>
        Change password
      </button>
      <button
        className="nav-item"
        type="button"
        onClick={async () => {
          // A failed sign-out still means this browser should stop showing data.
          await api.logout().catch(() => undefined);
          onSignedOut();
        }}
      >
        Sign out
      </button>
      {changing && <ChangePassword onDone={() => setChanging(false)} />}
    </div>
  );
}

function ChangePassword({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.changePassword(current, next);
      onDone();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Password was not changed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="password-panel" onSubmit={submit}>
      <p>Changing your password signs out every other browser.</p>
      {error && (
        <div className="message error" role="alert">
          {error}
        </div>
      )}
      <label>
        <span>Current password</span>
        <input
          type="password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <label>
        <span>New password</span>
        <input
          type="password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
          autoComplete="new-password"
          required
        />
      </label>
      <button className="secondary-button" type="submit" disabled={busy}>
        {busy ? "Saving…" : "Save password"}
      </button>
    </form>
  );
}
