import { useMemo } from "react";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import type { DegreeDetail } from "@/types/project/degree";
import type { WeekBlockResponse } from "@/types/project/sessions";
import type { YearDetail } from "@/types/project/year";
import { formatWeekRange } from "@/utils/date";
import {
  sessionToEvents,
  sortValuesByReference,
  type ScheduleFilters,
} from "@/utils/scheduleEvents";
import { WEEKDAYS, WEEKDAY_LABELS_LONG } from "@/utils/weekdays";
import { formatWeekRanges } from "./scheduleGrid";
import type { TurnoTurmaGroup } from "./TurnoTurmaDropdown";
import type { DropdownOption } from "./types";

/**
 * Resolves the selected ano values from the raw `anos` state and the year
 * values the active degree actually offers. When nothing valid is selected it
 * falls back to the degree's first year. Exported so the page can derive the
 * year *before* calling this hook (it needs the value to wire up the
 * year-detail query) without re-implementing the rule and risking drift.
 */
export function deriveEffectiveAnos(curso: string, anos: string[], yearValues: string[]): string[] {
  if (!curso) return [];
  if (yearValues.length === 0) return anos;
  const filtered = anos.filter((ano) => yearValues.includes(ano));
  const firstYear = yearValues[0];
  return filtered.length > 0 ? filtered : firstYear ? [firstYear] : [];
}

/**
 * Orders turno values numerically, except turno 0 — the "no fixed shift"
 * bucket — which always sorts last (PI ToDo #25).
 */
export function compareTurnos(left: string, right: string): number {
  const leftValue = Number(left) === 0 ? Number.POSITIVE_INFINITY : Number(left);
  const rightValue = Number(right) === 0 ? Number.POSITIVE_INFINITY : Number(right);
  return leftValue - rightValue;
}

/**
 * Orders turma codes naturally so the numeric suffix sorts as a number
 * (...08 < ...09 < ...10), not lexically (which would put ...10 before ...8).
 */
export function compareTurmas(left: string, right: string): number {
  return left.localeCompare(right, undefined, { numeric: true });
}

/** The single ano value that drives the selected-year query. */
export function pickSelectedYearNumber(
  curso: string,
  anos: string[],
  yearValues: string[],
): string {
  return deriveEffectiveAnos(curso, anos, yearValues)[0] ?? "";
}

interface UseScheduleFiltersParams {
  /** Whether the user has actually picked a curso yet. */
  curso: string;
  /** Selected ano values (raw state). */
  anos: string[];
  /** Selected UCs (raw state). */
  ucs: string[];
  /** Selected turnos (raw state). */
  turnos: string[];
  /** Selected turmas (raw state). */
  turmas: string[];
  /** Selected weekday keys (raw state). */
  dias: string[];
  /** Selected week-block values (raw state). */
  semanas: string[];
  /** Detail for the active degree, used for year list + year options. */
  selectedDegree: DegreeDetail | undefined;
  /** Detail for the active year, used for subject + class lists. */
  selectedYearDetail: YearDetail | undefined;
  /** sessionsQuery.data — undefined while the sessions query is loading. */
  selectedYearWeeks: WeekBlockResponse[] | undefined;
  /**
   * Whether the selected year has any Saturday sessions, supplied by the
   * dedicated probe query in the page so it stays cached across filter
   * changes (otherwise the main sessions query would have to smuggle
   * saturday into every request to probe for it).
   */
  hasSaturdaySessions: boolean;
}

/**
 * Computes every cascading derivation needed by the schedule page: each
 * `effective*` fallback, the navbar option lists, the API filter ids for the
 * sessions query, and the final scheduleEvents list. The raw filter state
 * and the side-effecty cascade hooks (useTurnoTurmaSync, useScheduleViewUrl)
 * stay in the page, which keeps the data flow one-way: page state +
 * query results → hook derivations.
 */
export function useScheduleFilters({
  curso,
  anos,
  ucs,
  turnos,
  turmas,
  dias,
  semanas,
  selectedDegree,
  selectedYearDetail,
  selectedYearWeeks,
  hasSaturdaySessions,
}: UseScheduleFiltersParams) {
  // --- selectedDegree-derived references --------------------------------
  const selectedDegreeYearValues = useMemo(
    () => selectedDegree?.years.map((year) => String(year.number)) ?? [],
    [selectedDegree],
  );

  const effectiveAnos = useMemo(
    () => deriveEffectiveAnos(curso, anos, selectedDegreeYearValues),
    [anos, curso, selectedDegreeYearValues],
  );

  const selectedYearNumber = effectiveAnos[0] ?? "";

  // --- selectedYearDetail-derived references ----------------------------
  const selectedYearSubjects = useMemo(
    () => selectedYearDetail?.subjects ?? [],
    [selectedYearDetail],
  );
  const selectedYearClasses = useMemo(
    () => selectedYearDetail?.classes ?? [],
    [selectedYearDetail],
  );

  const ucOptions = useMemo(
    () =>
      selectedYearSubjects
        .slice()
        .sort((a, b) => a.acronym.localeCompare(b.acronym))
        .map((subject) => subject.name),
    [selectedYearSubjects],
  );

  const classesByTurno = useMemo(() => {
    const groups = new Map<string, typeof selectedYearClasses>();
    for (const classItem of selectedYearClasses) {
      const turno = String(classItem.shift);
      const current = groups.get(turno) ?? [];
      groups.set(turno, [...current, classItem]);
    }
    return groups;
  }, [selectedYearClasses]);

  const turnoTurmaGroups = useMemo<TurnoTurmaGroup[]>(() => {
    const byTurno = [...classesByTurno.entries()].sort((a, b) => compareTurnos(a[0], b[0]));
    return byTurno.map(([turno, classes]) => ({
      turno,
      label: `Turno ${turno}`,
      turmas: classes
        .slice()
        .sort((a, b) => compareTurmas(a.code, b.code))
        .map((classItem) => classItem.code),
    }));
  }, [classesByTurno]);

  const turnoOrder = useMemo(
    () => turnoTurmaGroups.map((group) => group.turno),
    [turnoTurmaGroups],
  );
  const turmaOrder = useMemo(
    () => turnoTurmaGroups.flatMap((group) => group.turmas),
    [turnoTurmaGroups],
  );
  const turmaShifts = useMemo(
    () =>
      Object.fromEntries(selectedYearClasses.map((classItem) => [classItem.code, classItem.shift])),
    [selectedYearClasses],
  );

  // --- sessions-derived references --------------------------------------
  // 1-based ordinal of every week across the whole year, in chronological
  // order (ISO date strings sort chronologically). Lets the grid label a
  // partial session with its semester week range (e.g. "1-7"), and prefixes
  // each week-selector option with its week number(s).
  const weekNumbers = useMemo(() => {
    const sorted = [...new Set((selectedYearWeeks ?? []).flatMap((block) => block.weeks))].sort();
    return new Map(sorted.map((week, index) => [week, index + 1]));
  }, [selectedYearWeeks]);

  const weekOptions = useMemo<DropdownOption[]>(
    () =>
      (selectedYearWeeks ?? []).flatMap((block) => {
        if (block.weeks.length === 0) return [];
        const numbers = formatWeekRanges(
          block.weeks
            .map((week) => weekNumbers.get(week))
            .filter((n): n is number => n !== undefined),
        );
        const dateRange = formatWeekRange(block.weeks);
        const weekWord = block.weeks.length === 1 ? "Semana" : "Semanas";
        return [
          {
            value: block.weeks.join("|"),
            // Week number(s) lead; the date range drops to the secondary line.
            // "Semanas 3-4" already conveys the count, so no "N semanas" suffix.
            label: numbers ? `${weekWord} ${numbers}` : dateRange,
            secondaryText: numbers
              ? dateRange
              : block.weeks.length === 1
                ? undefined
                : `${block.weeks.length} semanas`,
          },
        ];
      }),
    [selectedYearWeeks, weekNumbers],
  );

  const allWeekValues = useMemo(() => weekOptions.map((option) => option.value), [weekOptions]);

  // --- effective filters -----------------------------------------------
  const effectiveUcs = useMemo(
    () => (curso ? (ucs.length > 0 ? ucs.filter((uc) => ucOptions.includes(uc)) : ucOptions) : []),
    [curso, ucOptions, ucs],
  );

  const effectiveTurnos = useMemo(() => {
    if (!curso) return [];
    const validSelected = turnos.filter((turno) => turnoOrder.includes(turno));
    const fallback = validSelected.length > 0 ? validSelected : turnoOrder;
    return sortValuesByReference(fallback, turnoOrder);
  }, [curso, turnoOrder, turnos]);

  const effectiveTurmas = useMemo(() => {
    if (!curso) return [];
    const validSelected = turmas.filter((turma) => turmaOrder.includes(turma));
    const fallback = validSelected.length > 0 ? validSelected : turmaOrder;
    return sortValuesByReference(fallback, turmaOrder);
  }, [curso, turmaOrder, turmas]);

  // Saturday is only shown when the selected year actually has sessions on it.
  const effectiveDias = useMemo(
    () => (hasSaturdaySessions ? dias : dias.filter((day) => day !== "saturday")),
    [dias, hasSaturdaySessions],
  );

  const effectiveSemanas = useMemo(() => {
    if (!curso) return [];
    const validSelected = semanas.filter((semana) => allWeekValues.includes(semana));
    return validSelected.length > 0 ? validSelected : allWeekValues;
  }, [allWeekValues, curso, semanas]);

  // --- API-side filters -------------------------------------------------
  const subjectIdsFilter = useMemo(() => {
    if (ucs.length === 0) return [];
    const names = new Set(ucs);
    return selectedYearSubjects
      .filter((subject) => names.has(subject.name))
      .map((subject) => subject.id);
  }, [selectedYearSubjects, ucs]);

  const classIdsFilter = useMemo(() => {
    if (turmas.length === 0) return [];
    const codes = new Set(turmas);
    return selectedYearClasses
      .filter((classItem) => codes.has(classItem.code))
      .map((classItem) => classItem.id);
  }, [selectedYearClasses, turmas]);

  const weekdayFilter = useMemo(() => {
    if (dias.length === 0 || dias.length === WEEKDAYS.length) return [];
    return dias;
  }, [dias]);

  // --- schedule events --------------------------------------------------
  const activeWeekBlocks = useMemo(() => {
    const blocks = selectedYearWeeks ?? [];
    if (blocks.length === 0) return [];
    const selectedValues = new Set(effectiveSemanas);
    const filtered = blocks.filter((block) => selectedValues.has(block.weeks.join("|")));
    return filtered.length > 0 ? filtered : blocks;
  }, [effectiveSemanas, selectedYearWeeks]);

  const scheduleEvents = useMemo<WeekGridEvent[]>(() => {
    const filters: ScheduleFilters = {
      ucs: new Set(effectiveUcs),
      turnos: new Set(effectiveTurnos),
      turmas: new Set(effectiveTurmas),
      dias: new Set(effectiveDias),
    };
    return activeWeekBlocks.flatMap((block) =>
      block.sessions.flatMap((session) => sessionToEvents(session, filters, block.weeks)),
    );
  }, [activeWeekBlocks, effectiveDias, effectiveTurmas, effectiveTurnos, effectiveUcs]);

  // Union of every week across the active blocks: the full set of weeks the
  // user is currently viewing. A rendered session whose weeks are a strict
  // subset of this only runs in part of the selection.
  const selectedWeeks = useMemo(
    () => [...new Set(activeWeekBlocks.flatMap((block) => block.weeks))],
    [activeWeekBlocks],
  );

  // --- secondary dropdown options ---------------------------------------
  const yearOptions = useMemo<DropdownOption[]>(
    () =>
      selectedDegree?.years.map((year) => ({
        value: String(year.number),
        label: `${year.number}º Ano`,
        secondaryText: `${year.subjects} UCs · ${year.classes} turmas`,
      })) ?? [],
    [selectedDegree],
  );

  const dayOptions = useMemo<DropdownOption[]>(() => {
    const options: DropdownOption[] = WEEKDAYS.map((weekday) => ({
      value: weekday,
      label: WEEKDAY_LABELS_LONG[weekday],
    }));
    return hasSaturdaySessions ? options : options.filter((option) => option.value !== "saturday");
  }, [hasSaturdaySessions]);

  return {
    // effective values for read/display
    effectiveAnos,
    effectiveUcs,
    effectiveTurnos,
    effectiveTurmas,
    effectiveDias,
    effectiveSemanas,
    selectedYearNumber,
    // year-detail-derived references (consumed by cascade hooks too)
    selectedYearSubjects,
    selectedYearClasses,
    ucOptions,
    turnoOrder,
    turmaOrder,
    turmaShifts,
    turnoTurmaGroups,
    weekOptions,
    yearOptions,
    dayOptions,
    allWeekValues,
    // API filters for the sessions query
    subjectIdsFilter,
    classIdsFilter,
    weekdayFilter,
    // schedule output
    scheduleEvents,
    selectedWeeks,
    weekNumbers,
  };
}
