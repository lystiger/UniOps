/** Shared vi-VN number, currency, and date formatting.
 *
 * One place, so a figure never renders differently on two pages. `money`
 * always says which currency; a bare number invites the reader to guess.
 */

const numberFormatter = new Intl.NumberFormat("vi-VN");
const dateFormatter = new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
const dateTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** A VND amount. `null`/`undefined` render as "—", never as 0. */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${numberFormatter.format(Number(value))} ₫`;
}

/** A plain count or quantity, with no currency mark. */
export function number(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return numberFormatter.format(value);
}

/** An ISO date string (`YYYY-MM-DD`) as `dd/mm/yyyy`. */
export function isoDate(value: string | null | undefined): string {
  if (!value) return "—";
  return dateFormatter.format(new Date(`${value}T00:00:00`));
}

/** An ISO timestamp as `dd/mm/yyyy hh:mm`. */
export function timestamp(value: string | null | undefined): string {
  if (!value) return "—";
  return dateTimeFormatter.format(new Date(value));
}

/** Wall-clock duration between two ISO timestamps, e.g. "2m 14s" or "2 phút 14 giây". Empty if
 * either end is missing — never guessed from a run still in progress. */
export function duration(
  start: string | null | undefined,
  end: string | null | undefined,
  locale: "vi" | "en" = "vi",
): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (locale === "vi") {
    if (minutes > 0 && seconds > 0) return `${minutes} phút ${seconds} giây`;
    if (minutes > 0) return `${minutes} phút`;
    return `${seconds} giây`;
  }
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

import type { SyncRun } from "./types";
import type { StatusTone } from "./components/primitives";

export const syncStatusTone: Record<SyncRun["status"], StatusTone> = {
  SUCCEEDED: "accepted",
  PARTIAL: "pending",
  FAILED: "rejected",
  RUNNING: "neutral",
};

export const syncStatusLabel: Record<SyncRun["status"], string> = {
  SUCCEEDED: "Success",
  PARTIAL: "Partial",
  FAILED: "Failure",
  RUNNING: "Running",
};

/** The most recent completed run and the most recent attempt of any kind. */
export function latestSyncRuns(runs: SyncRun[]): {
  lastSuccess: SyncRun | null;
  lastAttempt: SyncRun | null;
} {
  const lastAttempt = runs[0] ?? null;
  const lastSuccess = runs.find((run) => run.status === "SUCCEEDED") ?? null;
  return { lastSuccess, lastAttempt };
}

/** Today, as the `YYYY-MM-DD` shape the analytics endpoints expect. */
export function today(): string {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

/** N days before today, same shape as {@link today}. */
export function daysAgo(days: number): string {
  const value = new Date();
  value.setDate(value.getDate() - days);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}
