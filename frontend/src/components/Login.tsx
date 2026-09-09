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
        <span className="brand-mark" aria-hidden="true">
          U
        </span>
        <h1>UniOps</h1>
        <p className="sign-in-lead">Sign in to reach the order desk.</p>
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
