/**
 * What a spec needs to know about the world the harness seeded.
 *
 * The credentials come from `constants.mjs`, which the Node seeding scripts use
 * too, so they can never drift apart. The rest is written out by the seed at
 * boot and read back here.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export { BASE_URL, E2E_PASSWORD, E2E_PORT, E2E_ROLE, E2E_USERNAME } from "./constants.mjs";

const E2E_DIR = path.dirname(fileURLToPath(import.meta.url));

/** Everything the seed derived from backend/tests/fixtures/easybooks_bundle.json. */
export type SeededFacts = {
  database_path: string;
  customer_id: string;
  customer_name: string;
  customer_code: string;
  product_id: string;
  product_code: string;
  order_id: string;
  order_number: string;
  order_status: string;
  order_date: string;
  required_date: string;
  order_total: string;
  line_quantity: string;
  line_unit_price: string;
  invoice_source_id: string;
  invoice_number: string;
  invoice_series: string;
  invoice_date: string;
  invoice_subtotal: string;
  invoice_total: string;
  candidate_confidence: string;
};

export function readSeededFacts(): SeededFacts {
  const factsPath = path.join(E2E_DIR, ".facts.json");
  if (!fs.existsSync(factsPath)) {
    throw new Error(
      `${factsPath} is missing. It is written by e2e/serve.mjs; run the suite through Playwright.`,
    );
  }
  return JSON.parse(fs.readFileSync(factsPath, "utf8")) as SeededFacts;
}
