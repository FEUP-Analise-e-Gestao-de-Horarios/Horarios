import type { ParallelBlockNode } from "@/types/parallelSessions";

/** Format an ISO date (YYYY-MM-DD) as DD/MM. */
export function formatWeek(dateStr: string): string {
  const parts = dateStr.split("-");
  return parts.length === 3 ? `${parts[2]}/${parts[1]}` : dateStr;
}

/** A week span, e.g. "15/09" or "15/09–20/12". */
export function weekSpanLabel(first: string, last: string): string {
  const a = formatWeek(first);
  const b = formatWeek(last);
  return a === b ? a : `${a}–${b}`;
}

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
/** Hard cap on grid length, guards against malformed date ranges. */
const MAX_WEEKS = 60;

/**
 * Every teaching week a candidate spans: ISO dates from the earliest
 * `first_week` to the latest `last_week`, stepping 7 days. All of a candidate's
 * blocks share the same weekday, so edge collision weeks land exactly on this
 * grid.
 */
export function weekGrid(nodes: Pick<ParallelBlockNode, "first_week" | "last_week">[]): string[] {
  let min: string | null = null;
  let max: string | null = null;
  for (const n of nodes) {
    if (!min || n.first_week < min) min = n.first_week;
    if (!max || n.last_week > max) max = n.last_week;
  }
  if (!min || !max) return [];
  const start = Date.parse(`${min}T00:00:00Z`);
  const end = Date.parse(`${max}T00:00:00Z`);
  if (Number.isNaN(start) || Number.isNaN(end)) return [];
  const grid: string[] = [];
  for (let t = start; t <= end && grid.length < MAX_WEEKS; t += WEEK_MS) {
    grid.push(new Date(t).toISOString().slice(0, 10));
  }
  return grid;
}
