import { type FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Role, User } from "../types";

const roleLabels: Record<Role, string> = {
  ADMIN: "Admin",
  OFFICE: "Office",
  FACTORY_READ: "Factory · read only",
};

export function AccountMenu({ user, onSignedOut }: { user: User; onSignedOut: () => void }) {
  const [open, setOpen] = useState(false);
  const [changing, setChanging] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  async function handleLogout() {
    setSigningOut(true);
    try {
      await api.logout().catch(() => undefined);
    } finally {
      onSignedOut();
    }
  }

  const initial = (user.full_name ?? user.username).charAt(0).toUpperCase();

  return (
    <div className="account-menu" ref={menuRef}>
      <button
        className={`settings-trigger ${open ? "active" : ""}`}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Settings"
        aria-expanded={open}
        title="Settings"
      >
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>

      <div className={`settings-dropdown ${open ? "open" : ""}`} role="dialog" aria-label="Account Settings">
        <div className="settings-user-header">
          <div className="settings-avatar" aria-hidden="true">
            {initial}
          </div>
          <div className="settings-user-meta">
            <strong>{user.full_name ?? user.username}</strong>
            {user.full_name && <span className="settings-user-handle">@{user.username}</span>}
          </div>
        </div>

        <div className={`settings-role-badge role-${user.role.toLowerCase().replace("_", "-")}`}>
          <span className="role-dot" aria-hidden="true" />
          <span>Status: <strong>{roleLabels[user.role]}</strong></span>
        </div>

        <hr className="settings-divider" />

        <div className="settings-actions">
          <button
            type="button"
            className={`settings-action-btn ${changing ? "active" : ""}`}
            onClick={() => setChanging((prev) => !prev)}
            aria-expanded={changing}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Change password</span>
            <svg
              className={`settings-action-chevron ${changing ? "expanded" : ""}`}
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {changing && (
            <div className="settings-password-subpanel">
              <ChangePassword
                onDone={() => {
                  setChanging(false);
                  setOpen(false);
                }}
                onCancel={() => setChanging(false)}
              />
            </div>
          )}

          <button
            type="button"
            className="settings-action-btn danger"
            onClick={handleLogout}
            disabled={signingOut}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>{signingOut ? "Signing out…" : "Sign out"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function PasswordInputWithToggle({
  label,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  autoComplete: string;
}) {
  const [show, setShow] = useState(false);

  return (
    <label>
      <span>{label}</span>
      <div className="password-input-wrapper">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          required
        />
        <button
          type="button"
          className="password-toggle-button"
          onClick={() => setShow((prev) => !prev)}
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          title={show ? "Hide password" : "Show password"}
          tabIndex={-1}
        >
          {show ? (
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
              <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
              <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
              <line x1="2" y1="2" x2="22" y2="22" />
            </svg>
          ) : (
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    </label>
  );
}

function ChangePassword({
  onDone,
  onCancel,
}: {
  onDone: () => void;
  onCancel: () => void;
}) {
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
    <form className="settings-password-form" onSubmit={submit}>
      <p>Changing your password signs out every other browser session.</p>
      {error && (
        <div className="message error" role="alert">
          {error}
        </div>
      )}
      <PasswordInputWithToggle
        label="Current password"
        value={current}
        onChange={setCurrent}
        autoComplete="current-password"
      />
      <PasswordInputWithToggle
        label="New password"
        value={next}
        onChange={setNext}
        autoComplete="new-password"
      />
      <div className="settings-password-buttons">
        <button className="primary-button small" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </button>
        <button
          className="ghost-button small"
          type="button"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
