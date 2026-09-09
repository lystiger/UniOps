/**
 * The single source of truth for the harness's throwaway identifiers.
 *
 * Imported by both the Node seeding scripts (.mjs) and the specs (.ts), so a
 * password or port only ever has to change in one place.
 *
 * These credentials are fake and only ever exist inside a temp SQLite database
 * created by the harness. No real credential belongs in this file.
 */
export const E2E_USERNAME = "e2e-office";
export const E2E_PASSWORD = "e2e-throwaway-passphrase";
export const E2E_ROLE = "office";

export const E2E_PORT = Number(process.env.UNIOPS_E2E_PORT ?? 8931);
export const BASE_URL = `http://127.0.0.1:${E2E_PORT}`;
