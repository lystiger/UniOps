import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { AccountMenu } from "./components/AccountMenu";
import { DataView } from "./components/DataView";
import { FinanceView } from "./components/FinanceView";
import { LoadingScreen } from "./components/LoadingScreen";
import { Login } from "./components/Login";
import { NewOrder } from "./components/NewOrder";
import { OrderBoard } from "./components/OrderBoard";
import { OverviewView } from "./components/OverviewView";
import { canWrite, type User } from "./types";

type View = "board" | "new" | "overview" | "finance" | "data";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [view, setView] = useState<View>("board");
  const [boardVersion, setBoardVersion] = useState(0);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  // A session can end while any view is open, so any route that answers 401
  // returns the whole app to sign-in rather than showing an error on a page the
  // caller can no longer load.
  const handleSessionLost = useCallback(() => {
    setUser(null);
    setView("board");
  }, []);

  if (checking) {
    return <LoadingScreen />;
  }
  if (!user) {
    return <Login onSignedIn={setUser} />;
  }

  const writer = canWrite(user.role);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand-section">
          <button className="brand" type="button" onClick={() => setView("board")}>
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 64 64" className="brand-icon">
                <rect width="64" height="64" rx="14" fill="#176b3a" />
                <path d="M18 18v20c0 9 5 14 14 14s14-5 14-14V18h-9v20c0 4-1 6-5 6s-5-2-5-6V18z" fill="#fff" />
                <path d="M32 9c7 1 11 5 12 11-7 0-11-4-12-11z" fill="#b9df70" />
              </svg>
            </span>
            <div className="brand-text">
              <span className="brand-logo-text">
                Uni<span className="brand-green-accent">-Green</span>
                <span className="brand-slash">/</span>
                <span className="brand-ops-label">OPS</span>
              </span>
            </div>
          </button>
        </div>

        <nav className="topbar-nav" aria-label="Primary">
          <button
            className={view === "overview" ? "nav-item active" : "nav-item"}
            type="button"
            onClick={() => setView("overview")}
          >
            Overview
          </button>
          <button
            className={view === "board" ? "nav-item active" : "nav-item"}
            type="button"
            onClick={() => setView("board")}
          >
            Orders
          </button>
          <button
            className={view === "finance" ? "nav-item active" : "nav-item"}
            type="button"
            onClick={() => setView("finance")}
          >
            Finance
          </button>
          <button
            className={view === "data" ? "nav-item active" : "nav-item"}
            type="button"
            onClick={() => setView("data")}
          >
            Data
          </button>
          {writer && (
            <button
              className={view === "new" ? "nav-item active" : "nav-item"}
              type="button"
              onClick={() => setView("new")}
            >
              + New order
            </button>
          )}
        </nav>

        <div className="topbar-actions">
          <AccountMenu user={user} onSignedOut={handleSessionLost} />
        </div>
      </header>

      <main>
        {view === "overview" && (
          <OverviewView
            onNavigateOrders={() => setView("board")}
            onNewOrder={() => setView("new")}
            canWrite={writer}
            onSessionLost={handleSessionLost}
          />
        )}
        {view === "board" && (
          <OrderBoard
            refreshKey={boardVersion}
            canWrite={writer}
            onNewOrder={() => setView("new")}
            onSessionLost={handleSessionLost}
          />
        )}
        {view === "new" && writer && (
          <NewOrder
            onCreated={() => {
              setBoardVersion((version) => version + 1);
              setView("board");
            }}
            onSessionLost={handleSessionLost}
          />
        )}
        {view === "finance" && <FinanceView onSessionLost={handleSessionLost} />}
        {view === "data" && <DataView onSessionLost={handleSessionLost} />}
      </main>
    </div>
  );
}
