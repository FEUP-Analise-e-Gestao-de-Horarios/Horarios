import type { WeekBlockResponse } from "@/types/project/sessions";

/** Reformats an ISO-ish `YYYY-MM-DD` string as `DD-MM-YYYY`. */
export function formatDateLabel(value: string): string {
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${day}-${month}-${year}`;
}

/** Human label for a contiguous block of week start dates (DD-MM-YYYY). */
export function formatWeekRange(weeks: string[]): string {
  if (weeks.length === 0) return "";
  const firstWeek = formatDateLabel(weeks.at(0) ?? "");
  const lastWeek = formatDateLabel(weeks.at(-1) ?? "");
  return firstWeek === lastWeek ? firstWeek : `${firstWeek} - ${lastWeek}`;
}

/** Formats `YYYY-MM-DD` as a pt-PT short label (e.g. "5 mar."). */
export function formatShortDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (y === undefined || m === undefined || d === undefined) {
    throw new Error(`Invalid YYYY-MM-DD date: ${iso}`);
  }
  return new Date(y, m - 1, d).toLocaleDateString("pt-PT", {
    day: "2-digit",
    month: "short",
  });
}

/**
 * Dashboard-style label for a `WeekBlockResponse`: short date range + a
 * "N semanas" suffix (e.g. "5 mar. – 19 mar. · 3 semanas").
 */
export function formatBlockLabel(block: WeekBlockResponse): string {
  const first = block.weeks[0];
  const last = block.weeks[block.weeks.length - 1];
  if (!first) return "—";
  const count = block.weeks.length;
  const range =
    count === 1 || !last
      ? formatShortDate(first)
      : `${formatShortDate(first)} – ${formatShortDate(last)}`;
  const weeksLabel = count === 1 ? "1 semana" : `${count} semanas`;
  return `${range} · ${weeksLabel}`;
}
