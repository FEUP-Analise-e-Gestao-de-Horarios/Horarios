import { useMemo, useRef, type CSSProperties, type MouseEvent } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";
import { SCHEDULE_PLACEMENT_DATA_ATTR } from "./dismissable";
import EventArcsOverlay from "./EventArcsOverlay";
import ScheduleEventCard from "./ScheduleEventCard";
import {
  assignLaneSegments,
  computeColumnWidths,
  computeRowHeights,
  computeRowOccupancy,
  computeValidPlacementSlots,
  placeEventsOnGrid,
} from "./scheduleGrid";
import { styleForSubject, type SubjectPalette } from "./subjectColors";
import { TURMA_COLUMN_MAX_PX, TURMA_COLUMN_MIN_PX, useColumnResize } from "./useColumnResize";
import { useGridTimeRange } from "./useGridTimeRange";

export interface WeekGridEvent {
  id: string;
  /**
   * Backend session id, shared by every event expanded from the same session
   * (`id` is `${sessionId}-${turma}` for class-expanded events). Conflict
   * records and session mutations key on this, never on `id`.
   */
  sessionId: string;
  weekday: Weekday;
  startTime: number;
  duration: number;
  title?: string;
  body?: string[];
  type?: string;
  turma?: string;
  classCodes?: string[];
  /** Weeks (as ISO date strings) the source week-block covers. */
  weeks?: string[];
  uc?: string;
  professor?: string;
  sala?: string;
  teachers?: { id: string; acronym: string; name: string }[];
  rooms?: { id: string; name: string }[];
  subjectNames?: string[];
}

export interface WeekGridMark {
  id: string;
  weekday: Weekday;
  time: number;
  /** Selection unavailability (#5); absent = generic red block. */
  kind?: "unavailable";
}

const UNAVAILABLE_RED = "#e5484d";

function markStyle(kind: WeekGridMark["kind"]): { className: string; style?: CSSProperties } {
  if (kind === "unavailable") {
    return {
      className: "border-l-2",
      style: { backgroundColor: `${UNAVAILABLE_RED}40`, borderColor: UNAVAILABLE_RED },
    };
  }
  return { className: "bg-[#f7ddd7]/80 border-l-2 border-[#e0b0a5]" };
}

interface WeekGridProps {
  events: WeekGridEvent[];
  marks?: WeekGridMark[];
  startTime?: number;
  endTime?: number;
  onEventClick?: (event: WeekGridEvent, domEvent: MouseEvent<HTMLButtonElement>) => void;
  onHorizontalScroll?: () => void;
  emptyMessage?: string;
  weekdayLabels?: string[];
  primaryHeaderLeftLabel?: string;
  secondaryHeaderLeftLabel?: string;
  selectedTurmas?: string[];
  /** Union of the weeks the user has selected; drives the partial-weeks badge. */
  selectedWeeks?: string[];
  /** Maps each week (ISO date) to its 1-based ordinal, for the week-range label. */
  weekNumbers?: Map<string, number>;
  turmaShifts?: Record<string, number>;
  slotHeightPx?: number;
  showHalfHourLabels?: boolean;
  showHalfHourDividers?: boolean;
  includeEndSlot?: boolean;
  headerHeightPx?: number;
  hourLabelFontPx?: number;
  editingEventId?: string;
  /** Sessions marked for a bulk move (shift-click); shown with a blue ring. */
  selectedSessionIds?: Set<string>;
  selectedDays?: string[];
  /** Per-UC colours; events fall back to a neutral style when absent. */
  subjectPalette?: SubjectPalette;
  /** Collapse rows/columns that hold no events or marks to reduce scroll (#13/#14). */
  compactEmpty?: boolean;
  /**
   * Placement mode for moving an event: empty cells become click targets that
   * highlight on hover, even while collapsed by `compactEmpty` — a row only
   * grows once something actually occupies it. `placementDurationSlots` drives
   * which start rows are valid.
   */
  placementMode?: boolean;
  placementDurationSlots?: number;
  /**
   * `turma` is the class column the click landed in — undefined when there's
   * no secondary turma header at all (a single-turma view). Passing it
   * through lets a placement cross into a different class, not just move
   * within the one the event already belongs to.
   */
  onSlotClick?: (weekday: Weekday, minutes: number, turma?: string) => void;
}

const WEEKDAY_LABELS = WEEKDAYS.map((day) => WEEKDAY_LABELS_SHORT[day]);

const SLOT_MINUTES = 30;
const MIN_SLOT_PX = 16;
const HEADER_PX = 40;
// Width of the sticky time-label column. '08:00' at the 12px label font is
// ~33px; 34px hugs it tight on both sides (PI ToDo #22).
const TIME_COL_PX = 34;
// Height of a collapsed (event-free) time-slot row: just tall enough for the
// hour number to stay legible with no padding above/below (PI ToDo #13).
const COMPACT_ROW_PX = 16;
// Font size of the day-header labels (matches the `text-[10px]` class below);
// used to size a fully-empty day down to its label width (PI ToDo #14).
const DAY_HEADER_FONT_PX = 10;
// Width each turma column gets in the default (un-resized) flexible layout.
const TURMA_COLUMN_DEFAULT_MIN_PX = 64;
// Pixels of horizontal scroll change required to count as a user gesture.
const HORIZONTAL_SCROLL_THRESHOLD_PX = 8;

function getTurmaHeaderStyle(shift?: number): string {
  // Alternating turnos get a neutral cool-grey tint (was orange); the brand
  // colour is reserved for actions, not passive headers (#23).
  if (shift !== undefined && shift % 2 === 0) return "bg-[#e7eaee] border-[#d3d8df] text-[#08060d]";
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
  selectedWeeks = [],
  weekNumbers,
  turmaShifts = {},
  slotHeightPx,
  showHalfHourLabels = false,
  showHalfHourDividers = false,
  includeEndSlot = false,
  headerHeightPx,
  hourLabelFontPx,
  editingEventId,
  selectedSessionIds,
  selectedDays,
  subjectPalette,
  compactEmpty = true,
  placementMode = false,
  placementDurationSlots = 1,
  onSlotClick,
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

  const { gridStartMinutes, slotCount } = useGridTimeRange({
    events,
    marks,
    startTime,
    endTime,
    includeEndSlot,
  });

  const placedEvents = useMemo(
    () =>
      placeEventsOnGrid(
        events,
        activeTurmas,
        visibleDayIndices,
        gridStartMinutes,
        slotCount,
        selectedWeeks,
        weekNumbers,
      ),
    [
      events,
      activeTurmas,
      gridStartMinutes,
      slotCount,
      visibleDayIndices,
      selectedWeeks,
      weekNumbers,
    ],
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

  // Start rows a moved class can land on without overflowing the grid.
  const validPlacementRows = useMemo(
    () =>
      placementMode ? new Set(computeValidPlacementSlots(slotCount, placementDurationSlots)) : null,
    [placementMode, slotCount, placementDurationSlots],
  );

  // Empty row/column compaction (#13/#14); compactEmpty off keeps all full-size.
  const rowOccupied = useMemo(
    () =>
      compactEmpty
        ? // Marks (the #5 unavailability overlay) intentionally don't keep a row
          // expanded — only real events drive row height.
          computeRowOccupancy(placedEvents, [], slotCount)
        : new Array<boolean>(slotCount).fill(true),
    [compactEmpty, placedEvents, slotCount],
  );

  const { laned: lanedEvents, colLaneCount: rawColLaneCount } = useMemo(
    () =>
      assignLaneSegments(
        placedEvents,
        turmasCount,
        turmaColumnCount,
        placedMarks.map((m) => m.col),
      ),
    [placedEvents, turmasCount, turmaColumnCount, placedMarks],
  );

  const colLaneCount = useMemo(
    () => (compactEmpty ? rawColLaneCount : rawColLaneCount.map((lanes) => Math.max(lanes, 1))),
    [compactEmpty, rawColLaneCount],
  );

  // Width a fully-empty day collapses to: enough to show its (longest) day
  // label on one line, with a little padding.
  const emptyDayTotalPx = useMemo(() => {
    const longest = Math.max(3, ...filteredLabels.map((label) => label?.length ?? 0));
    return Math.ceil(longest * DAY_HEADER_FONT_PX * 0.8) + 20;
  }, [filteredLabels]);

  const fullRowTrack = `minmax(${minSlotPx}px, 1fr)`;
  const compactRowPx = Math.max(COMPACT_ROW_PX, Math.ceil(hourFontPx * 1.5));
  const gridTemplateRows = `${headerPx}px${
    hasSecondaryHeader ? ` ${headerPx}px` : ""
  } ${computeRowHeights(rowOccupied, fullRowTrack, compactRowPx).join(" ")}`;

  // While dragging, occupied columns freeze at their pre-drag width so they
  // don't reflow as the handle moves, and only the dragged column follows the
  // pointer. Empty columns/days stay compacted just as they will after the
  // commit, so releasing no longer pops them from full-width back to thin.
  const turmaColumnTracks = dragState
    ? computeColumnWidths(
        colLaneCount,
        turmasCount,
        dragState.othersWidth,
        TURMA_COLUMN_DEFAULT_MIN_PX,
        TURMA_COLUMN_MIN_PX,
        emptyDayTotalPx,
      ).map((track, columnIndex) =>
        columnIndex === dragState.colIndex ? `${dragState.width}px` : track,
      )
    : computeColumnWidths(
        colLaneCount,
        turmasCount,
        columnWidthPx ?? null,
        TURMA_COLUMN_DEFAULT_MIN_PX,
        TURMA_COLUMN_MIN_PX,
        emptyDayTotalPx,
      );
  const gridTemplateColumns = `${TIME_COL_PX}px ${turmaColumnTracks.join(" ")}`;

  // Encode everything that fixes a card's position, not just the segment count:
  // the grid tracks plus each event's day/row and every segment's start/span/lane.
  // A same-size reshuffle (e.g. editing a session's time without changing which
  // rows are occupied) leaves the tracks and counts identical, so without the
  // positional fields the overlay would keep stale arcs until the next resize.
  const arcSignature = `${gridTemplateColumns}|${gridTemplateRows}|${lanedEvents
    .map(
      (e) =>
        `${e.ev.id}@${e.dayCol}:${e.rowStart}:${e.segments
          .map((s) => `${s.start}/${s.span}/${s.lane}/${s.laneCount}`)
          .join("+")}`,
    )
    .join(",")}`;

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
        className="relative grid h-full w-max min-w-full"
        ref={gridRef}
        style={{ gridTemplateColumns, gridTemplateRows }}
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
            className={`sticky top-0 z-20 overflow-hidden whitespace-nowrap border-b border-[#e5e4e7] bg-[#f9f7f4] px-2 py-1 text-center text-[10px] font-semibold uppercase tracking-wider text-[#08060d] ${
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
                    className={`@container sticky z-20 overflow-hidden border-b px-0.5 py-1 text-center text-[10px] font-semibold uppercase tracking-wider ${getTurmaHeaderStyle(
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
                      onKeyDown={(event) => handleResizeKeyDown(event)}
                      className={`absolute top-0 right-0 z-10 h-full w-2 cursor-col-resize hover:bg-[#8C2C19]/40 focus-visible:bg-[#8C2C19]/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C73F24]/70 ${
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
              className={`sticky left-0 z-20 flex items-center justify-center bg-white border-r border-[#e5e4e7] px-0 text-center text-[#6b6375] ${rowDividerClass}`}
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
              // Which turma column the click landed in travels with the click,
              // so a placement can cross into a different class instead of
              // only ever moving within the one the event already has.
              const dayIndex = visibleDayIndices[visibleIdx];
              const weekday = dayIndex === undefined ? undefined : WEEKDAYS[dayIndex];
              const clickedTurma = activeTurmas[turmaIdx];
              const isPlacementTarget =
                validPlacementRows !== null && validPlacementRows.has(i) && weekday !== undefined;
              const place = isPlacementTarget
                ? () => onSlotClick?.(weekday, gridStartMinutes + i * SLOT_MINUTES, clickedTurma)
                : undefined;
              return (
                <div
                  key={`c-${i}-${visibleIdx}-${turmaIdx}`}
                  {...(isPlacementTarget ? { [SCHEDULE_PLACEMENT_DATA_ATTR]: "" } : {})}
                  role={isPlacementTarget ? "button" : undefined}
                  tabIndex={isPlacementTarget ? 0 : undefined}
                  aria-label={
                    isPlacementTarget
                      ? `Mover para ${minutesToTime(gridStartMinutes + i * SLOT_MINUTES)}`
                      : undefined
                  }
                  className={`border-r border-[#e5e4e7] ${rowDividerClass} ${
                    turmaIdx === 0 && visibleIdx > 0 ? "border-l border-[#d8d5da]" : ""
                  } ${isLastDay && isLastTurma ? "border-r-0" : ""} ${
                    isPlacementTarget
                      ? "cursor-pointer hover:bg-[#c73f24]/15 hover:ring-1 hover:ring-inset hover:ring-[#c73f24]"
                      : ""
                  }`}
                  style={{
                    gridColumn: visibleIdx * turmasCount + turmaIdx + 2,
                    gridRow: i + headerRows + 1,
                  }}
                  onClick={place}
                  onKeyDown={
                    place
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            place();
                          }
                        }
                      : undefined
                  }
                />
              );
            }),
          ),
        )}

        {placedMarks.map(({ mark, col, rowStart }) => {
          const dayIdx = col;
          const { className, style } = markStyle(mark.kind);
          return (
            <div
              key={`m-${mark.id}`}
              className={`pointer-events-none ${className}`}
              style={{
                ...style,
                gridColumn: `${dayIdx * turmasCount + 2} / span ${turmasCount}`,
                gridRow: rowStart + headerRows + 1,
              }}
              title="Bloco Vermelho"
            />
          );
        })}

        {lanedEvents.flatMap(({ ev, dayCol, rowStart, span, segments, weekRangeLabel }) => {
          const style = styleForSubject(subjectPalette, ev.uc, ev.type);
          const isEditingEvent = editingEventId === ev.id;
          const multiSegment = segments.length > 1;
          return segments.map((seg, segIndex) => (
            <ScheduleEventCard
              key={`e-${ev.id}-${seg.start}`}
              ev={ev}
              startCol={dayCol * turmasCount + seg.start + 2}
              startRow={rowStart + headerRows + 1}
              colSpan={seg.span}
              rowSpan={span}
              lane={seg.lane}
              laneCount={seg.laneCount}
              arcGroupId={multiSegment ? `${ev.id}-${dayCol}-${rowStart}` : undefined}
              arcSegIndex={multiSegment ? segIndex : undefined}
              style={style}
              isEditing={isEditingEvent}
              selected={selectedSessionIds?.has(ev.sessionId)}
              weekRangeLabel={weekRangeLabel}
              onClick={onEventClick}
            />
          ));
        })}

        <EventArcsOverlay
          gridRef={gridRef}
          signature={arcSignature}
          minPeakY={headerPx * headerRows + 2}
        />
      </div>
    </div>
  );
}
