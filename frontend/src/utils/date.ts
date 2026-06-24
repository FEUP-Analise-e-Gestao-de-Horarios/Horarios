import type { WeekBlockResponse } from "@/types/project/sessions";

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

export function findWeekBlockIndex(blocks: WeekBlockResponse[], targetWeek: string | null): number {
  if (!targetWeek) return -1;
  return blocks.findIndex((block) => block.weeks.includes(targetWeek));
}
