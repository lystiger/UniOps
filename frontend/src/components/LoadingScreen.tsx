import { quoteOfTheDay } from "../quotes";

/**
 * Shown while the app verifies the session cookie on load. Purely
 * decorative — no props, no state — so it stays cheap even though it
 * animates; `prefers-reduced-motion` (global rule in styles.css) turns
 * every animation here off.
 */
export function LoadingScreen() {
  const quote = quoteOfTheDay();

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
          Verifying your session…
        </p>
      </div>

      <blockquote className="loading-quote">
        <p>&ldquo;{quote.text}&rdquo;</p>
        <cite>— {quote.author}</cite>
      </blockquote>
    </div>
  );
}
