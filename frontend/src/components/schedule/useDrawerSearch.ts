import { useCallback, useMemo, useState } from "react";

/**
 * Owns a drawer's search input state and exposes a `matches` helper that does
 * the case-insensitive substring check against a precomputed normalised query.
 * Lets a caller filter several lists by the same query without duplicating the
 * `.toLowerCase().trim()` on every keystroke.
 */
export function useDrawerSearch(): {
  query: string;
  setQuery: (value: string) => void;
  /** Returns true when `text` is empty-query-match or contains the query. */
  matches: (text: string) => boolean;
} {
  const [query, setQuery] = useState("");
  const normalisedQuery = useMemo(() => query.toLowerCase().trim(), [query]);
  const matches = useCallback(
    (text: string) => normalisedQuery === "" || text.toLowerCase().includes(normalisedQuery),
    [normalisedQuery],
  );
  return { query, setQuery, matches };
}
