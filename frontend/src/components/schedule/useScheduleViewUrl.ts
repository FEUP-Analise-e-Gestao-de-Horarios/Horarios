import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { sortValuesByReference } from "@/utils/scheduleEvents";
import {
  SCHEDULE_VIEW_DAYS,
  degreeKey,
  encodeScheduleView,
  parseScheduleView,
  unpackSections,
} from "@/utils/scheduleView";

type DegreeOption = { id: string; acronym: string };
type SyncedClass = { code: string; shift: number };

interface UseScheduleViewUrlParams {
  degrees: DegreeOption[] | undefined;
  /** Whether the selected year's detail (subjects/classes) has loaded. */
  hasYearDetail: boolean;
  /** Whether the selected year's week blocks query has resolved. */
  hasYearWeeks: boolean;
  selectedYearClasses: SyncedClass[];
  ucOptions: string[];
  turnoOrder: string[];
  turmaOrder: string[];
  allWeekValues: string[];
  activeDegreeId: string;
  ano: string;
  ucs: string[];
  turmas: string[];
  dias: string[];
  semanas: string[];
  setCurso: (value: string) => void;
  setAnos: (value: string[]) => void;
  setUcs: (value: string[]) => void;
  setTurnos: (value: string[]) => void;
  setTurmas: (value: string[]) => void;
  setDias: (value: string[]) => void;
  setSemanas: (value: string[]) => void;
}

/**
 * Owns the two-way binding between the schedule filters and the `?view=` URL
 * parameter:
 *
 * - **Hydration** — on first load, decodes `?view=` into the filter state. It
 *   runs as a small phased state machine (`hydrationPhaseRef`) because the
 *   reference lists it decodes against — subjects, turmas, week blocks — only
 *   become available once the degree/year queries resolve over several
 *   renders.
 * - **Serialization** — once hydrated, re-encodes the filters back into
 *   `?view=` whenever they change.
 *
 * Returns `isHydrated` so callers can gate behaviour on the initial decode.
 */
export function useScheduleViewUrl({
  degrees,
  hasYearDetail,
  hasYearWeeks,
  selectedYearClasses,
  ucOptions,
  turnoOrder,
  turmaOrder,
  allWeekValues,
  activeDegreeId,
  ano,
  ucs,
  turmas,
  dias,
  semanas,
  setCurso,
  setAnos,
  setUcs,
  setTurnos,
  setTurmas,
  setDias,
  setSemanas,
}: UseScheduleViewUrlParams): { isHydrated: boolean } {
  const [searchParams, setSearchParams] = useSearchParams();
  const [initialView] = useState<string | null>(() => searchParams.get("view"));
  const hydrationPhaseRef = useRef(0);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    if (isHydrated) return;
    if (!degrees) return;

    if (!initialView) {
      if (degrees.some((degree) => degree.acronym === "L.EIC")) {
        setCurso("L.EIC");
        setAnos(["1"]);
      }
      setIsHydrated(true);
      return;
    }

    const parsed = parseScheduleView(initialView);
    if (!parsed.degreeKey) {
      setIsHydrated(true);
      return;
    }

    if (hydrationPhaseRef.current < 1) {
      const matchingDegree = degrees.find((degree) => degreeKey(degree.id) === parsed.degreeKey);
      if (!matchingDegree) {
        setIsHydrated(true);
        return;
      }
      setCurso(matchingDegree.acronym);
      if (parsed.year) setAnos([parsed.year]);
      hydrationPhaseRef.current = 1;
      if (!parsed.bytes || parsed.bytes.length === 0) {
        setIsHydrated(true);
        return;
      }
    }

    if (!parsed.bytes) {
      setIsHydrated(true);
      return;
    }

    if (hydrationPhaseRef.current < 2) {
      if (!hasYearDetail) return;
      const sections = unpackSections(parsed.bytes, [
        { ref: ucOptions },
        { ref: turmaOrder },
        { ref: [...SCHEDULE_VIEW_DAYS] },
        { ref: allWeekValues },
      ]);
      const ucsSection = sections[0];
      const turmasSection = sections[1];
      const diasSection = sections[2];
      if (ucsSection && !ucsSection.isAll) setUcs(ucsSection.values);
      if (turmasSection) {
        const decodedTurmas = turmasSection.isAll ? [] : turmasSection.values;
        setTurmas(decodedTurmas);
        const shifts = new Set<string>();
        for (const classItem of selectedYearClasses) {
          if (decodedTurmas.includes(classItem.code)) shifts.add(String(classItem.shift));
        }
        setTurnos(sortValuesByReference([...shifts], turnoOrder));
      }
      if (diasSection) {
        setDias(diasSection.isAll ? [...SCHEDULE_VIEW_DAYS] : diasSection.values);
      }
      hydrationPhaseRef.current = 2;
    }

    if (hydrationPhaseRef.current < 3) {
      if (!hasYearWeeks) return;
      if (allWeekValues.length > 0) {
        const sections = unpackSections(parsed.bytes, [
          { ref: ucOptions },
          { ref: turmaOrder },
          { ref: [...SCHEDULE_VIEW_DAYS] },
          { ref: allWeekValues },
        ]);
        const semanasSection = sections[3];
        if (semanasSection && !semanasSection.isAll) setSemanas(semanasSection.values);
      }
      hydrationPhaseRef.current = 3;
      setIsHydrated(true);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [
    isHydrated,
    initialView,
    degrees,
    hasYearDetail,
    hasYearWeeks,
    selectedYearClasses,
    ucOptions,
    turmaOrder,
    turnoOrder,
    allWeekValues,
    setCurso,
    setAnos,
    setUcs,
    setTurnos,
    setTurmas,
    setDias,
    setSemanas,
  ]);

  useEffect(() => {
    if (!isHydrated) return;

    const newView = encodeScheduleView(
      { degreeId: activeDegreeId, ano, ucs, turmas, dias, semanas },
      { ucOrder: ucOptions, turmaOrder, weekOrder: allWeekValues },
    );

    const currentView = searchParams.get("view") ?? "";
    if (newView === currentView) return;

    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (newView) next.set("view", newView);
        else next.delete("view");
        return next;
      },
      { replace: true },
    );
  }, [
    isHydrated,
    activeDegreeId,
    ano,
    ucs,
    turmas,
    dias,
    semanas,
    ucOptions,
    turmaOrder,
    allWeekValues,
    searchParams,
    setSearchParams,
  ]);

  return { isHydrated };
}
