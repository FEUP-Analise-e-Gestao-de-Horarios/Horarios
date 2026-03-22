function normalize(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/**
 * Returns true if every character in `query` appears in `target` in order,
 * but not necessarily consecutively. Case- and accent-insensitive.
 * e.g. matchesSequence("l.eic", "leic") → true
 *      matchesSequence("Computação", "computacao") → true
 */
export function matchesSequence(target: string, query: string): boolean {
  if (!query) return true;
  const t = normalize(target);
  const q = normalize(query);
  let qi = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++;
  }
  return qi === q.length;
}
