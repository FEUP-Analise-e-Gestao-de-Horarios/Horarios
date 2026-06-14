import { useMemo, useRef } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_LONG, WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";
import MarqueeText from "./MarqueeText";
import { styleForSubject } from "./subjectColors";
import { TURMA_COLUMN_MAX_PX, TURMA_COLUMN_MIN_PX, useColumnResize } from "./useColumnResize";

export interface WeekGridEvent {
  id: string;
  blockId?: string;
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
// Width each turma column gets in the default (un-resized) flexible layout.
const TURMA_COLUMN_DEFAULT_MIN_PX = 64;
// Pixels of horizontal scroll change required to count as a user gesture.
const HORIZONTAL_SCROLL_THRESHOLD_PX = 8;

function weekdayIndex(weekday: Weekday): number {
  return WEEKDAYS.indexOf(weekday);
}

function getTurmaHeaderStyle(shift?: number): string {
  if (shift !== undefined && shift % 2 === 0) return "bg-[#f7ddd7] border-[#e0b0a5] text-[#8C2C19]";
  return "bg-[#f9f7f4] text-[#08060d]";
}

function getEventAriaLabel(ev: WeekGridEvent): string {
  const startMin = hhmmToMinutes(ev.startTime);
  const endMin = startMin + ev.duration * SLOT_MINUTES;
  const timeRange = `${minutesToTime(startMin)} a ${minutesToTime(endMin)}`;
  const parts = [
    ev.title || ev.uc || ev.type || "Evento",
    `${WEEKDAY_LABELS_LONG[ev.weekday]}, ${timeRange}`,
  ];
  if (ev.turma) parts.push(`turma ${ev.turma}`);
  if (ev.professor) parts.push(`docente ${ev.professor}`);
  if (ev.sala) parts.push(`sala ${ev.sala}`);
  return parts.join(" — ");
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

// Collapses a sorted, ascending list of column indices into contiguous runs.
// A merged event may cover non-adjacent turma columns (e.g. [0, 2]); each run
// is rendered as its own card so a card never spans a gap.
function toContiguousRuns(sortedIndices: number[]): { start: number; span: number }[] {
  const runs: { start: number; span: number }[] = [];
  for (const index of sortedIndices) {
    const last = runs[runs.length - 1];
    if (last && index === last.start + last.span) {
      last.span += 1;
    } else {
      runs.push({ start: index, span: 1 });
    }
  }
  return runs;
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
  const lastScrollLeftRef = useRef(0);
  const { gridRef, columnWidthPx, dragState, handleResizeStart, handleResizeKeyDown } =
    useColumnResize();

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
    // The backend emits one event per (session, class code). Events that are
    // really the same session — same day/time/duration/type and same
    // title/teacher/room — are merged into a single card that spans every
    // turma column it belongs to, instead of drawing N identical cards.
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
      // Contiguous column runs the event occupies; usually one run.
      runs: { start: number; span: number }[];
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
          runs: toContiguousRuns(turmaIndices),
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
        // Threshold filters out the small programmatic adjustments
        // `useColumnResize` makes to scrollLeft when a column changes width,
        // so resizing a column doesn't accidentally collapse an open drawer.
        // Real horizontal scroll gestures easily clear this threshold.
        if (Math.abs(scrollLeft - lastScrollLeftRef.current) > HORIZONTAL_SCROLL_THRESHOLD_PX) {
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
                    {/* Window-splitter pattern: `role="separator"` with
                        `aria-orientation` and a focusable tabindex is the
                        standard ARIA widget for a column resize grip
                        (https://www.w3.org/WAI/ARIA/apg/patterns/windowsplitter/).
                        jsx-a11y conservatively treats separator as
                        non-interactive, so the rules are disabled here. */}
                    {/* eslint-disable jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions */}
                    <div
                      role="separator"
                      tabIndex={0}
                      aria-orientation="vertical"
                      aria-label={`Redimensionar coluna ${turma}`}
                      aria-valuemin={TURMA_COLUMN_MIN_PX}
                      aria-valuemax={TURMA_COLUMN_MAX_PX}
                      aria-valuenow={
                        dragState?.colIndex === columnIndex
                          ? dragState.width
                          : (columnWidthPx ?? undefined)
                      }
                      onMouseDown={(event) => handleResizeStart(columnIndex, event)}
                      onKeyDown={(event) => handleResizeKeyDown(columnIndex, event)}
                      className={`absolute top-0 right-0 z-10 h-full w-2 cursor-col-resize hover:bg-[#8C2C19]/40 focus-visible:bg-[#8C2C19]/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/80 ${
                        dragState?.colIndex === columnIndex ? "bg-[#8C2C19]/60" : ""
                      }`}
                      title="Arrasta para redimensionar as colunas"
                    />
                    {/* eslint-enable jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions */}
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

        {placedEvents.flatMap(({ ev, dayCol, rowStart, span, runs }) => {
          const style = styleForSubject(ev.uc);
          const clickable = !!onEventClick || !!onEventDoubleClick;
          const isEditingEvent = editingEventId === ev.id;
          const ariaLabel = getEventAriaLabel(ev);
          return runs.map((run) => {
            const startCol = dayCol * turmasCount + run.start + 2;
            return (
              <button
                key={`e-${ev.id}-${run.start}`}
                type="button"
                data-schedule-event=""
                onClick={onEventClick ? () => onEventClick(ev) : undefined}
                onDoubleClick={onEventDoubleClick ? () => onEventDoubleClick(ev) : undefined}
                aria-label={ariaLabel}
                aria-current={isEditingEvent ? "true" : undefined}
                className={`group relative my-[1px] rounded border text-left text-[11px] leading-tight overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/80 focus-visible:z-10 ${
                  isEditingEvent
                    ? "bg-[#250902] border-[#38040e] text-white"
                    : `${style.bg} ${style.border} ${style.text}`
                } ${clickable ? "cursor-pointer hover:brightness-95 transition" : "cursor-default"}`}
                style={{
                  gridColumn: `${startCol} / span ${run.span}`,
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
          });
        })}
      </div>
    </div>
  );
}
