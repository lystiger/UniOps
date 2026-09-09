/**
 * The Playwright `webServer` entry point.
 *
 * Builds the SPA, seeds a throwaway database, then serves the API and the built
 * frontend from ONE uvicorn process, so the tests hit a single origin with no
 * CORS or dev-proxy in the way. Everything it created is removed on teardown.
 */
import fs from "node:fs";
import path from "node:path";

import {
  BASE_URL,
  E2E_PORT,
  FRONTEND_DIR,
  REPO_ROOT,
  removeTempDir,
  run,
  spawnLogged,
} from "./harness.mjs";
import { seed } from "./seed.mjs";

const FACTS_LINK = path.join(FRONTEND_DIR, "e2e", ".facts.json");

let tmpDir = null;
let server = null;
let cleaned = false;

function cleanup() {
  if (cleaned) return;
  cleaned = true;
  if (server && server.exitCode === null) {
    try {
      server.kill("SIGTERM");
    } catch {
      /* already gone */
    }
  }
  fs.rmSync(FACTS_LINK, { force: true });
  removeTempDir(tmpDir);
}

process.on("exit", cleanup);
for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(signal, () => {
    cleanup();
    process.exit(0);
  });
}

if (process.env.UNIOPS_E2E_SKIP_BUILD !== "1") {
  console.log("[e2e] building the frontend...");
  run("npm", ["run", "build"], { cwd: FRONTEND_DIR, env: process.env, label: "npm run build" });
}
if (!fs.existsSync(path.join(FRONTEND_DIR, "dist/index.html"))) {
  throw new Error("frontend/dist/index.html is missing; run `npm run build` in frontend/");
}

const seeded = seed();
tmpDir = seeded.tmpDir;

// Handy for a spec or a human that wants the seeded facts. Gitignored.
fs.writeFileSync(FACTS_LINK, JSON.stringify(seeded.facts, null, 2));

console.log(`[e2e] starting uvicorn on ${BASE_URL}`);
server = spawnLogged(
  "uv",
  ["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(E2E_PORT)],
  { cwd: REPO_ROOT, env: seeded.env },
);

server.on("exit", (code, signal) => {
  cleanup();
  if (!signal) process.exit(code ?? 0);
});
