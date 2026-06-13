import { hhmmToMinutes } from "@/utils/time";
import { WEEKDAYS } from "@/utils/weekdays";
import type { WeekGridEvent } from "./WeekGrid";

const SLOT_MINUTES = 30;

export type ContiguousRun = { start: number; span: number };

export type PlacedEvent = {
  ev: WeekGridEvent;
  /** Index into the visible day list, NOT into WEEKDAYS. */
  dayCol: number;
  /** Row offset from the first slot, in slot units. */
  rowStart: number;
  /** Row span, in slot units. */
  span: number;
  /** Contiguous column runs the event occupies; usually one run. */
  runs: ContiguousRun[];
  /**
   * True when the session occurs in only some of the selected weeks — i.e. the
   * weeks it covers are a strict subset of `selectedWeeks`. Always false when
   * `selectedWeeks` is empty or the events carry no week data.
   */
  isPartialWeeks: boolean;
  /**
   * Compact week range the card renders (e.g. "1-7", "1-3, 5-7"). Empty unless
   * the session is partial and `weekNumbers` maps its weeks to ordinals.
   */
  weekRangeLabel: string;
};

/**
 * Renders a sorted, deduplicated list of week ordinals as a compact range
 * string: [1,2,3,4,5,6,7] -> "1-7", [1,2,3,5,6,7] -> "1-3, 5-7", [3] -> "3".
 */
export function formatWeekRanges(numbers: number[]): string {
  const sorted = [...new Set(numbers)].sort((a, b) => a - b);
  const parts: string[] = [];
  let start: number | null = null;
  let prev: number | null = null;
  for (const n of sorted) {
    if (start === null || prev === null) {
      start = n;
      prev = n;
    } else if (n === prev + 1) {
      prev = n;
    } else {
      parts.push(start === prev ? `${start}` : `${start}-${prev}`);
      start = n;
      prev = n;
    }
  }
  if (start !== null && prev !== null) {
    parts.push(start === prev ? `${start}` : `${start}-${prev}`);
  }
  return parts.join(", ");
}

/**
 * Marks which of the `slotCount` grid rows carry content — any placed event
 * spanning the row, or any mark (red block) on it. Empty rows can then be
 * collapsed to reduce vertical scroll (#13).
 */
export function computeRowOccupancy(
  placed: PlacedEvent[],
  markRowStarts: number[],
  slotCount: number,
): boolean[] {
  const occupied = new Array<boolean>(slotCount).fill(false);
  for (const { rowStart, span } of placed) {
    for (let row = rowStart; row < rowStart + span && row < slotCount; row += 1) {
      if (row >= 0) occupied[row] = true;
    }
  }
  for (const row of markRowStarts) {
    if (row >= 0 && row < slotCount) occupied[row] = true;
  }
  return occupied;
}

/**
 * CSS grid-row track sizes: occupied rows keep `fullTrack` (a stretchable
 * `minmax(...,1fr)` so the grid still fills the viewport), empty rows collapse
 * to a thin `compactPx`. Pass an all-true occupancy (or use `compactEmpty`
 * false upstream) to keep every row full — e.g. while placing an event.
 */
export function computeRowHeights(
  rowOccupied: boolean[],
  fullTrack: string,
  compactPx: number,
): string[] {
  return rowOccupied.map((occupied) => (occupied ? fullTrack : `${compactPx}px`));
}

/**
 * Marks which of the `columnCount` turma columns carry an event. A column's
 * global index is `dayCol * turmasCount + turmaIndex`; a run covers every
 * column in `[start, start + span)`. Empty columns can then be narrowed (#14).
 */
export function computeColumnOccupancy(
  placed: PlacedEvent[],
  columnCount: number,
  turmasCount: number,
): boolean[] {
  const occupied = new Array<boolean>(columnCount).fill(false);
  for (const { dayCol, runs } of placed) {
    const base = dayCol * turmasCount;
    for (const run of runs) {
      for (let i = run.start; i < run.start + run.span; i += 1) {
        const col = base + i;
        if (col >= 0 && col < columnCount) occupied[col] = true;
      }
    }
  }
  return occupied;
}

/**
 * CSS grid-column tracks for the turma columns, with two levels of compaction
 * (#14/#16):
 *  - a turma column with an event keeps `fullTrack`;
 *  - an empty column inside a day that *has* events shrinks to `minColPx` (the
 *    smallest a column can be resized to);
 *  - a day with NO events at all collapses to roughly its day-label width
 *    (`emptyDayTotalPx`), split across its columns — narrower than n·minColPx.
 */
export function computeColumnWidths(
  colOccupied: boolean[],
  turmasCount: number,
  fullTrack: string,
  minColPx: number,
  emptyDayTotalPx: number,
): string[] {
  const turmas = Math.max(turmasCount, 1);
  const emptyDayColPx = emptyDayTotalPx / turmas;
  const dayCount = Math.ceil(colOccupied.length / turmas);
  const tracks: string[] = [];
  for (let day = 0; day < dayCount; day += 1) {
    const base = day * turmas;
    const dayHasEvents = colOccupied.slice(base, base + turmas).some(Boolean);
    for (let t = 0; t < turmas; t += 1) {
      if (!dayHasEvents) tracks.push(`${emptyDayColPx}px`);
      else tracks.push(colOccupied[base + t] ? fullTrack : `${minColPx}px`);
    }
  }
  return tracks;
}

/**
 * Collapses a sorted, ascending list of column indices into contiguous runs.
 * A merged event may cover non-adjacent turma columns (e.g. [0, 2]); each run
 * is rendered as its own card so a card never spans a gap.
 */
export function toContiguousRuns(sortedIndices: number[]): ContiguousRun[] {
  const runs: ContiguousRun[] = [];
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

/**
 * Merges events that belong to the same underlying session (same day/time/
 * duration/type/title/teacher/room) AND cover the same set of classes into a
 * single card spanning every turma column they cover, and places each card on
 * the grid.
 *
 * The backend emits one event per (session, class code) but stamps each with
 * the session's full class list, so without merging the grid would draw N
 * identical overlapping cards for one session. Including that class set in the
 * key keeps two sessions that merely share the other fields — but cover
 * different classes (e.g. {B,C} vs {B,C,D}) — as distinct blocks.
 */
export function placeEventsOnGrid(
  events: WeekGridEvent[],
  activeTurmas: string[],
  visibleDayIndices: number[],
  gridStartMinutes: number,
  slotCount: number,
  selectedWeeks: string[] = [],
  weekNumbers: Map<string, number> = new Map(),
): PlacedEvent[] {
  const selectedWeekSet = new Set(selectedWeeks);
  const getMergeKey = (ev: WeekGridEvent): string => {
    const classes = ev.classCodes ? [...ev.classCodes].sort().join(",") : "";
    return [
      ev.weekday,
      ev.startTime,
      ev.duration,
      ev.type,
      ev.title,
      ev.professor,
      ev.sala,
      classes,
    ].join("||");
  };

  const mergeGroups = new Map<
    string,
    { events: WeekGridEvent[]; turmas: Set<string>; weeks: Set<string> }
  >();
  for (const ev of events) {
    if (activeTurmas.length > 0 && ev.turma && !activeTurmas.includes(ev.turma)) continue;
    const key = getMergeKey(ev);
    let group = mergeGroups.get(key);
    if (!group) {
      group = { events: [], turmas: new Set(), weeks: new Set() };
      mergeGroups.set(key, group);
    }
    group.events.push(ev);
    if (ev.turma) group.turmas.add(ev.turma);
    for (const week of ev.weeks ?? []) group.weeks.add(week);
  }

  const result: PlacedEvent[] = [];
  for (const { events: groupEvents, turmas, weeks } of mergeGroups.values()) {
    const ev = groupEvents[0];
    if (!ev) continue;

    // Partial when the session's weeks don't cover every selected week. Skipped
    // when no weeks were selected or the events carry no week data.
    const isPartialWeeks =
      selectedWeekSet.size > 0 &&
      weeks.size > 0 &&
      [...selectedWeekSet].some((week) => !weeks.has(week));

    // Only partial sessions carry a range; a full-span session would just
    // repeat the whole selection on every card.
    const weekRangeLabel = isPartialWeeks
      ? formatWeekRanges(
          [...weeks]
            .map((week) => weekNumbers.get(week))
            .filter((n): n is number => n !== undefined),
        )
      : "";

    const dayCol = WEEKDAYS.indexOf(ev.weekday);
    if (dayCol < 0) continue;

    const visibleColIdx = visibleDayIndices.indexOf(dayCol);
    if (visibleColIdx < 0) continue;

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
        isPartialWeeks,
        weekRangeLabel,
      });
    }
  }

  return result;
}
