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
};

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
): PlacedEvent[] {
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

  const mergeGroups = new Map<string, { events: WeekGridEvent[]; turmas: Set<string> }>();
  for (const ev of events) {
    if (activeTurmas.length > 0 && ev.turma && !activeTurmas.includes(ev.turma)) continue;
    const key = getMergeKey(ev);
    let group = mergeGroups.get(key);
    if (!group) {
      group = { events: [], turmas: new Set() };
      mergeGroups.set(key, group);
    }
    group.events.push(ev);
    if (ev.turma) group.turmas.add(ev.turma);
  }

  const result: PlacedEvent[] = [];
  for (const { events: groupEvents, turmas } of mergeGroups.values()) {
    const ev = groupEvents[0];
    if (!ev) continue;

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
      });
    }
  }

  return result;
}
