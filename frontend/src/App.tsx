import { useState } from "react";
import { NewOrder } from "./components/NewOrder";
import { OrderBoard } from "./components/OrderBoard";

type View = "board" | "new";

export default function App() {
  const [view, setView] = useState<View>("board");
  const [boardVersion, setBoardVersion] = useState(0);

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
          <button
            className={view === "new" ? "nav-item active" : "nav-item"}
            onClick={() => setView("new")}
          >
            + New order
          </button>
        </nav>
      </header>

      <main>
        {view === "board" ? (
          <OrderBoard refreshKey={boardVersion} onNewOrder={() => setView("new")} />
        ) : (
          <NewOrder
            onCreated={() => {
              setBoardVersion((version) => version + 1);
              setView("board");
            }}
          />
        )}
      </main>
    </div>
  );
}

