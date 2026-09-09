import { type FormEvent, useState } from "react";
import { api } from "../api";
import type { User } from "../types";

export function Login({ onSignedIn }: { onSignedIn: (user: User) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      onSignedIn(await api.login(username, password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign-in did not work");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sign-in-page">
      <form className="sign-in-card" onSubmit={submit}>
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
        <p className="eyebrow sign-in-eyebrow">00 / AUTHENTICATION · INTERNAL ACCESS</p>
        <h1>UniOps</h1>
        <p className="sign-in-lead">Sign in to reach the order desk &amp; factory operations.</p>
        {error && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}
        <label>
          <span>Username</span>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>
        <label>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button className="primary-button large" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </section>
  );
}
