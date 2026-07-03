import { useEffect, useState } from "react";
import type { GroupView } from "@/api/hooks/useParallelSessions";
import { dayConfig, formatTime, sessionTypeStyle } from "./parallelDisplay";

/**
 * A single group card in the "Selecionadas" panel, animated by its lifecycle:
 * a freshly-created card expands in shifted right with a green rail and only
 * slides back once the server confirms; a card being deleted turns its rail red
 * and shifts right, then — once confirmed — collapses out so the others slide
 * up into its place. The outer grid drives the height collapse (enter/leave)
 * and the rightward shift; the middle wrapper carries the reveal pulse.
 */
export default function GroupCard({
  view,
  highlighted,
  onRemove,
  registerRef,
}: {
  view: GroupView;
  highlighted: boolean;
  onRemove: () => void;
  registerRef: (el: HTMLDivElement | null) => void;
}) {
  const { group, weekday, startTime, blocks } = view;
  const status = group.status;
  const day = dayConfig(weekday);

  // A freshly-created card appears in its normal place, then slides right on the
  // next frame and holds there while its create confirms. `moved` gates that
  // delay so the shift animates from rest instead of starting shifted. Two RAFs
  // ensure the browser paints the un-shifted frame before the flip.
  const [moved, setMoved] = useState(status !== "creating");
  useEffect(() => {
    if (moved) return;
    let inner = 0;
    const outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => setMoved(true));
    });
    return () => {
      cancelAnimationFrame(outer);
      cancelAnimationFrame(inner);
    };
  }, [moved]);

  // Pending cards (create confirming or delete confirming) hold shifted to the
  // right; a settled "saved" card — and a confirmed-deleted card releasing on
  // its way out — sit flush.
  const shifted = status === "deleting" || (status === "creating" && moved);
  // A confirmed-deleted card releases the shift, fades, and collapses its row so
  // the others slide up into its place.
  const open = status !== "leaving";
  const leaving = status === "leaving";

  const borderColor =
    status === "deleting"
      ? "border-red-400"
      : status === "creating"
        ? "border-emerald-300"
        : "border-[#e4e4e4]";
  const railColor =
    status === "deleting"
      ? "bg-red-400"
      : status === "creating"
        ? "bg-emerald-400"
        : "bg-[#c8c8c8]";
  // One-shot glow that plays when the card enters its pending state.
  const glow = highlighted
    ? "parallel-group-pulse"
    : status === "creating"
      ? "parallel-group-added"
      : status === "deleting"
        ? "parallel-group-removing"
        : "";

  return (
    <div
      ref={registerRef}
      className={`grid transition-all ease-out ${leaving ? "duration-500" : "duration-300"} ${
        open ? "grid-rows-[1fr] opacity-100 mb-1.5" : "grid-rows-[0fr] opacity-0 mb-0"
      } ${shifted ? "translate-x-4" : "translate-x-0"}`}
    >
      <div className={`min-h-0 overflow-hidden rounded-lg ${glow}`}>
        <div
          className={`flex items-stretch overflow-hidden rounded-lg border bg-white transition-colors duration-300 ${borderColor}`}
        >
          <div className={`w-1 shrink-0 transition-colors duration-300 ${railColor}`} />
          <div className="flex-1 min-w-0 px-2.5 py-2">
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className={`text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded ${day.bg} ${day.text}`}
              >
                {day.short}
              </span>
              <span className="text-[12px] font-bold tabular-nums text-[#333]">
                {formatTime(startTime)}
              </span>
              <button
                onClick={onRemove}
                className="ml-auto flex items-center justify-center w-5 h-5 rounded text-[#bbb] hover:bg-red-50 hover:text-red-600 transition-colors text-sm leading-none cursor-pointer"
                title="Remover grupo"
              >
                ×
              </button>
            </div>
            <div className="flex flex-col gap-1">
              {blocks.map((block) => {
                const typeStyle = sessionTypeStyle(block.type);
                return (
                  <div key={block.blockId} className="group/codes flex items-center gap-1.5">
                    <span
                      className={`shrink-0 w-7 text-center text-[10px] font-bold px-1 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                    >
                      {block.type}
                    </span>
                    {/* Codes collapse to one line with a right-edge fade;
                        hovering the row wraps them to reveal the full list. */}
                    <div className="flex min-w-0 flex-1 flex-nowrap gap-1 overflow-hidden [mask-image:linear-gradient(to_right,black_calc(100%_-_20px),transparent)] [-webkit-mask-image:linear-gradient(to_right,black_calc(100%_-_20px),transparent)] group-hover/codes:flex-wrap group-hover/codes:overflow-visible group-hover/codes:[mask-image:none] group-hover/codes:[-webkit-mask-image:none]">
                      {block.codes.map((code) => (
                        <span
                          key={`${block.blockId}-${code}`}
                          className="shrink-0 whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200"
                        >
                          {code}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
