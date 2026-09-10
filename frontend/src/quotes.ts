export interface Quote {
  text: string;
  author: string;
}

/** Short, work-themed lines to greet whoever opens UniOps, each with its
 * commonly cited author. Keep this list at 4-5 entries — it is read once
 * per session, not browsed. */
export const DAILY_QUOTES: Quote[] = [
  { text: "The way to get started is to quit talking and begin doing.", author: "Walt Disney" },
  { text: "Well done is better than well said.", author: "Benjamin Franklin" },
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
  { text: "Success is the sum of small efforts, repeated day in and day out.", author: "Robert Collier" },
  {
    text: "Do the best you can until you know better. Then when you know better, do better.",
    author: "Maya Angelou",
  },
];

/**
 * Same quote for everyone all day, cycling by day-of-year, so the loading
 * screen reads as a deliberate "quote of the day" rather than a random
 * flicker on every reload.
 */
export function quoteOfTheDay(date: Date = new Date()): Quote {
  const startOfYear = Date.UTC(date.getUTCFullYear(), 0, 1);
  const startOfDay = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  const dayOfYear = Math.round((startOfDay - startOfYear) / 86_400_000);
  return DAILY_QUOTES[dayOfYear % DAILY_QUOTES.length];
}
