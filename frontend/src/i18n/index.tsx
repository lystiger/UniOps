import React, { createContext, useContext, useEffect, useState } from "react";
import { en } from "./en";
import type { Dictionary, Locale } from "./types";
import { vi } from "./vi";

const STORAGE_KEY = "uniops.locale";
const DEFAULT_LOCALE: Locale = "vi";

const DICTIONARIES: Record<Locale, Dictionary> = {
  vi,
  en,
};

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Dictionary;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

function getInitialLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "vi" || saved === "en") {
      return saved;
    }
  } catch {
    // localStorage might be disabled / inaccessible
  }
  return DEFAULT_LOCALE;
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale);

  const setLocale = (next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value: LocaleContextValue = {
    locale,
    setLocale,
    t: DICTIONARIES[locale],
  };

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): { locale: Locale; setLocale: (locale: Locale) => void } {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    // Fallback if rendered outside provider in isolated tests
    const loc = getInitialLocale();
    return {
      locale: loc,
      setLocale: (next: Locale) => {
        try {
          localStorage.setItem(STORAGE_KEY, next);
        } catch {
          // ignore
        }
      },
    };
  }
  return { locale: ctx.locale, setLocale: ctx.setLocale };
}

export function useT(): Dictionary {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    // Fallback if rendered outside provider in isolated tests
    return DICTIONARIES[getInitialLocale()];
  }
  return ctx.t;
}

export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  const t = useT();

  return (
    <div className={`language-switcher ${className ?? ""}`} role="group" aria-label={t.auth.language}>
      <button
        type="button"
        className={`lang-btn ${locale === "vi" ? "active" : ""}`}
        onClick={() => setLocale("vi")}
        aria-pressed={locale === "vi"}
      >
        Tiếng Việt
      </button>
      <span className="lang-separator" aria-hidden="true">|</span>
      <button
        type="button"
        className={`lang-btn ${locale === "en" ? "active" : ""}`}
        onClick={() => setLocale("en")}
        aria-pressed={locale === "en"}
      >
        English
      </button>
    </div>
  );
}

export { en } from "./en";
export type { Dictionary, Locale } from "./types";
export { vi } from "./vi";
