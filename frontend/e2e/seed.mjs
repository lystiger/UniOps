/**
 * Build a complete, disposable UniOps world for the end-to-end suite.
 *
 * Steps, all against a temp SQLite file and never the repository database:
 *   1. alembic upgrade head
 *   2. create the throwaway `office` account
 *   3. ingest the CHECKED-IN EasyBooks fixture (never a live sync)
 *   4. add a customer + order that has exactly one strong invoice candidate
 *
 * Can be run on its own for debugging:  node e2e/seed.mjs
 */
import fs from "node:fs";
import path from "node:path";

import {
  E2E_PASSWORD,
  E2E_ROLE,
  E2E_USERNAME,
  FIXTURE_PATH,
  REPO_ROOT,
  assertThrowawayDatabase,
  harnessEnv,
  makeTempDir,
  run,
  sweepStaleTempDirs,
} from "./harness.mjs";

export function seed({ tmpDir } = {}) {
  sweepStaleTempDirs();
  tmpDir = tmpDir ?? makeTempDir();
  const dbPath = assertThrowawayDatabase(path.join(tmpDir, "uniops-e2e.db"));
  const env = harnessEnv(dbPath);
  const factsPath = path.join(tmpDir, "facts.json");

  if (!fs.existsSync(FIXTURE_PATH)) {
    throw new Error(`the EasyBooks fixture is missing at ${FIXTURE_PATH}`);
  }

  console.log(`[e2e seed] temp database: ${dbPath}`);

  run("uv", ["run", "alembic", "upgrade", "head"], { env, label: "alembic upgrade head" });

  run(
    "uv",
    ["run", "uniops", "user", "create", "--username", E2E_USERNAME, "--role", E2E_ROLE, "--password-stdin"],
    { env, input: `${E2E_PASSWORD}\n`, label: "uniops user create" },
  );

  // Fixture only. A live sync would read the company's real accounting system.
  const syncOutput = run(
    "uv",
    ["run", "uniops", "sync-easybooks", "--fixture", path.relative(REPO_ROOT, FIXTURE_PATH)],
    { env, label: "uniops sync-easybooks --fixture" },
  );
  const syncRun = JSON.parse(syncOutput.trim().split("\n").pop());

  const seedOutput = run(
    "uv",
    ["run", "python", path.join(REPO_ROOT, "frontend/e2e/seed_data.py"), FIXTURE_PATH],
    { env: { ...env, UNIOPS_E2E_FACTS_PATH: factsPath }, label: "seed_data.py" },
  );
  const facts = JSON.parse(seedOutput.trim().split("\n").pop());

  console.log(
    `[e2e seed] fixture sync: ${syncRun.documents_seen} documents seen, ${syncRun.created} created`,
  );
  console.log(
    `[e2e seed] order ${facts.order_number} -> invoice ${facts.invoice_number} ` +
      `(confidence ${facts.candidate_confidence})`,
  );

  return { tmpDir, dbPath, env, facts, factsPath, syncRun };
}

const invokedDirectly =
  process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname);

if (invokedDirectly) {
  const result = seed();
  console.log(JSON.stringify(result.facts, null, 2));
  console.log(`[e2e seed] left in place for inspection: ${result.tmpDir}`);
}
