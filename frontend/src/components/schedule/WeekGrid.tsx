import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";
import { styleForSubject } from "./subjectColors";

export interface WeekGridEvent {
  id: string;
  weekday: Weekday;
  startTime: number;
  duration: number;
  title?: string;
  body?: string[];
  type?: string;
  turma?: string;
  classCodes?: string[];
  uc?: string;
  professor?: string;
  sala?: string;
  teacherIds?: string[];
  roomIds?: string[];
  subjectNames?: string[];
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
  onEventDoubleClick?: (event: WeekGridEvent) => void;
  onHorizontalScroll?: () => void;
  emptyMessage?: string;
  weekdayLabels?: string[];
  primaryHeaderLeftLabel?: string;
  secondaryHeaderLeftLabel?: string;
  selectedTurmas?: string[];
  turmaShifts?: Record<string, number>;
  slotHeightPx?: number;
  showHalfHourLabels?: boolean;
  showHalfHourDividers?: boolean;
  includeEndSlot?: boolean;
  headerHeightPx?: number;
  hourLabelFontPx?: number;
  editingEventId?: string;
  selectedDays?: string[];
}

const WEEKDAY_LABELS = WEEKDAYS.map((day) => WEEKDAY_LABELS_SHORT[day]);

const DEFAULT_START_HHMM = 800;
const DEFAULT_END_HHMM = 2000;
const SLOT_MINUTES = 30;
const MIN_SLOT_PX = 16;
const HEADER_PX = 40;
const TURMA_COLUMN_MIN_PX = 32;
const TURMA_COLUMN_MAX_PX = 320;
// Width each turma column gets in the default (un-resized) flexible layout.
const TURMA_COLUMN_DEFAULT_MIN_PX = 64;

function weekdayIndex(weekday: Weekday): number {
  return WEEKDAYS.indexOf(weekday);
}

// Marquee scroll speed in pixels per second. The animation duration is derived
// from this and the overflow distance, so text always scrolls at this exact
// rate regardless of how much it overflows.
const MARQUEE_SPEED_PX_PER_SEC = 9;

// One line of text inside an event card. When the text is wider than the
// available space it scrolls back and forth while the parent card (a `group`)
// is hovered, so the clipped part can still be read.
function MarqueeText({ children, className = "" }: { children: string; className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [overflowPx, setOverflowPx] = useState(0);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const text = textRef.current;
    if (!container || !text) return;
    const measure = () => {
      const diff = Math.ceil(text.scrollWidth - container.clientWidth);
      setOverflowPx(diff > 1 ? diff : 0);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    observer.observe(text);
    return () => observer.disconnect();
  }, [children]);

  const isOverflowing = overflowPx > 0;

  return (
    <div ref={containerRef} className={`overflow-hidden ${className}`}>
      <span
        ref={textRef}
        className={`inline-block whitespace-nowrap ${isOverflowing ? "marquee" : ""}`}
        style={
          isOverflowing
            ? ({
                "--marquee-shift": `-${overflowPx}px`,
                "--marquee-duration": `${overflowPx / MARQUEE_SPEED_PX_PER_SEC}s`,
              } as React.CSSProperties)
            : undefined
        }
      >
        {children}
      </span>
    </div>
  );
}

function getTurmaHeaderStyle(shift?: number): string {
  if (shift !== undefined && shift % 2 === 0) return "bg-[#f7ddd7] border-[#e0b0a5] text-[#8C2C19]";
  return "bg-[#f9f7f4] text-[#08060d]";
}

// Maps each turma code to a shortened label with the prefix/suffix shared by
// every code stripped off (e.g. "2LEIC01", "2LEIC02" -> "01", "02"). Used when
// a column is too narrow to show the full code.
function getTurmaShortLabels(turmas: string[]): Map<string, string> {
  const labels = new Map<string, string>();
  const first = turmas[0];
  if (turmas.length < 2 || !first) {
    for (const turma of turmas) labels.set(turma, turma);
    return labels;
  }

  // Longest common prefix shared by every turma code.
  let prefixLen = first.length;
  for (const turma of turmas) {
    let i = 0;
    const max = Math.min(prefixLen, turma.length);
    while (i < max && turma[i] === first[i]) i++;
    prefixLen = i;
  }

  // Longest common suffix, measured on what is left after the shared prefix.
  let suffixLen = first.length - prefixLen;
  for (const turma of turmas) {
    let i = 0;
    const max = Math.min(suffixLen, turma.length - prefixLen);
    while (i < max && turma[turma.length - 1 - i] === first[first.length - 1 - i]) i++;
    suffixLen = i;
  }

  for (const turma of turmas) {
    const short = turma.slice(prefixLen, turma.length - suffixLen);
    labels.set(turma, short.length > 0 ? short : turma);
  }
  return labels;
}

export default function WeekGrid({
  events,
  marks = [],
  startTime,
  endTime,
  onEventClick,
  onEventDoubleClick,
  onHorizontalScroll,
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
  editingEventId,
  selectedDays,
}: WeekGridProps) {
  const gridRef = useRef<HTMLDivElement>(null);
  const lastScrollLeftRef = useRef(0);

  // Uniform width applied to every turma column once a resize finishes
  // (null = use the default flexible layout).
  const [columnWidthPx, setColumnWidthPx] = useState<number | null>(null);
  // While a resize is in progress, only the dragged column changes width;
  // every other column stays frozen at `othersWidth`.
  const [dragState, setDragState] = useState<{
    colIndex: number;
    width: number;
    othersWidth: number;
  } | null>(null);
  const dragInfoRef = useRef<{
    colIndex: number;
    startX: number;
    startWidth: number;
    width: number;
  } | null>(null);
  // Pending horizontal scroll correction so a resized column keeps its on-screen
  // position once every column adopts the new width.
  const scrollAdjustRef = useRef(0);

  const labels =
    weekdayLabels && weekdayLabels.length === WEEKDAY_LABELS.length
      ? weekdayLabels
      : WEEKDAY_LABELS;

  const visibleDayIndices = useMemo(() => {
    if (!selectedDays || selectedDays.length === 0) return WEEKDAYS.map((_, idx) => idx);
    return WEEKDAYS.map((day, idx) => (selectedDays.includes(day) ? idx : -1)).filter(
      (idx) => idx >= 0,
    );
  }, [selectedDays]);

  const filteredLabels = useMemo(
    () => visibleDayIndices.map((idx) => labels[idx]),
    [visibleDayIndices, labels],
  );

  // When no turmas are explicitly selected, fall back to every turma present
  // in the events. Memoized because `activeTurmas` feeds several downstream
  // memos — recreating it each render would invalidate all of them.
  const activeTurmas = useMemo(
    () =>
      selectedTurmas.length > 0
        ? selectedTurmas
        : Array.from(new Set(events.map((e) => e.turma).filter(Boolean) as string[])).sort(),
    [selectedTurmas, events],
  );
  const turmasCount = Math.max(activeTurmas.length, 1);
  const turmaColumnCount = visibleDayIndices.length * turmasCount;
  const turmaShortLabels = useMemo(() => getTurmaShortLabels(activeTurmas), [activeTurmas]);

  const hasSecondaryHeader = activeTurmas.length > 0 && visibleDayIndices.length > 0;
  const headerRows = hasSecondaryHeader ? 2 : 1;
  const minSlotPx = slotHeightPx ?? MIN_SLOT_PX;
  const headerPx = headerHeightPx ?? HEADER_PX;
  const hourFontPx = hourLabelFontPx ?? 10;

  const gridTemplateColumns = dragState
    ? `44px ${Array.from({ length: turmaColumnCount }, (_, columnIndex) =>
        columnIndex === dragState.colIndex ? `${dragState.width}px` : `${dragState.othersWidth}px`,
      ).join(" ")}`
    : columnWidthPx != null
      ? `44px repeat(${turmaColumnCount}, ${columnWidthPx}px)`
      : `44px repeat(${turmaColumnCount}, minmax(${TURMA_COLUMN_DEFAULT_MIN_PX}px, 1fr))`;

  const handleResizeStart = (columnIndex: number, event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    const startWidth = Math.round(cell.getBoundingClientRect().width);
    dragInfoRef.current = {
      colIndex: columnIndex,
      startX: event.clientX,
      startWidth,
      width: startWidth,
    };
    setDragState({ colIndex: columnIndex, width: startWidth, othersWidth: startWidth });
  };

  const handleResizeKeyDown = (
    columnIndex: number,
    event: React.KeyboardEvent<HTMLButtonElement>,
  ) => {
    const direction = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (direction === 0) return;
    event.preventDefault();
    const cell = event.currentTarget.parentElement;
    if (!cell) return;
    const step = event.shiftKey ? 32 : 8;
    const currentWidth = Math.round(cell.getBoundingClientRect().width);
    const nextWidth = Math.min(
      TURMA_COLUMN_MAX_PX,
      Math.max(TURMA_COLUMN_MIN_PX, currentWidth + direction * step),
    );
    scrollAdjustRef.current = columnIndex * (nextWidth - currentWidth);
    setColumnWidthPx(nextWidth);
  };

  const isResizing = dragState !== null;
  useEffect(() => {
    if (!isResizing) return;

    const handleMove = (event: MouseEvent) => {
      const info = dragInfoRef.current;
      if (!info) return;
      const nextWidth = Math.min(
        TURMA_COLUMN_MAX_PX,
        Math.max(TURMA_COLUMN_MIN_PX, Math.round(info.startWidth + (event.clientX - info.startX))),
      );
      info.width = nextWidth;
      setDragState({ colIndex: info.colIndex, width: nextWidth, othersWidth: info.startWidth });
    };

    const handleUp = () => {
      const info = dragInfoRef.current;
      if (info) {
        // Once every column adopts the new width, the dragged column's left edge
        // shifts by colIndex * (newWidth - oldWidth); cancel it out via scrollLeft.
        scrollAdjustRef.current = info.colIndex * (info.width - info.startWidth);
        setColumnWidthPx(info.width);
      }
      dragInfoRef.current = null;
      setDragState(null);
    };

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", handleMove);
    document.addEventListener("mouseup", handleUp);
    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      document.removeEventListener("mousemove", handleMove);
      document.removeEventListener("mouseup", handleUp);
    };
  }, [isResizing]);

  // After a resize commits the new column width, shift the scroll position so the
  // resized column stays exactly where it was on screen.
  useLayoutEffect(() => {
    const adjustment = scrollAdjustRef.current;
    if (adjustment === 0) return;
    scrollAdjustRef.current = 0;
    const scrollContainer = gridRef.current?.parentElement;
    if (scrollContainer) scrollContainer.scrollLeft += adjustment;
  }, [columnWidthPx]);

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

      // Filter events by visible days
      const visibleColIdx = visibleDayIndices.indexOf(dayCol);
      if (visibleColIdx < 0) continue; // Event is on a hidden day

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
          dayCol: visibleColIdx,
          rowStart,
          span,
          turmaIndices,
          colSpan: turmaIndices.length,
        });
      }
    }

    return result;
  }, [events, activeTurmas, gridStartMinutes, slotCount, visibleDayIndices]);

  const placedMarks = useMemo(
    () =>
      marks
        .map((m) => {
          const col = weekdayIndex(m.weekday);
          if (col < 0) return null;
          const visibleColIdx = visibleDayIndices.indexOf(col);
          if (visibleColIdx < 0) return null; // Mark is on a hidden day
          const rowStart = Math.round((hhmmToMinutes(m.time) - gridStartMinutes) / SLOT_MINUTES);
          if (rowStart < 0 || rowStart >= slotCount) return null;
          return { mark: m, col: visibleColIdx, rowStart };
        })
        .filter(<T,>(x: T | null): x is T => x !== null),
    [marks, gridStartMinutes, slotCount, visibleDayIndices],
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
      onScroll={(e) => {
        const { scrollLeft } = e.currentTarget;
        if (scrollLeft !== lastScrollLeftRef.current) {
          lastScrollLeftRef.current = scrollLeft;
          onHorizontalScroll?.();
        }
      }}
    >
      <div
        className="grid h-full w-max min-w-full"
        ref={gridRef}
        style={{
          gridTemplateColumns,
          gridTemplateRows: `${headerPx}px${hasSecondaryHeader ? ` ${headerPx}px` : ""} repeat(${slotCount}, minmax(${minSlotPx}px, 1fr))`,
        }}
      >
        <div
          className="sticky top-0 left-0 z-30 border-b border-r border-[#e5e4e7] bg-[#f9f7f4]"
          style={{ gridColumn: 1, gridRow: 1 }}
        >
          <div className="px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d]">
            {primaryHeaderLeftLabel ?? ""}
          </div>
        </div>
        {filteredLabels.map((label, visibleIdx) => (
          <div
            key={label}
            className={`sticky top-0 z-20 border-b border-[#e5e4e7] bg-[#f9f7f4] px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d] ${
              visibleIdx > 0 ? "border-l border-[#d8d5da]" : ""
            }`}
            style={{
              gridColumn: `${visibleIdx * turmasCount + 2} / span ${turmasCount}`,
              gridRow: 1,
            }}
          >
            {label}
          </div>
        ))}

        {hasSecondaryHeader ? (
          <>
            <div
              className="sticky left-0 z-30 border-b border-r border-[#e5e4e7] bg-[#f9f7f4]"
              style={{ gridColumn: 1, gridRow: 2, top: headerPx }}
            >
              <div className="px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d]">
                {secondaryHeaderLeftLabel ?? ""}
              </div>
            </div>
            {visibleDayIndices.map((_, visibleIdx) =>
              activeTurmas.map((turma, turmaIdx) => {
                const columnIndex = visibleIdx * turmasCount + turmaIdx;
                const shortLabel = turmaShortLabels.get(turma) ?? turma;
                return (
                  <div
                    key={`sub-${visibleIdx}-${turmaIdx}`}
                    className={`@container sticky z-20 overflow-hidden border-b px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider ${getTurmaHeaderStyle(
                      turmaShifts[turma],
                    )} ${turmaIdx === 0 && visibleIdx > 0 ? "border-l border-[#d8d5da]" : "border-[#e5e4e7]"}`}
                    style={{
                      gridColumn: columnIndex + 2,
                      gridRow: 2,
                      top: headerPx,
                    }}
                  >
                    <span className="inline @min-[32px]:hidden">{shortLabel}</span>
                    <span className="hidden @min-[32px]:inline">{turma}</span>
                    <button
                      type="button"
                      aria-label="Redimensionar colunas"
                      onMouseDown={(event) => handleResizeStart(columnIndex, event)}
                      onKeyDown={(event) => handleResizeKeyDown(columnIndex, event)}
                      className={`absolute top-0 right-0 z-10 h-full w-2 cursor-col-resize border-0 bg-transparent p-0 hover:bg-[#8C2C19]/40 focus:bg-[#8C2C19]/60 focus:outline-none ${
                        dragState?.colIndex === columnIndex ? "bg-[#8C2C19]/60" : ""
                      }`}
                      title="Arrasta para redimensionar as colunas"
                    />
                  </div>
                );
              }),
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
              className={`sticky left-0 z-10 flex items-center justify-center bg-white border-r border-[#e5e4e7] px-2 text-center text-[#6b6375] ${rowDividerClass}`}
              style={{
                gridColumn: 1,
                gridRow: i + headerRows + 1,
                fontSize: `${hourFontPx}px`,
              }}
            >
              {showLabel ? minutesToTime(mins) : ""}
            </div>
          );
        })}

        {Array.from({ length: slotCount }).map((_, i) =>
          visibleDayIndices.flatMap((_, visibleIdx) =>
            Array.from({ length: turmasCount }).map((_, turmaIdx) => {
              const mins = gridStartMinutes + i * SLOT_MINUTES;
              const isHour = mins % 60 === 0;
              const rowDividerClass = showHalfHourDividers
                ? "border-t border-[#e5e4e7]"
                : isHour
                  ? "border-t"
                  : "";
              const isLastTurma = turmaIdx === turmasCount - 1;
              const isLastDay = visibleIdx === visibleDayIndices.length - 1;
              return (
                <div
                  key={`c-${i}-${visibleIdx}-${turmaIdx}`}
                  className={`border-r border-[#e5e4e7] ${rowDividerClass} ${
                    turmaIdx === 0 && visibleIdx > 0 ? "border-l border-[#d8d5da]" : ""
                  } ${isLastDay && isLastTurma ? "border-r-0" : ""}`}
                  style={{
                    gridColumn: visibleIdx * turmasCount + turmaIdx + 2,
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
              className="bg-[#f7ddd7]/80 border-l-2 border-[#e0b0a5] pointer-events-none"
              style={{
                gridColumn: `${dayIdx * turmasCount + 2} / span ${turmasCount}`,
                gridRow: rowStart + headerRows + 1,
              }}
              title="Bloco Vermelho"
            />
          );
        })}

        {placedEvents.map(({ ev, dayCol, rowStart, span, turmaIndices, colSpan }) => {
          const style = styleForSubject(ev.uc);
          const clickable = !!onEventClick || !!onEventDoubleClick;
          const firstTurmaIdx = turmaIndices[0];
          if (firstTurmaIdx === undefined) return null;
          const startCol = dayCol * turmasCount + firstTurmaIdx + 2;
          const isEditingEvent = editingEventId === ev.id;
          return (
            <button
              key={`e-${ev.id}`}
              type="button"
              data-schedule-event=""
              onClick={onEventClick ? () => onEventClick(ev) : undefined}
              onDoubleClick={onEventDoubleClick ? () => onEventDoubleClick(ev) : undefined}
              className={`group relative my-[1px] rounded border text-left text-[11px] leading-tight overflow-hidden ${
                isEditingEvent
                  ? "bg-[#250902] border-[#38040e] text-white"
                  : `${style.bg} ${style.border} ${style.text}`
              } ${clickable ? "cursor-pointer hover:brightness-95 transition" : "cursor-default"}`}
              style={{
                gridColumn: `${startCol} / span ${colSpan}`,
                gridRow: `${rowStart + headerRows + 1} / span ${span}`,
              }}
              title={ev.title}
              disabled={!clickable}
            >
              <div
                className="absolute inset-0 overflow-hidden px-1.5 py-1"
                style={{
                  maskImage:
                    "linear-gradient(to bottom, black calc(100% - 3px), rgba(0,0,0,0.2) calc(100% - 1px), transparent 100%)",
                  WebkitMaskImage:
                    "linear-gradient(to bottom, black calc(100% - 3px), rgba(0,0,0,0.2) calc(100% - 1px), transparent 100%)",
                }}
              >
                {ev.title && <MarqueeText className="font-semibold">{ev.title}</MarqueeText>}
                {ev.type && (
                  <MarqueeText className="text-[10px] uppercase leading-none opacity-70">
                    {ev.type}
                  </MarqueeText>
                )}
                {ev.body?.map((line, i) => (
                  <MarqueeText key={i} className="opacity-80">
                    {line}
                  </MarqueeText>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
