import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { computeDistribution } from "@/utils/distribution";
import { WEEKDAY_LABELS_UPPER } from "@/utils/weekdays";
import type { WeekGridEvent } from "./WeekGrid";

interface DistributionModalProps {
  open: boolean;
  onClose: () => void;
  /** The events currently shown in the grid; the table mirrors the filters. */
  events: WeekGridEvent[];
}

/**
 * Draggable floating panel with the distribution table (PI ToDo #3): one row
 * per UC; each weekday is split into a sub-column per class type holding its
 * distinct-session count. Computed client-side from the already-filtered events,
 * so it mirrors the current filters. Grab the header to move it; the Fechar
 * button sits in the top-left corner.
 */
export default function DistributionModal({ open, onClose, events }: DistributionModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const theadRef = useRef<HTMLTableSectionElement>(null);
  const rowRef = useRef<HTMLTableRowElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [maxBodyHeight, setMaxBodyHeight] = useState<number | null>(null);

  const distribution = useMemo(() => computeDistribution(events), [events]);
  const rowCount = distribution.rows.length;

  // Cap the scroll area at the header + 5 rows; the rest scrolls (PI ToDo #3).
  useLayoutEffect(() => {
    if (!open) return;
    const head = theadRef.current;
    const row = rowRef.current;
    if (!head || !row || rowCount <= 5) {
      setMaxBodyHeight(null);
      return;
    }
    setMaxBodyHeight(head.offsetHeight + row.offsetHeight * 5 + 2);
  }, [open, rowCount]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const startDrag = (event: React.PointerEvent) => {
    const panel = panelRef.current;
    if (!panel) return;
    const rect = panel.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const offsetY = event.clientY - rect.top;
    const move = (moveEvent: PointerEvent) => {
      setPos({
        x: Math.max(0, Math.min(window.innerWidth - rect.width, moveEvent.clientX - offsetX)),
        y: Math.max(0, Math.min(window.innerHeight - 28, moveEvent.clientY - offsetY)),
      });
    };
    const up = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  };

  const closeButton = (
    <button
      type="button"
      onClick={onClose}
      onPointerDown={(event) => event.stopPropagation()}
      className="rounded border border-[#e5e4e7] bg-white px-1.5 py-0.5 text-xs text-[#6b6375] hover:text-[#08060d]"
    >
      Fechar
    </button>
  );

  const { weekdays, typesByDay, rows } = distribution;
  const headCell = "px-2 py-0.5 text-center font-semibold border-l border-[#e5e4e7]";

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-label="Distribuição"
      className="fixed z-50 flex max-h-[80vh] max-w-[92vw] flex-col overflow-hidden rounded-lg border border-[#e5e4e7] bg-white shadow-2xl"
      style={
        pos
          ? { left: pos.x, top: pos.y }
          : { left: "50%", top: "4rem", transform: "translateX(-50%)" }
      }
    >
      {rows.length === 0 ? (
        <div className="flex items-center gap-4 px-3 py-2">
          {closeButton}
          <span className="text-sm text-[#6b6375]">Sem eventos para mostrar.</span>
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="overflow-auto"
          style={{ maxHeight: maxBodyHeight ?? undefined }}
        >
          <table className="border-collapse text-sm">
            <thead
              ref={theadRef}
              onPointerDown={startDrag}
              className="sticky top-0 z-10 cursor-move select-none bg-white text-[11px] uppercase tracking-wide text-[#6b6375] [&_th]:bg-white"
            >
              <tr className="border-b border-[#e5e4e7]">
                <th className="sticky left-0 z-20 bg-white border-r border-[#e5e4e7] px-2 py-1 text-left">
                  {closeButton}
                </th>
                {weekdays.map((weekday) => (
                  <th key={weekday} colSpan={typesByDay[weekday].length} className={headCell}>
                    {WEEKDAY_LABELS_UPPER[weekday]}
                  </th>
                ))}
              </tr>
              <tr className="border-b border-[#e5e4e7]">
                <th className="sticky left-0 z-20 bg-white border-r border-[#e5e4e7] px-2 py-0.5 text-left font-semibold">
                  UC
                </th>
                {weekdays.flatMap((weekday) =>
                  typesByDay[weekday].map((type, index) => (
                    <th
                      key={`${weekday}-${type}`}
                      className={`px-2 py-0.5 text-center font-medium ${
                        index === 0 ? "border-l border-[#e5e4e7]" : ""
                      }`}
                    >
                      {type}
                    </th>
                  )),
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr
                  key={row.acronym}
                  ref={rowIndex === 0 ? rowRef : undefined}
                  className="border-b border-[#f0eeeb] text-[#08060d]"
                >
                  <td
                    className="sticky left-0 bg-white border-r border-[#f0eeeb] px-2 py-0.5 text-left font-semibold"
                    title={row.name}
                  >
                    {row.acronym}
                  </td>
                  {weekdays.flatMap((weekday) =>
                    typesByDay[weekday].map((type, index) => {
                      const count = row.perDay[weekday][type];
                      return (
                        <td
                          key={`${weekday}-${type}`}
                          className={`px-2 py-0.5 text-center tabular-nums ${
                            index === 0 ? "border-l border-[#f0eeeb]" : ""
                          } ${count ? "" : "text-[#cbc9d1]"}`}
                        >
                          {count ?? ""}
                        </td>
                      );
                    }),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
