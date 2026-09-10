import { useEffect, useState } from "react";
import { UnauthorizedError } from "./api";

export interface AsyncResource<T> {
  data: T | null;
  /** Empty once a fetch has resolved successfully, regardless of `data`. */
  error: string;
  /** True only until the first fetch settles. A stale table should not
   * disappear behind a spinner every time a filter changes. */
  loading: boolean;
  /** True for the duration of any fetch, first load or refetch. */
  fetching: boolean;
}

/**
 * One data section's request lifecycle: loading, error, or data — with a 401
 * routed back to sign-in exactly like the rest of the app, and the previous
 * result kept on screen while a refetch (e.g. a changed date filter) is in
 * flight, so the layout does not collapse and rebuild on every change.
 */
export function useApiResource<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
  onSessionLost: () => void,
): AsyncResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    let alive = true;
    setFetching(true);
    fetcher()
      .then((result) => {
        if (!alive) return;
        setData(result);
        setError("");
      })
      .catch((reason) => {
        if (!alive) return;
        if (reason instanceof UnauthorizedError) {
          onSessionLost();
          return;
        }
        setError(reason instanceof Error ? reason.message : "Could not load data");
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
        setFetching(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, fetching };
}
