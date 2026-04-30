// ─── Types ────────────────────────────────────────────────────────────────────

export type UUID = string;

export interface YearOption {
  year_id: UUID;
  year_number: number;
}

export interface DegreeOption {
  id: UUID;
  name: string;
  acronym: string;
  years: YearOption[] | number;
}

export interface ParallelCandidateSession {
  original_block_id: UUID;
  class_codes: string[];
}

export interface ParallelCandidate {
  id: UUID;
  candidate_group_id?: UUID;
  subject_name?: string;
  session_start_time?: number;
  session_weekday?: string;
  session_duration?: number;
  session_week?: string;
  sessions?: ParallelCandidateSession[];
  year?: number;
  degree_id?: string;
  degree_acronym?: string;
}

export interface SuccessResponse<T> {
  message: string;
  data: T;
}

// ─── Utilities ────────────────────────────────────────────────────────────────

export function formatTime(t: number): string {
  const s = String(t).padStart(4, "0");
  return `${s.slice(0, 2)}:${s.slice(2)}`;
}

export function normalizeYears(years: DegreeOption["years"]): YearOption[] {
  if (Array.isArray(years)) return years;
  return Array.from({ length: years }, (_, i) => ({
    year_id: `${i + 1}`,
    year_number: i + 1,
  }));
}

export function getSessionClassCodes(candidate: ParallelCandidate): string[][] {
  return (candidate.sessions ?? []).map((s) => s.class_codes);
}

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}
