/**
 * The branded splash belongs to a browser's first open only. Replaying a
 * full-screen animation on every reload makes a routine session check look
 * like a cold start, so later opens get a quiet pending state instead.
 */
export const SPLASH_SEEN_KEY = "uniops.splashSeen";

/** Long enough for the splash animation to settle; the quote lands at ~1.4s. */
export const SPLASH_MIN_MS = 1500;

/** Later opens stay blank this long before a session-check note appears, so a
 * fast check never flashes anything. */
export const SESSION_CHECK_NOTE_DELAY_MS = 400;

export function hasSeenSplash(): boolean {
  try {
    return localStorage.getItem(SPLASH_SEEN_KEY) !== null;
  } catch {
    // Storage unavailable: skip the splash rather than replay it on every load.
    return true;
  }
}

export function markSplashSeen(): void {
  try {
    localStorage.setItem(SPLASH_SEEN_KEY, "1");
  } catch {
    // Nothing to remember it in; hasSeenSplash() already skips in this case.
  }
}
