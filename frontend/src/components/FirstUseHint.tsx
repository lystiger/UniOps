import { useState } from "react";
import { useT } from "../i18n";

/**
 * One sentence, shown once, dismissed for good.
 *
 * The first pilot found that people could work the system but "cũng phải mất
 * thời gian để làm quen". This is the smallest answer to that: what UniOps
 * holds, and the one thing it does not hold — the finance figures EasyBooks
 * still owns. Not a tour, not a modal, and never shown a second time.
 */
export const FIRST_USE_HINT_KEY = "uniops.firstUseHintDismissed";

function alreadyDismissed(): boolean {
  try {
    return localStorage.getItem(FIRST_USE_HINT_KEY) !== null;
  } catch {
    // Storage unavailable: show it rather than suppress it. It costs one click.
    return false;
  }
}

export function FirstUseHint() {
  const [dismissed, setDismissed] = useState(alreadyDismissed);
  const t = useT();

  if (dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem(FIRST_USE_HINT_KEY, "1");
    } catch {
      // Nothing to remember it in; it reappears on the next open, which is
      // better than a hint that cannot be dismissed at all.
    }
  }

  return (
    // A plain div, not a labelled landmark: one dismissible sentence should not
    // add a `complementary` region to every page, and its name would collide
    // with real field labels in the accessible-name space.
    <div className="first-use-hint">
      <p>{t.firstUse.body}</p>
      <button className="secondary-button" type="button" onClick={dismiss}>
        {t.firstUse.dismiss}
      </button>
    </div>
  );
}
