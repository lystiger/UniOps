import { useEffect, useState } from "react";
import { useLocale, useT } from "../i18n";
import { quoteOfTheDay } from "../quotes";
import { SESSION_CHECK_NOTE_DELAY_MS } from "../splash";

/**
 * Covers the session check on a later open (see splash.ts). Blank at first so
 * a fast check shows nothing; a short note appears only if the check is slow.
 */
export function SessionCheckPending() {
  const t = useT();
  const [showNote, setShowNote] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setShowNote(true), SESSION_CHECK_NOTE_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="session-check-pending" role="status" aria-live="polite">
      {showNote && (
        <p className="session-check-note">
          <span className="live-dot pulse" aria-hidden="true" />
          {t.auth.verifyingSession}
        </p>
      )}
    </div>
  );
}

/**
 * The branded splash for a browser's first open (see splash.ts). Every part is
 * visible by default and its entrance animation only hides it during its own
 * delay, so `prefers-reduced-motion` (global rule in styles.css), which turns
 * the animations off, still leaves a complete, static screen.
 */
export function LoadingScreen() {
  const { locale } = useLocale();
  const t = useT();
  const quote = quoteOfTheDay(new Date(), locale);

  return (
    <div className="loading-state-screen">
      <div className="loading-hero">
        <span className="loading-logo" aria-hidden="true">
          <svg viewBox="0 0 64 64" className="brand-icon">
            <rect width="64" height="64" rx="14" fill="#176b3a" />
            <path
              className="loading-logo-cup"
              d="M18 18v20c0 9 5 14 14 14s14-5 14-14V18h-9v20c0 4-1 6-5 6s-5-2-5-6V18z"
              fill="#fff"
            />
            <path
              className="loading-logo-leaf"
              d="M32 9c7 1 11 5 12 11-7 0-11-4-12-11z"
              fill="#b9df70"
            />
          </svg>
        </span>

        <div className="loading-wordmark brand-logo-text">
          Uni<span className="brand-green-accent">-Green</span>
          <span className="brand-slash">/</span>
          <span className="brand-ops-label">OPS</span>
        </div>

        <p className="loading-status">
          <span className="live-dot pulse" aria-hidden="true" />
          {t.auth.verifyingSession}
        </p>
      </div>

      <blockquote className="loading-quote">
        <p>&ldquo;{quote.text}&rdquo;</p>
        <cite>— {quote.author}</cite>
      </blockquote>
    </div>
  );
}
