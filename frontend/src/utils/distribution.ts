import type { Weekday } from "@/types/project/weekday";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import { WEEKDAYS } from "./weekdays";

/** Canonical class-type order; unknown types fall after, alphabetically. */
const TYPE_ORDER = ["T", "TP", "TC", "OT", "P", "PL"];

function compareTypes(a: string, b: string): number {
  const ia = TYPE_ORDER.indexOf(a);
  const ib = TYPE_ORDER.indexOf(b);
  const ra = ia === -1 ? TYPE_ORDER.length : ia;
  const rb = ib === -1 ? TYPE_ORDER.length : ib;
  return ra - rb || a.localeCompare(b);
}

export interface DistributionRow {
  /** UC acronym (the table's row label). */
  acronym: string;
  /** Full UC name, for a tooltip/title. */
  name: string;
  /** `perDay[weekday][type]` = distinct sessions of that type that day. */
  perDay: Record<Weekday, Record<string, number>>;
}

export interface Distribution {
  /** Weekdays that carry at least one session, in canonical order. */
  weekdays: Weekday[];
  /** The class types present on each weekday (its sub-columns), type-ordered. */
  typesByDay: Record<Weekday, string[]>;
  rows: DistributionRow[];
}

/**
 * Builds the distribution table (PI ToDo #3): one row per UC; each weekday is
 * split into a sub-column per class type, holding the number of distinct
 * sessions. Counted by `sessionId` (turma-expanded events of one session count
 * once); weekday columns and their type sub-columns only include what's present.
 */
export function computeDistribution(events: WeekGridEvent[]): Distribution {
  const groups = new Map<
    string,
    { acronym: string; name: string; perDay: Map<Weekday, Map<string, Set<string>>> }
  >();
  const typeSetByDay = new Map<Weekday, Set<string>>();

  for (const ev of events) {
    const name = ev.uc ?? ev.title ?? "";
    const acronym = ev.title ?? name;
    const type = ev.type ?? "";
    let group = groups.get(name);
    if (!group) {
      group = { acronym, name, perDay: new Map() };
      groups.set(name, group);
    }
    let day = group.perDay.get(ev.weekday);
    if (!day) {
      day = new Map();
      group.perDay.set(ev.weekday, day);
    }
    let sessions = day.get(type);
    if (!sessions) {
      sessions = new Set();
      day.set(type, sessions);
    }
    sessions.add(ev.sessionId);

    let dayTypes = typeSetByDay.get(ev.weekday);
    if (!dayTypes) {
      dayTypes = new Set();
      typeSetByDay.set(ev.weekday, dayTypes);
    }
    dayTypes.add(type);
  }

  const weekdays = WEEKDAYS.filter((weekday) => typeSetByDay.has(weekday));
  const typesByDay = {} as Record<Weekday, string[]>;
  for (const weekday of WEEKDAYS) {
    typesByDay[weekday] = [...(typeSetByDay.get(weekday) ?? [])].sort(compareTypes);
  }

  const rows = [...groups.values()]
    .map<DistributionRow>((group) => {
      const perDay = {} as Record<Weekday, Record<string, number>>;
      for (const weekday of WEEKDAYS) {
        const byType = group.perDay.get(weekday);
        const counts: Record<string, number> = {};
        if (byType) for (const [type, sessions] of byType) counts[type] = sessions.size;
        perDay[weekday] = counts;
      }
      return { acronym: group.acronym, name: group.name, perDay };
    })
    .sort((a, b) => a.acronym.localeCompare(b.acronym));

  return { weekdays, typesByDay, rows };
}
