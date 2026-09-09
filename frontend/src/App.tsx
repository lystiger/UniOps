import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { AccountMenu } from "./components/AccountMenu";
import { Login } from "./components/Login";
import { NewOrder } from "./components/NewOrder";
import { OrderBoard } from "./components/OrderBoard";
import { canWrite, type User } from "./types";

type View = "board" | "new";

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

  // A session can end while the board is open, so any route that answers 401
  // returns the whole app to sign-in rather than showing an error on a page the
  // caller can no longer load.
  const handleSessionLost = useCallback(() => {
    setUser(null);
    setView("board");
  }, []);

  if (checking) {
    return <div className="loading-state">Checking your session…</div>;
  }
  if (!user) {
    return <Login onSignedIn={setUser} />;
  }

  const writer = canWrite(user.role);

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => setView("board")}>
          <span className="brand-mark" aria-hidden="true">U</span>
          <span>
            <strong>UniOps</strong>
            <small>Order desk · 07:00–18:00</small>
          </span>
        </button>
        <nav aria-label="Primary">
          <button
            className={view === "board" ? "nav-item active" : "nav-item"}
            onClick={() => setView("board")}
          >
            Order board
          </button>
          {writer && (
            <button
              className={view === "new" ? "nav-item active" : "nav-item"}
              onClick={() => setView("new")}
            >
              + New order
            </button>
          )}
        </nav>
        <AccountMenu user={user} onSignedOut={handleSessionLost} />
      </header>

      <main>
        {view === "board" || !writer ? (
          <OrderBoard
            refreshKey={boardVersion}
            canWrite={writer}
            onNewOrder={() => setView("new")}
            onSessionLost={handleSessionLost}
          />
        ) : (
          <NewOrder
            onCreated={() => {
              setBoardVersion((version) => version + 1);
              setView("board");
            }}
            onSessionLost={handleSessionLost}
          />
        )}
      </main>
    </div>
  );
}
