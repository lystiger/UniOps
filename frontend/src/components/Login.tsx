import { type FormEvent, useState } from "react";
import { api, formatApiError } from "../api";
import { LanguageSwitcher, useT } from "../i18n";
import type { User } from "../types";

export function Login({ onSignedIn }: { onSignedIn: (user: User) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const t = useT();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      onSignedIn(await api.login(username, password));
    } catch (reason) {
      setError(formatApiError(reason, t).message);
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sign-in-page">
      <form className="sign-in-card" onSubmit={submit}>
        <div className="sign-in-top-row">
          <div className="sign-in-brand">
            <svg viewBox="0 0 64 64" className="brand-icon" aria-hidden="true">
              <rect width="64" height="64" rx="14" fill="#176b3a" />
              <path d="M18 18v20c0 9 5 14 14 14s14-5 14-14V18h-9v20c0 4-1 6-5 6s-5-2-5-6V18z" fill="#fff" />
              <path d="M32 9c7 1 11 5 12 11-7 0-11-4-12-11z" fill="#b9df70" />
            </svg>
            <span className="brand-wordmark">
              Uni<span className="brand-green-accent">-Green</span> <span className="brand-ops-slash">/</span> <span className="brand-ops-label">OPS</span>
            </span>
          </div>
          <LanguageSwitcher className="sign-in-language-switcher" variant="short" />
        </div>
        <h1>UniOps</h1>
        {error && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}
        <label>
          <span>{t.auth.username}</span>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>
        <label>
          <span>{t.auth.password}</span>
          <div className="password-input-wrapper">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              className="password-toggle-button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? t.auth.hidePassword : t.auth.showPassword}
              title={showPassword ? t.auth.hidePassword : t.auth.showPassword}
              tabIndex={-1}
            >
              {showPassword ? (
                <svg
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
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
                  width="18"
                  height="18"
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
        <button className="primary-button large" type="submit" disabled={busy}>
          {busy ? t.auth.signingIn : t.auth.signIn}
        </button>
      </form>
    </section>
  );
}
