/**
 * Shared constants and helpers for the UniOps end-to-end harness.
 *
 * SAFETY: everything in here runs against a throwaway SQLite database created
 * under the OS temp directory. The harness never touches the repository's
 * uniops.db, never runs a live EasyBooks sync, and never reads .env values.
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { BASE_URL } from "./constants.mjs";

export const E2E_DIR = path.dirname(fileURLToPath(import.meta.url));
export const FRONTEND_DIR = path.resolve(E2E_DIR, "..");
export const REPO_ROOT = path.resolve(FRONTEND_DIR, "..");

/** Checked-in fixture. The ONLY EasyBooks data source the harness may use. */
export const FIXTURE_PATH = path.join(
  REPO_ROOT,
  "backend/tests/fixtures/easybooks_bundle.json",
);

/** Throwaway test credentials and the harness port. Shared with the specs. */
export { BASE_URL, E2E_PASSWORD, E2E_PORT, E2E_ROLE, E2E_USERNAME } from "./constants.mjs";

const TMP_PREFIX = "uniops-e2e-";

/** Absolute path of the repository database that must never be opened. */
const FORBIDDEN_DB = path.join(REPO_ROOT, "uniops.db");

/**
 * Refuse to continue if a database path is anywhere inside the repository.
 * This is the single guard that keeps real customer data out of the harness.
 */
export function assertThrowawayDatabase(dbPath) {
  const resolved = path.resolve(dbPath);
  if (resolved === FORBIDDEN_DB) {
    throw new Error(`refusing to use the repository database at ${resolved}`);
  }
  if (resolved.startsWith(REPO_ROOT + path.sep)) {
    throw new Error(
      `refusing to use a database inside the repository: ${resolved}. ` +
        "The E2E harness must use a temp directory.",
    );
  }
  if (!resolved.startsWith(path.resolve(os.tmpdir()) + path.sep)) {
    throw new Error(`refusing to use a database outside the temp directory: ${resolved}`);
  }
  return resolved;
}

/** Create a fresh temp directory for one harness run. */
export function makeTempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), TMP_PREFIX));
}

/**
 * Delete temp databases a previous run failed to clean up.
 *
 * A crashed or SIGKILLed harness leaves its directory behind; without this they
 * accumulate. Anything currently in use belongs to a run that is still holding
 * the port, so the next seed would fail anyway.
 */
export function sweepStaleTempDirs() {
  const root = path.resolve(os.tmpdir());
  let entries = [];
  try {
    entries = fs.readdirSync(root);
  } catch {
    return 0;
  }
  let removed = 0;
  for (const entry of entries) {
    if (!entry.startsWith(TMP_PREFIX)) continue;
    try {
      fs.rmSync(path.join(root, entry), { recursive: true, force: true });
      removed += 1;
    } catch {
      // Someone else's, or already gone.
    }
  }
  return removed;
}

export function removeTempDir(dir) {
  if (!dir) return;
  const resolved = path.resolve(dir);
  if (!path.basename(resolved).startsWith(TMP_PREFIX)) return;
  if (!resolved.startsWith(path.resolve(os.tmpdir()) + path.sep)) return;
  fs.rmSync(resolved, { recursive: true, force: true });
}

/**
 * The environment every backend process in the harness runs with.
 *
 * UNIOPS_* variables set here override backend/.env, because pydantic-settings
 * ranks real environment variables above the dotenv file. The EasyBooks
 * credentials are blanked so that even a mistaken --live call cannot reach the
 * real accounting system: app.config treats a blank value as unset.
 */
export function harnessEnv(dbPath) {
  const resolved = assertThrowawayDatabase(dbPath);
  return {
    ...process.env,
    UNIOPS_DATABASE_URL: `sqlite:///${resolved}`,
    UNIOPS_SERVE_FRONTEND: "true",
    UNIOPS_FRONTEND_DIST_PATH: path.join(FRONTEND_DIR, "dist"),
    UNIOPS_SESSION_COOKIE_SECURE: "false",
    UNIOPS_CORS_ORIGINS: JSON.stringify([BASE_URL]),
    // Hard-disable every live EasyBooks path.
    UNIOPS_EASYBOOKS_LIVE_ENABLED: "false",
    UNIOPS_EASYBOOKS_BEARER_TOKEN: "",
    UNIOPS_EASYBOOKS_COOKIE: "",
    UNIOPS_EASYBOOKS_USERNAME: "",
    UNIOPS_EASYBOOKS_PASSWORD: "",
    UNIOPS_EASYBOOKS_COMPANY_ID: "",
    UNIOPS_EASYBOOKS_GROUP: "",
    UNIOPS_EASYBOOKS_ORG: "",
    PYTHONUNBUFFERED: "1",
  };
}

/** Run a command to completion in the repo root, failing loudly. */
export function run(command, args, { env, input, cwd = REPO_ROOT, label } = {}) {
  const name = label ?? `${command} ${args.join(" ")}`;
  const result = spawnSync(command, args, {
    cwd,
    env,
    input,
    encoding: "utf8",
    stdio: ["pipe", "pipe", "pipe"],
  });
  if (result.error) throw new Error(`${name} could not start: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(
      `${name} exited with ${result.status}\n--- stdout ---\n${result.stdout}\n--- stderr ---\n${result.stderr}`,
    );
  }
  return result.stdout;
}

export function spawnLogged(command, args, options) {
  const child = spawn(command, args, { ...options, stdio: ["ignore", "inherit", "inherit"] });
  return child;
}

export async function waitForHealth(timeoutMs = 90_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${BASE_URL}/api/health`);
      if (response.ok) return await response.json();
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`the UniOps API never became healthy at ${BASE_URL}/api/health`);
}
