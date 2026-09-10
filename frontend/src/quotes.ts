export interface Quote {
  text: string;
  author: string;
}

/** Short, work-themed lines to greet whoever opens UniOps in English. */
export const DAILY_QUOTES_EN: Quote[] = [
  { text: "The way to get started is to quit talking and begin doing.", author: "Walt Disney" },
  { text: "Well done is better than well said.", author: "Benjamin Franklin" },
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
  { text: "Success is the sum of small efforts, repeated day in and day out.", author: "Robert Collier" },
  {
    text: "Do the best you can until you know better. Then when you know better, do better.",
    author: "Maya Angelou",
  },
];

/** Commonly known Vietnamese proverbs about work and diligence, attributed as "Tục ngữ". */
export const DAILY_QUOTES_VI: Quote[] = [
  { text: "Có công mài sắt, có ngày nên kim.", author: "Tục ngữ" },
  { text: "Vạn sự khởi đầu nan, gian nan đừng nản.", author: "Tục ngữ" },
  { text: "Muốn biết phải hỏi, muốn giỏi phải học.", author: "Tục ngữ" },
  { text: "Chớ thấy sóng cả mà ngã tay chèo.", author: "Tục ngữ" },
  { text: "Cần cù bù thông minh.", author: "Tục ngữ" },
];

export const DAILY_QUOTES = DAILY_QUOTES_EN;

/**
 * Same quote for everyone all day, cycling by day-of-year, so the loading
 * screen reads as a deliberate "quote of the day" rather than a random
 * flicker on every reload.
 */
export function quoteOfTheDay(date: Date = new Date(), locale?: "vi" | "en"): Quote {
  let activeLocale = locale;
  if (!activeLocale && typeof window !== "undefined") {
    try {
      const saved = localStorage.getItem("uniops.locale");
      if (saved === "vi" || saved === "en") {
        activeLocale = saved;
      }
    } catch {
      // ignore
    }
  }
  const quotes = activeLocale === "en" ? DAILY_QUOTES_EN : DAILY_QUOTES_VI;
  const startOfYear = Date.UTC(date.getUTCFullYear(), 0, 1);
  const startOfDay = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  const dayOfYear = Math.round((startOfDay - startOfYear) / 86_400_000);
  return quotes[dayOfYear % quotes.length];
}
