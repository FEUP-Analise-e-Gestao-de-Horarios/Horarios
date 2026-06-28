import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { EmptyState } from "@/components/exporter/ExportSection";
import type { ExportConflictBase } from "@/types/exporter";
import { conflictAulasCount } from "@/utils/exporter/conflicts";
import { formatTime, WEEKDAY_LABELS } from "@/utils/exporter/formatters";

function formatConflictWeeks(row: ExportConflictBase): string {
  const weeks = row.weeks?.length ? [...new Set(row.weeks)] : [row.week];
  if (weeks.length === 1) return weeks[0] ?? row.week;
  return `${weeks[0]} a ${weeks[weeks.length - 1]}`;
}

function conflictTitle(row: ExportConflictBase, name: string): ReactNode {
  if (!row.subject_labels?.length) return name;

  return (
    <>
      <span>{name}</span>
      <span className="font-normal text-[#6b6375]"> · {row.subject_labels.join(", ")}</span>
    </>
  );
}

export default function ConflictRows<T extends ExportConflictBase>({
  rows,
  getName,
  getHref,
  getAnchorId,
  highlightedAnchor,
  onCardClick,
}: {
  rows: T[];
  getName: (row: T) => string;
  getHref: (row: T) => string;
  getAnchorId: (row: T, index: number) => string;
  highlightedAnchor: string | null;
  onCardClick: (anchorId: string) => void;
}) {
  if (!rows.length) return <EmptyState>Sem conflitos.</EmptyState>;

  return (
    <div className="divide-y divide-[#e5e4e7]">
      {rows.map((row, index) => {
        const anchor = getAnchorId(row, index);
        const isHighlighted = highlightedAnchor === anchor;
        return (
          <Link
            id={anchor}
            key={`${getName(row)}-${row.week}-${row.weekday}-${row.start_time}-${index}`}
            to={getHref(row)}
            aria-label={`Ver horário do conflito de ${getName(row)}`}
            onClick={() => onCardClick(anchor)}
            className={`group relative block scroll-mt-4 cursor-pointer px-4 py-3 pr-32 text-left transition-colors hover:bg-[#fff8f4] focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8c2d19] focus-visible:ring-inset sm:pr-28 ${
              isHighlighted ? "bg-amber-50 ring-2 ring-inset ring-amber-400" : ""
            }`}
          >
            {isHighlighted ? (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 z-0 animate-pulse bg-amber-300/50"
              />
            ) : null}
            <span className="absolute right-4 top-3 z-20 whitespace-nowrap rounded border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700 transition-colors group-hover:border-red-300 group-hover:bg-red-100">
              {conflictAulasCount(row)} aulas
            </span>
            <div className="relative z-10">
              <div className="min-w-0">
                <span className="min-w-0 break-words text-sm font-semibold text-[#08060d] transition-colors group-hover:text-[#8c2d19]">
                  {conflictTitle(row, getName(row))}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#6b6375]">
                <span>{formatConflictWeeks(row)}</span>
                <span>{WEEKDAY_LABELS[row.weekday]}</span>
                <span>{formatTime(row.start_time)}</span>
              </div>
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-[#8c2d19] opacity-80 transition-opacity group-hover:opacity-100">
                Ver horário
                <ArrowUpRight size={12} aria-hidden="true" />
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
