import { useMemo } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hasHighlightedSession } from "@/utils/exporter/dashboardNavigation";

export interface WeekGridEvent {
  id: string;
  weekday: Weekday;
  startTime: number;
  duration: number;
  title?: string;
  body?: string[];
  type?: string;
}

export interface WeekGridMark {
  id: string;
  weekday: Weekday;
  time: number;
}

interface WeekGridProps {
  events: WeekGridEvent[];
  marks?: WeekGridMark[];
  startTime?: number;
  endTime?: number;
  onEventClick?: (event: WeekGridEvent) => void;
  emptyMessage?: string;
  highlightedEventIds?: Set<string>;
}

const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

const DEFAULT_START_HHMM = 800;
const DEFAULT_END_HHMM = 2000;
const SLOT_MINUTES = 30;
const MIN_SLOT_PX = 16;
const MAX_SLOT_PX = 36;
const HEADER_PX = 40;

function hhmmToMinutes(hhmm: number): number {
  const h = Math.floor(hhmm / 100);
  const m = hhmm % 100;
  return h * 60 + m;
}

function minutesToLabel(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

function weekdayIndex(weekday: Weekday): number {
  return WEEKDAYS.indexOf(weekday);
}

const TYPE_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  T: { bg: "bg-blue-100", border: "border-blue-300", text: "text-blue-900" },
  TP: { bg: "bg-emerald-100", border: "border-emerald-300", text: "text-emerald-900" },
  PL: { bg: "bg-amber-100", border: "border-amber-300", text: "text-amber-900" },
  P: { bg: "bg-purple-100", border: "border-purple-300", text: "text-purple-900" },
  S: { bg: "bg-pink-100", border: "border-pink-300", text: "text-pink-900" },
  OT: { bg: "bg-slate-100", border: "border-slate-300", text: "text-slate-900" },
  TC: { bg: "bg-cyan-100", border: "border-cyan-300", text: "text-cyan-900" },
};
const DEFAULT_STYLE = {
  bg: "bg-slate-100",
  border: "border-slate-300",
  text: "text-slate-900",
};

function styleForType(type: string | undefined) {
  if (!type) return DEFAULT_STYLE;
  return TYPE_STYLES[type.toUpperCase()] ?? DEFAULT_STYLE;
}

export default function WeekGrid({
  events,
  marks = [],
  startTime,
  endTime,
  onEventClick,
  emptyMessage,
  highlightedEventIds,
}: WeekGridProps) {
  const { gridStartMinutes, slotCount } = useMemo(() => {
    let min = hhmmToMinutes(startTime ?? DEFAULT_START_HHMM);
    let max = hhmmToMinutes(endTime ?? DEFAULT_END_HHMM);

    if (startTime === undefined || endTime === undefined) {
      for (const ev of events) {
        const start = hhmmToMinutes(ev.startTime);
        const end = start + ev.duration * SLOT_MINUTES;
        if (startTime === undefined && start < min) min = Math.floor(start / 60) * 60;
        if (endTime === undefined && end > max) max = Math.ceil(end / 60) * 60;
      }
      for (const m of marks) {
        const t = hhmmToMinutes(m.time);
        if (startTime === undefined && t < min) min = Math.floor(t / 60) * 60;
        if (endTime === undefined && t + SLOT_MINUTES > max)
          max = Math.ceil((t + SLOT_MINUTES) / 60) * 60;
      }
    }

    const count = (max - min) / SLOT_MINUTES;
    return { gridStartMinutes: min, slotCount: Math.max(count, 1) };
  }, [events, marks, startTime, endTime]);

  const placedEvents = useMemo(() => {
    const raw = events
      .map((ev) => {
        const col = weekdayIndex(ev.weekday);
        if (col < 0) return null;
        const startMin = hhmmToMinutes(ev.startTime);
        const rowStart = Math.round((startMin - gridStartMinutes) / SLOT_MINUTES);
        if (rowStart < 0 || rowStart >= slotCount) return null;
        const span = Math.min(ev.duration, slotCount - rowStart);
        return { ev, col, rowStart, span };
      })
      .filter(<T,>(x: T | null): x is T => x !== null);

    // Assign lanes per weekday: parallel events in the same day sit
    // side-by-side instead of stacking. Collision "clusters" are
    // maximal runs of transitively-overlapping events; every event in
    // a cluster shares the same laneCount so their widths line up.
    type Raw = (typeof raw)[number];
    type Placed = Raw & { lane: number; laneCount: number };

    const byDay = new Map<number, Raw[]>();
    for (const p of raw) {
      const list = byDay.get(p.col) ?? [];
      list.push(p);
      byDay.set(p.col, list);
    }

    const result: Placed[] = [];
    for (const dayEvents of byDay.values()) {
      dayEvents.sort(
        (a, b) => a.rowStart - b.rowStart || b.span - a.span || a.ev.id.localeCompare(b.ev.id),
      );

      let cluster: Array<Raw & { lane: number }> = [];
      let clusterEnd = -Infinity;

      const flush = () => {
        if (cluster.length === 0) return;
        const laneCount = cluster.reduce((m, e) => Math.max(m, e.lane + 1), 0);
        for (const e of cluster) result.push({ ...e, laneCount });
        cluster = [];
        clusterEnd = -Infinity;
      };

      for (const ev of dayEvents) {
        if (ev.rowStart >= clusterEnd) flush();

        const usedLanes = new Set<number>();
        for (const e of cluster) {
          if (e.rowStart + e.span > ev.rowStart) usedLanes.add(e.lane);
        }
        let lane = 0;
        while (usedLanes.has(lane)) lane++;

        cluster.push({ ...ev, lane });
        clusterEnd = Math.max(clusterEnd, ev.rowStart + ev.span);
      }
      flush();
    }

    return result;
  }, [events, gridStartMinutes, slotCount]);

  const placedMarks = useMemo(
    () =>
      marks
        .map((m) => {
          const col = weekdayIndex(m.weekday);
          if (col < 0) return null;
          const rowStart = Math.round((hhmmToMinutes(m.time) - gridStartMinutes) / SLOT_MINUTES);
          if (rowStart < 0 || rowStart >= slotCount) return null;
          return { mark: m, col, rowStart };
        })
        .filter(<T,>(x: T | null): x is T => x !== null),
    [marks, gridStartMinutes, slotCount],
  );

  if (events.length === 0 && marks.length === 0 && emptyMessage) {
    return (
      <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 text-center text-sm text-[#6b6375]">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div
      className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-y-auto h-full"
      style={{ maxHeight: slotCount * MAX_SLOT_PX + HEADER_PX }}
    >
      <div
        className="grid h-full"
        style={{
          gridTemplateColumns: `56px repeat(${WEEKDAYS.length}, minmax(0, 1fr))`,
          gridTemplateRows: `${HEADER_PX}px repeat(${slotCount}, minmax(${MIN_SLOT_PX}px, 1fr))`,
        }}
      >
        <div
          className="sticky top-0 z-20 border-b border-r border-[#e5e4e7] bg-[#f9f7f4]"
          style={{ gridColumn: 1, gridRow: 1 }}
        />
        {WEEKDAY_LABELS.map((label, i) => (
          <div
            key={label}
            className="sticky top-0 z-20 border-b border-[#e5e4e7] bg-[#f9f7f4] px-2 py-2 text-center text-xs font-semibold uppercase tracking-wider text-[#08060d]"
            style={{ gridColumn: i + 2, gridRow: 1 }}
          >
            {label}
          </div>
        ))}

        {Array.from({ length: slotCount }).map((_, i) => {
          const mins = gridStartMinutes + i * SLOT_MINUTES;
          const isHour = mins % 60 === 0;
          return (
            <div
              key={`t-${i}`}
              className={`border-r border-[#e5e4e7] px-2 text-right text-[10px] text-[#6b6375] ${
                isHour ? "border-t" : ""
              }`}
              style={{ gridColumn: 1, gridRow: i + 2 }}
            >
              {isHour ? minutesToLabel(mins) : ""}
            </div>
          );
        })}

        {Array.from({ length: slotCount }).map((_, i) =>
          WEEKDAYS.map((_d, col) => {
            const mins = gridStartMinutes + i * SLOT_MINUTES;
            const isHour = mins % 60 === 0;
            return (
              <div
                key={`c-${i}-${col}`}
                className={`border-r border-[#e5e4e7] ${isHour ? "border-t" : ""} ${
                  col === WEEKDAYS.length - 1 ? "border-r-0" : ""
                }`}
                style={{ gridColumn: col + 2, gridRow: i + 2 }}
              />
            );
          }),
        )}

        {placedMarks.map(({ mark, col, rowStart }) => (
          <div
            key={`m-${mark.id}`}
            className="bg-red-100/70 border-l-2 border-red-400 pointer-events-none"
            style={{ gridColumn: col + 2, gridRow: rowStart + 2 }}
            title="Bloco Vermelho"
          />
        ))}

        {placedEvents.map(({ ev, col, rowStart, span, lane, laneCount }) => {
          const style = styleForType(ev.type);
          const clickable = !!onEventClick;
          const isHighlighted = highlightedEventIds
            ? hasHighlightedSession(ev.id, highlightedEventIds)
            : false;
          return (
            <button
              key={`e-${ev.id}`}
              type="button"
              data-copy-id={ev.id}
              data-copy-label="ID da sessão"
              onClick={clickable ? (e) => !e.altKey && onEventClick(ev) : undefined}
              className={`relative my-[1px] rounded border text-left text-[11px] leading-tight overflow-hidden ${
                isHighlighted
                  ? "z-10 animate-pulse border-red-700 bg-red-100 text-red-950 shadow-[0_0_0_2px_rgba(220,38,38,0.75)]"
                  : `${style.bg} ${style.border} ${style.text}`
              } ${clickable ? "cursor-pointer hover:brightness-95 transition" : "cursor-default"}`}
              style={{
                gridColumn: col + 2,
                gridRow: `${rowStart + 2} / span ${span}`,
                justifySelf: "start",
                width: `calc(100% / ${laneCount})`,
                marginLeft: `calc(100% * ${lane} / ${laneCount})`,
              }}
              title={ev.title}
              disabled={!clickable}
            >
              {ev.type && (
                <div className="absolute top-1 right-1.5 z-10 text-[10px] opacity-70 uppercase leading-none">
                  {ev.type}
                </div>
              )}
              <div
                className="absolute inset-0 overflow-hidden px-1.5 py-1 pr-6"
                style={{
                  maskImage:
                    "linear-gradient(to bottom, black calc(100% - 3px), rgba(0,0,0,0.2) calc(100% - 1px), transparent 100%)",
                  WebkitMaskImage:
                    "linear-gradient(to bottom, black calc(100% - 3px), rgba(0,0,0,0.2) calc(100% - 1px), transparent 100%)",
                }}
              >
                {ev.title && <div className="font-semibold truncate">{ev.title}</div>}
                {ev.body?.map((line, i) => (
                  <div key={i} className="truncate opacity-80">
                    {line}
                  </div>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
