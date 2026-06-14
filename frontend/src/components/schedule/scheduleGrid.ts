import { hhmmToMinutes } from "@/utils/time";
import { WEEKDAYS } from "@/utils/weekdays";
import type { WeekGridEvent } from "./WeekGrid";

const SLOT_MINUTES = 30;

/** Quadratic-bezier path linking two segment points of the same event (#20). */
export function buildArcPath(x1: number, y1: number, x2: number, y2: number, minPeakY = 0): string {
  // Shallow bow: enough to clear the card tops, never so tall it reaches the
  // row/time-label above (PI ToDo #20 — the arc must not overlap other rows).
  const lift = Math.min(10, Math.max(6, Math.abs(x2 - x1) * 0.05));
  const peakY = Math.max(minPeakY, Math.min(y1, y2) - lift);
  const midX = (x1 + x2) / 2;
  return `M ${x1} ${y1} Q ${midX} ${peakY} ${x2} ${y2}`;
}

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

/** Marks rows carrying any event or mark, so empty rows can collapse (#13). */
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

/** Grid-row tracks: occupied rows stretch (`fullTrack`), empty ones collapse. */
export function computeRowHeights(
  rowOccupied: boolean[],
  fullTrack: string,
  compactPx: number,
): string[] {
  return rowOccupied.map((occupied) => (occupied ? fullTrack : `${compactPx}px`));
}

export type LaneSegment = { start: number; span: number; lane: number; laneCount: number };

export type LanedEvent = PlacedEvent & { segments: LaneSegment[] };

function eventColumns(p: PlacedEvent, turmasCount: number): number[] {
  const base = p.dayCol * turmasCount;
  const cols: number[] = [];
  for (const run of p.runs) {
    for (let i = run.start; i < run.start + run.span; i += 1) cols.push(base + i);
  }
  return cols;
}

/**
 * Side-by-side lanes per column (#24): within a column, overlapping events get
 * distinct lanes and a per-cluster lane count, so an event stays full width
 * where it has no conflict. Returns render `segments` and per-column
 * `colLaneCount` for sizing.
 */
export function assignLaneSegments(
  placed: PlacedEvent[],
  turmasCount: number,
  columnCount: number,
): { laned: LanedEvent[]; colLaneCount: number[] } {
  const perColumn: { index: number; rowStart: number; span: number }[][] = Array.from(
    { length: columnCount },
    () => [],
  );
  placed.forEach((p, index) => {
    for (const col of eventColumns(p, turmasCount)) {
      if (col >= 0 && col < columnCount) {
        perColumn[col]!.push({ index, rowStart: p.rowStart, span: p.span });
      }
    }
  });

  const laneOf = new Map<string, number>();
  const laneCountOf = new Map<string, number>();
  const colLaneCount = new Array<number>(columnCount).fill(0);
  for (let col = 0; col < columnCount; col += 1) {
    const list = perColumn[col]!;
    if (list.length === 0) continue;
    list.sort(
      (a, b) =>
        a.rowStart - b.rowStart ||
        b.span - a.span ||
        placed[a.index]!.ev.id.localeCompare(placed[b.index]!.ev.id),
    );
    let cluster: { index: number; rowStart: number; span: number; lane: number }[] = [];
    let clusterEnd = -Infinity;
    const flush = () => {
      if (cluster.length === 0) return;
      const laneCount = Math.max(...cluster.map((c) => c.lane)) + 1;
      for (const c of cluster) {
        laneOf.set(`${c.index}:${col}`, c.lane);
        laneCountOf.set(`${c.index}:${col}`, laneCount);
      }
      colLaneCount[col] = Math.max(colLaneCount[col]!, laneCount);
      cluster = [];
      clusterEnd = -Infinity;
    };
    for (const item of list) {
      if (item.rowStart >= clusterEnd) flush();
      const used = new Set<number>();
      for (const c of cluster) if (c.rowStart + c.span > item.rowStart) used.add(c.lane);
      let lane = 0;
      while (used.has(lane)) lane += 1;
      cluster.push({ ...item, lane });
      clusterEnd = Math.max(clusterEnd, item.rowStart + item.span);
    }
    flush();
  }

  const laned = placed.map((p, index) => {
    const dayBase = p.dayCol * turmasCount;
    const cols = eventColumns(p, turmasCount)
      .filter((c) => c >= 0 && c < columnCount)
      .sort((a, b) => a - b);
    const segments: LaneSegment[] = [];
    let current: LaneSegment | null = null;
    let prevCol = -2;
    for (const col of cols) {
      const lane = laneOf.get(`${index}:${col}`) ?? 0;
      const laneCount = laneCountOf.get(`${index}:${col}`) ?? 1;
      // Only full-width columns merge; laned columns stay separate cards.
      if (
        current &&
        laneCount === 1 &&
        current.laneCount === 1 &&
        col === prevCol + 1 &&
        current.lane === lane
      ) {
        current.span += 1;
      } else {
        if (current) segments.push(current);
        current = { start: col - dayBase, span: 1, lane, laneCount };
      }
      prevCol = col;
    }
    if (current) segments.push(current);
    return { ...p, segments };
  });

  return { laned, colLaneCount };
}

/**
 * Grid-column tracks (#14/#16/#24): empty column in a busy day → `minColPx`;
 * fully empty day → day-label width; otherwise `L`× the base width for L lanes.
 */
export function computeColumnWidths(
  colLaneCount: number[],
  turmasCount: number,
  resizedColPx: number | null,
  defaultColPx: number,
  minColPx: number,
  emptyDayTotalPx: number,
): string[] {
  const turmas = Math.max(turmasCount, 1);
  const emptyDayColPx = emptyDayTotalPx / turmas;
  const dayCount = Math.ceil(colLaneCount.length / turmas);
  const tracks: string[] = [];
  for (let day = 0; day < dayCount; day += 1) {
    const base = day * turmas;
    const dayHasEvents = colLaneCount.slice(base, base + turmas).some((l) => l > 0);
    for (let t = 0; t < turmas; t += 1) {
      const lanes = colLaneCount[base + t] ?? 0;
      if (!dayHasEvents) {
        tracks.push(`${emptyDayColPx}px`);
      } else if (lanes === 0) {
        tracks.push(`${minColPx}px`);
      } else if (resizedColPx != null) {
        tracks.push(`${resizedColPx * lanes}px`);
      } else {
        tracks.push(`minmax(${defaultColPx * lanes}px, ${lanes}fr)`);
      }
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
