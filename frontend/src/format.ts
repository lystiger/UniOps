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

const quantityFormatter = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 4 });

/** A stored decimal quantity without its storage padding: "1000.0000" reads "1.000", "12.5000" reads "12,5". */
export function quantity(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? quantityFormatter.format(parsed) : String(value);
}

/** A typed day-first date as ISO `YYYY-MM-DD`: `31/12/2026`, `1/6/2026`, `.` or `-` separators, or
 * `31122026`. Null unless it names a real calendar day, so 31/02 never rolls into March. */
export function parseDisplayDate(text: string): string | null {
  const trimmed = text.trim();
  const match = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(trimmed) ?? /^(\d{2})(\d{2})(\d{4})$/.exec(trimmed);
  if (!match) return null;
  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);
  if (year < 1000 || month < 1 || month > 12 || day < 1) return null;
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
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

/** How long ago an ISO timestamp was, e.g. "3 giờ trước" or "3 hours ago". */
export function relativeTime(
  value: string | null | undefined,
  locale: "vi" | "en" = "vi",
  now: Date = new Date(),
): string {
  if (!value) return "—";
  const seconds = Math.round((new Date(value).getTime() - now.getTime()) / 1000);
  if (!Number.isFinite(seconds)) return "—";
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  const elapsed = Math.abs(seconds);
  if (elapsed < 60) return formatter.format(0, "second");
  if (elapsed < 3600) return formatter.format(Math.round(seconds / 60), "minute");
  if (elapsed < 86400) return formatter.format(Math.round(seconds / 3600), "hour");
  return formatter.format(Math.round(seconds / 86400), "day");
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
  SUCCEEDED: "success",
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
