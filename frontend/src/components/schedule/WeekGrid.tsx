import { useMemo } from "react";
import type { Weekday } from "@/types/dashboard";

export interface WeekGridEvent {
  id: string;
  weekday: Weekday;
  startTime: number;
  duration: number;
  title?: string;
  body?: string[];
  type?: string;
  turma?: string;
  uc?: string;
  professor?: string;
  sala?: string;
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
  weekdayLabels?: string[];
  primaryHeaderLeftLabel?: string;
  secondaryHeaderLeftLabel?: string;
  secondaryHeaderValues?: string[];
  selectedTurmas?: string[];
  turmaShifts?: Record<string, number>;
  slotHeightPx?: number;
  showHalfHourLabels?: boolean;
  showHalfHourDividers?: boolean;
  includeEndSlot?: boolean;
  headerHeightPx?: number;
  hourLabelFontPx?: number;
}

const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

const DEFAULT_START_HHMM = 800;
const DEFAULT_END_HHMM = 2000;
const SLOT_MINUTES = 30;
const MIN_SLOT_PX = 16;
const MAX_SLOT_PX = 36;
const HEADER_PX = 40;
const TURMA_COLUMN_MIN_PX = 64;

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

function getTurmaHeaderStyle(shift?: number): string {
  if (shift !== undefined && shift % 2 === 0) return "bg-red-100 border-red-200 text-[#08060d]";
  return "bg-[#f9f7f4] text-[#08060d]";
}

export default function WeekGrid({
  events,
  marks = [],
  startTime,
  endTime,
  onEventClick,
  emptyMessage,
  weekdayLabels,
  primaryHeaderLeftLabel,
  secondaryHeaderLeftLabel,
  selectedTurmas = [],
  turmaShifts = {},
  slotHeightPx,
  showHalfHourLabels = false,
  showHalfHourDividers = false,
  includeEndSlot = false,
  headerHeightPx,
  hourLabelFontPx,
}: WeekGridProps) {
  const labels =
    weekdayLabels && weekdayLabels.length === WEEKDAY_LABELS.length
      ? weekdayLabels
      : WEEKDAY_LABELS;

  const activeTurmas =
    selectedTurmas.length > 0
      ? selectedTurmas
      : Array.from(new Set(events.map((e) => e.turma).filter(Boolean) as string[])).sort();
  const turmasCount = Math.max(activeTurmas.length, 1);

  const expandedSecondaryHeaderValues =
    activeTurmas.length > 0 ? WEEKDAYS.flatMap(() => activeTurmas) : [];
  const hasSecondaryHeader = expandedSecondaryHeaderValues.length > 0 && activeTurmas.length > 0;
  const headerRows = hasSecondaryHeader ? 2 : 1;
  const minSlotPx = slotHeightPx ?? MIN_SLOT_PX;
  const maxSlotPx = slotHeightPx ?? MAX_SLOT_PX;
  const headerPx = headerHeightPx ?? HEADER_PX;
  const hourFontPx = hourLabelFontPx ?? 10;

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

    const count = (max - min) / SLOT_MINUTES + (includeEndSlot ? 1 : 0);
    return { gridStartMinutes: min, slotCount: Math.max(count, 1) };
  }, [events, marks, startTime, endTime, includeEndSlot]);

  const placedEvents = useMemo(() => {
    const getMergeKey = (ev: WeekGridEvent): string => {
      return [ev.weekday, ev.startTime, ev.duration, ev.type, ev.title, ev.professor, ev.sala].join(
        "||",
      );
    };

    const mergeGroups = new Map<string, { events: WeekGridEvent[]; turmas: Set<string> }>();
    for (const ev of events) {
      if (activeTurmas.length > 0 && ev.turma && !activeTurmas.includes(ev.turma)) continue;
      const key = getMergeKey(ev);
      if (!mergeGroups.has(key)) {
        mergeGroups.set(key, { events: [], turmas: new Set() });
      }
      const group = mergeGroups.get(key)!;
      group.events.push(ev);
      if (ev.turma) group.turmas.add(ev.turma);
    }

    type PlacedEvent = {
      ev: WeekGridEvent;
      dayCol: number;
      rowStart: number;
      span: number;
      turmaIndices: number[];
      colSpan: number;
    };

    const result: PlacedEvent[] = [];
    for (const { events: groupEvents, turmas } of mergeGroups.values()) {
      if (groupEvents.length === 0) continue;
      const ev = groupEvents[0];
      if (!ev) continue;

      const dayCol = weekdayIndex(ev.weekday);
      if (dayCol < 0) continue;

      const startMin = hhmmToMinutes(ev.startTime);
      const rowStart = Math.round((startMin - gridStartMinutes) / SLOT_MINUTES);
      if (rowStart < 0 || rowStart >= slotCount) continue;

      const span = Math.min(ev.duration, slotCount - rowStart);

      const turmaIndices: number[] = [];
      for (let i = 0; i < activeTurmas.length; i++) {
        const turma = activeTurmas[i];
        if (turma && turmas.has(turma)) {
          turmaIndices.push(i);
        }
      }

      if (turmaIndices.length === 0 && activeTurmas.length > 0) {
        turmaIndices.push(0);
      }

      if (turmaIndices.length > 0) {
        result.push({
          ev,
          dayCol,
          rowStart,
          span,
          turmaIndices,
          colSpan: turmaIndices.length,
        });
      }
    }

    return result;
  }, [events, activeTurmas, gridStartMinutes, slotCount]);

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
      className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-x-auto overflow-y-auto h-full"
      style={{ maxHeight: slotCount * maxSlotPx + headerPx * headerRows }}
    >
      <div
        className="grid h-full w-max min-w-full"
        style={{
          gridTemplateColumns: `44px repeat(${WEEKDAYS.length * turmasCount}, minmax(${TURMA_COLUMN_MIN_PX}px, 1fr))`,
          gridTemplateRows: `${headerPx}px${hasSecondaryHeader ? ` ${headerPx}px` : ""} repeat(${slotCount}, minmax(${minSlotPx}px, 1fr))`,
        }}
      >
        <div
          className="sticky top-0 z-20 border-b border-r border-[#e5e4e7] bg-[#f9f7f4]"
          style={{ gridColumn: 1, gridRow: 1 }}
        >
          <div className="px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d]">
            {primaryHeaderLeftLabel ?? ""}
          </div>
        </div>
        {labels.map((label, dayIdx) => (
          <div
            key={label}
            className={`sticky top-0 z-20 border-b border-[#e5e4e7] bg-[#f9f7f4] px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d] ${
              dayIdx > 0 ? "border-l border-[#d8d5da]" : ""
            }`}
            style={{
              gridColumn: `${dayIdx * turmasCount + 2} / span ${turmasCount}`,
              gridRow: 1,
            }}
          >
            {label}
          </div>
        ))}

        {hasSecondaryHeader ? (
          <>
            <div
              className="sticky z-20 border-b border-r border-[#e5e4e7] bg-[#f9f7f4]"
              style={{ gridColumn: 1, gridRow: 2, top: headerPx }}
            >
              <div className="px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d]">
                {secondaryHeaderLeftLabel ?? ""}
              </div>
            </div>
            {WEEKDAYS.map((_, dayIdx) =>
              activeTurmas.map((turma, turmaIdx) => (
                <div
                  key={`sub-${dayIdx}-${turmaIdx}`}
                  className={`sticky z-20 border-b px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider ${getTurmaHeaderStyle(
                    turmaShifts[turma],
                  )} ${turmaIdx === 0 && dayIdx > 0 ? "border-l border-[#d8d5da]" : "border-[#e5e4e7]"}`}
                  style={{
                    gridColumn: dayIdx * turmasCount + turmaIdx + 2,
                    gridRow: 2,
                    top: headerPx,
                  }}
                >
                  {turma}
                </div>
              )),
            )}
          </>
        ) : null}

        {Array.from({ length: slotCount }).map((_, i) => {
          const mins = gridStartMinutes + i * SLOT_MINUTES;
          const isHour = mins % 60 === 0;
          const showLabel = showHalfHourLabels || isHour;
          const rowDividerClass = showHalfHourDividers
            ? "border-t border-[#e5e4e7]"
            : isHour
              ? "border-t"
              : "";
          return (
            <div
              key={`t-${i}`}
              className={`border-r border-[#e5e4e7] px-2 text-right text-[#6b6375] ${rowDividerClass}`}
              style={{
                gridColumn: 1,
                gridRow: i + headerRows + 1,
                fontSize: `${hourFontPx}px`,
              }}
            >
              {showLabel ? minutesToLabel(mins) : ""}
            </div>
          );
        })}

        {Array.from({ length: slotCount }).map((_, i) =>
          WEEKDAYS.flatMap((_, dayIdx) =>
            Array.from({ length: turmasCount }).map((_, turmaIdx) => {
              const mins = gridStartMinutes + i * SLOT_MINUTES;
              const isHour = mins % 60 === 0;
              const rowDividerClass = showHalfHourDividers
                ? "border-t border-[#e5e4e7]"
                : isHour
                  ? "border-t"
                  : "";
              const isLastTurma = turmaIdx === turmasCount - 1;
              const isLastDay = dayIdx === WEEKDAYS.length - 1;
              return (
                <div
                  key={`c-${i}-${dayIdx}-${turmaIdx}`}
                  className={`border-r border-[#e5e4e7] ${rowDividerClass} ${
                    turmaIdx === 0 && dayIdx > 0 ? "border-l border-[#d8d5da]" : ""
                  } ${isLastDay && isLastTurma ? "border-r-0" : ""}`}
                  style={{
                    gridColumn: dayIdx * turmasCount + turmaIdx + 2,
                    gridRow: i + headerRows + 1,
                  }}
                />
              );
            }),
          ),
        )}

        {placedMarks.map(({ mark, col, rowStart }) => {
          const dayIdx = col;
          return (
            <div
              key={`m-${mark.id}`}
              className="bg-red-100/70 border-l-2 border-red-400 pointer-events-none"
              style={{
                gridColumn: `${dayIdx * turmasCount + 2} / span ${turmasCount}`,
                gridRow: rowStart + headerRows + 1,
              }}
              title="Bloco Vermelho"
            />
          );
        })}

        {placedEvents.map(({ ev, dayCol, rowStart, span, turmaIndices, colSpan }) => {
          const style = styleForType(ev.type);
          const clickable = !!onEventClick;
          const firstTurmaIdx = turmaIndices[0];
          if (firstTurmaIdx === undefined) return null;
          const startCol = dayCol * turmasCount + firstTurmaIdx + 2;
          return (
            <button
              key={`e-${ev.id}`}
              type="button"
              onClick={clickable ? () => onEventClick(ev) : undefined}
              className={`relative my-[1px] rounded border text-left text-[11px] leading-tight overflow-hidden ${
                style.bg
              } ${style.border} ${style.text} ${
                clickable ? "cursor-pointer hover:brightness-95 transition" : "cursor-default"
              }`}
              style={{
                gridColumn: `${startCol} / span ${colSpan}`,
                gridRow: `${rowStart + headerRows + 1} / span ${span}`,
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
