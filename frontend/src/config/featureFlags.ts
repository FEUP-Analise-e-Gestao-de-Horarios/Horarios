/**
 * Gates for features whose backend endpoints don't exist yet (contracts C1-C3
 * agreed with the backend side). While a flag is off, the corresponding hooks
 * in `@/api/hooks/project/*` serve data from `@/api/mocks/scheduleMocks`;
 * turning it on (build-time via the VITE_* env var, or by editing the default
 * here once the endpoint ships) switches to the real endpoint with no
 * call-site changes.
 */
function envFlag(value: unknown, fallback: boolean): boolean {
  if (value === undefined) return fallback;
  return value === "true" || value === "1" || value === true;
}

export const FLAGS = {
  /** C1 — PATCH /api/projects/<pid>/sessions/<sid>/ */
  sessionMutations: envFlag(import.meta.env.VITE_FLAG_SESSION_MUTATIONS, false),
  /** C2/C3 — GET conflicts + conflict ignore endpoints */
  conflictsApi: envFlag(import.meta.env.VITE_FLAG_CONFLICTS_API, false),
} as const;
