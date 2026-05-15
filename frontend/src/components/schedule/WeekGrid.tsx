import { useMemo, useRef } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";
import ScheduleEventCard from "./ScheduleEventCard";
import { placeEventsOnGrid } from "./scheduleGrid";
import { styleForSubject } from "./subjectColors";
import { useColumnResize } from "./useColumnResize";
import { useGridTimeRange } from "./useGridTimeRange";

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

const SLOT_MINUTES = 30;
const MIN_SLOT_PX = 16;
const HEADER_PX = 40;
// Width each turma column gets in the default (un-resized) flexible layout.
const TURMA_COLUMN_DEFAULT_MIN_PX = 64;

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

  const { gridStartMinutes, slotCount } = useGridTimeRange({
    events,
    marks,
    startTime,
    endTime,
    includeEndSlot,
  });

  const placedEvents = useMemo(
    () => placeEventsOnGrid(events, activeTurmas, visibleDayIndices, gridStartMinutes, slotCount),
    [events, activeTurmas, gridStartMinutes, slotCount, visibleDayIndices],
  );

  const placedMarks = useMemo(
    () =>
      marks
        .map((m) => {
          const col = WEEKDAYS.indexOf(m.weekday);
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

        {placedEvents.flatMap(({ ev, dayCol, rowStart, span, runs }) => {
          const style = styleForSubject(ev.uc);
          const isEditingEvent = editingEventId === ev.id;
          return runs.map((run) => (
            <ScheduleEventCard
              key={`e-${ev.id}-${run.start}`}
              ev={ev}
              startCol={dayCol * turmasCount + run.start + 2}
              startRow={rowStart + headerRows + 1}
              colSpan={run.span}
              rowSpan={span}
              style={style}
              isEditing={isEditingEvent}
              onClick={onEventClick}
            />
          ));
        })}
      </div>
    </div>
  );
}
