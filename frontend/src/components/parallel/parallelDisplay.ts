import type { ParallelCandidateGraph } from "@/types/parallelSessions";

export const DAY_CONFIG: Record<string, { short: string; bg: string; text: string }> = {
  monday: { short: "SEG", bg: "bg-blue-500", text: "text-white" },
  tuesday: { short: "TER", bg: "bg-emerald-500", text: "text-white" },
  wednesday: { short: "QUA", bg: "bg-violet-500", text: "text-white" },
  thursday: { short: "QUI", bg: "bg-orange-500", text: "text-white" },
  friday: { short: "SEX", bg: "bg-rose-500", text: "text-white" },
  saturday: { short: "SAB", bg: "bg-gray-500", text: "text-white" },
};

export const SESSION_TYPE_CONFIG: Record<string, { bg: string; text: string }> = {
  TP: { bg: "bg-blue-100", text: "text-blue-700" },
  OT: { bg: "bg-violet-100", text: "text-violet-700" },
  PL: { bg: "bg-emerald-100", text: "text-emerald-700" },
  T: { bg: "bg-orange-100", text: "text-orange-700" },
  S: { bg: "bg-rose-100", text: "text-rose-700" },
};
const SESSION_TYPE_DEFAULT = { bg: "bg-gray-100", text: "text-gray-600" };

/** Stable empty selection so graph panels keep a referentially-stable prop. */
export const EMPTY_SELECTION: Set<string> = new Set();

export function sessionTypeStyle(type: string): { bg: string; text: string } {
  return SESSION_TYPE_CONFIG[type] ?? SESSION_TYPE_DEFAULT;
}

export function dayConfig(weekday: string) {
  return DAY_CONFIG[weekday] ?? { short: "?", bg: "bg-gray-400", text: "text-white" };
}

export function formatTime(t: number): string {
  const s = String(t).padStart(4, "0");
  return `${s.slice(0, 2)}:${s.slice(2)}`;
}

export function graphStartTime(graph: ParallelCandidateGraph): number {
  return graph.nodes[0]?.session.start_time ?? 0;
}
