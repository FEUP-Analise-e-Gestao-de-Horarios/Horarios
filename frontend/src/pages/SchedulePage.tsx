import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import type { ClassBase } from "@/types/project/class";
import type { Weekday } from "@/types/project/weekday";
import WeekGrid, { type WeekGridEvent } from "@/components/schedule/WeekGrid";
import EditEventDrawer from "@/components/schedule/EditEventDrawer";
import ConflictsDrawer from "@/components/schedule/ConflictsDrawer";
import DistributionModal from "@/components/schedule/DistributionModal";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { slotOverlapsMarks } from "@/components/schedule/scheduleGrid";
import { useEventUnavailability } from "@/components/schedule/useEventUnavailability";
import { useEventEditor } from "@/components/schedule/useEventEditor";
import {
  eventDrawerFormReducer,
  useEventDrawerForm,
  type EventDrawerFormAction,
  type EventDrawerFormState,
} from "@/components/schedule/useEventDrawerForm";
import {
  applySessionOverrides,
  buildSessionOverride,
  useLocalSessionEdits,
  type OverrideLookups,
  type SessionOverride,
} from "@/components/schedule/useLocalSessionEdits";
import { useProjectAccess } from "@/api/hooks/project/access";
import { useParallelSessionsReminder } from "@/components/parallel/useParallelSessionsReminder";
import {
  pickSelectedYearNumber,
  useScheduleFilters,
} from "@/components/schedule/useScheduleFilters";
import { useScheduleOptions } from "@/components/schedule/useScheduleOptions";
import { useScheduleViewUrl } from "@/components/schedule/useScheduleViewUrl";
import { createSubjectPalette } from "@/components/schedule/subjectColors";
import { useTurnoTurmaSync } from "@/components/schedule/useTurnoTurmaSync";
import { useProjectDegree, useProjectDegrees } from "@/api/hooks/project/degree";
import { useProjectRooms } from "@/api/hooks/project/room";
import { useProjectTeachers } from "@/api/hooks/project/teacher";
import { useProjectSessions } from "@/api/hooks/project/sessions";
import { useProjectConflicts } from "@/api/hooks/project/conflicts";
import { useProjectYear } from "@/api/hooks/project/year";
import { hhmmToMinutes, minutesToHhmm, timeToHhmm } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_LONG, WEEKDAY_LABELS_UPPER } from "@/utils/weekdays";

// Same bounds the drawer's own time field clamps to.
const MIN_PLACEMENT_MINUTES = 7 * 60;
const MAX_PLACEMENT_MINUTES = 19 * 60 + 30;

function eventLabel(ev: WeekGridEvent): string {
  return ev.title ?? ev.uc ?? "Aula";
}

function slotLabel(weekday: Weekday, hhmm: number): string {
  return `${WEEKDAY_LABELS_LONG[weekday]} às ${String(Math.floor(hhmm / 100)).padStart(2, "0")}:${String(hhmm % 100).padStart(2, "0")}`;
}

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const {
    project,
    isPending: isProjectPending,
    isError: isProjectError,
  } = useProjectAccess(projectId);
  useParallelSessionsReminder(project);
  const { data: degrees } = useProjectDegrees(projectId ?? "");
  const { data: teachers } = useProjectTeachers(projectId ?? "");
  const { data: rooms } = useProjectRooms(projectId ?? "");

  const { courseOptions, teacherOptions, roomOptions } = useScheduleOptions({
    degrees,
    teachers,
    rooms,
  });

  // --- filter state ----------------------------------------------------
  const [curso, setCurso] = useState("");
  const [anos, setAnos] = useState<string[]>([]);
  const [ucs, setUcs] = useState<string[]>([]);
  const [turnos, setTurnos] = useState<string[]>([]);
  const [turmas, setTurmas] = useState<string[]>([]);
  const [semanas, setSemanas] = useState<string[]>([]);
  const [dias, setDias] = useState<string[]>([...WEEKDAYS]);

  const eventEditor = useEventEditor();
  const [isConflictsDrawerOpen, setIsConflictsDrawerOpen] = useState(false);
  const [isDistributionOpen, setIsDistributionOpen] = useState(false);

  // In-memory event edits: not persisted, cleared on course change. The
  // drawer's form lives here (not inside the drawer) so the grid can preview
  // it live and a placement click can write straight into it.
  const localEdits = useLocalSessionEdits();
  const [formState, dispatchForm] = useEventDrawerForm(eventEditor.editingEvent);
  const lastEditingEventRef = useRef(eventEditor.editingEvent);
  useEffect(() => {
    if (lastEditingEventRef.current !== eventEditor.editingEvent) {
      lastEditingEventRef.current = eventEditor.editingEvent;
      dispatchForm({ type: "reset", event: eventEditor.editingEvent });
    }
  }, [eventEditor.editingEvent, dispatchForm]);

  // Click-to-place mode for moving the open event on the grid. On by default
  // so clicking a slot moves the event without first toggling; the drawer has
  // a button to turn it off. A placement click commits on its own — dropdown
  // and stepper edits inside the drawer stay a draft until Guardar.
  const [placementMode, setPlacementMode] = useState(false);
  const openEditor = (event: WeekGridEvent) => {
    setPlacementMode(true);
    eventEditor.openEditor(event, true);
  };
  const closeEditor = () => {
    setPlacementMode(false);
    eventEditor.closeEditor();
  };

  // Sessions marked with shift-click for a bulk move; cleared on a course
  // change or once the move is applied.
  const [selectedSessionIds, setSelectedSessionIds] = useState<Set<string>>(new Set());
  const toggleBulkSelection = (sessionId: string) => {
    setSelectedSessionIds((prev) => {
      const next = new Set(prev);
      if (next.has(sessionId)) next.delete(sessionId);
      else next.add(sessionId);
      return next;
    });
  };

  const canShowSchedule = curso !== "";

  // --- query chain: degree → year → sessions ---------------------------
  const activeDegree = useMemo(
    () => degrees?.find((degree) => degree.acronym === curso) ?? null,
    [curso, degrees],
  );
  const { data: selectedDegree } = useProjectDegree(projectId ?? "", activeDegree?.id ?? "");

  const yearValues = useMemo(
    () => selectedDegree?.years.map((year) => String(year.number)) ?? [],
    [selectedDegree],
  );
  const selectedYearNumber = pickSelectedYearNumber(curso, anos, yearValues);
  const selectedYear = useMemo(
    () => selectedDegree?.years.find((year) => String(year.number) === selectedYearNumber) ?? null,
    [selectedDegree, selectedYearNumber],
  );

  const { data: selectedYearDetail } = useProjectYear(projectId ?? "", selectedYear?.id ?? "");
  const yearConflictsQuery = useProjectConflicts(projectId ?? "", "year", {
    yearId: selectedYear?.id ?? "",
  });
  const yearConflicts = yearConflictsQuery.data ?? [];

  // Sessions query needs subject/class/weekday ids derived from the year
  // detail. Compute them inline so we can call the sessions query before the
  // filters hook (which will re-derive the same values).
  const sessionApiFilters = useMemo(() => {
    const subjects = selectedYearDetail?.subjects ?? [];
    const classes = selectedYearDetail?.classes ?? [];
    const subjectIds =
      ucs.length === 0
        ? []
        : (() => {
            const names = new Set(ucs);
            return subjects
              .filter((subject) => names.has(subject.name))
              .map((subject) => subject.id);
          })();
    const classIds =
      turmas.length === 0
        ? []
        : (() => {
            const codes = new Set(turmas);
            return classes.filter((classItem) => codes.has(classItem.code)).map((c) => c.id);
          })();
    const weekdays = dias.length === 0 || dias.length === WEEKDAYS.length ? [] : dias;
    return { subjectIds, classIds, weekdays };
  }, [dias, selectedYearDetail, turmas, ucs]);

  const sessionsQuery = useProjectSessions(projectId ?? "", {
    yearId: selectedYear?.id ?? "",
    ...sessionApiFilters,
  });

  // Saturday-availability is keyed only on the year, so it stays cached
  // across UC/turma/day filter changes. Probing it via the main sessions
  // query would re-run the probe on every filter change.
  const saturdayProbeQuery = useProjectSessions(projectId ?? "", {
    yearId: selectedYear?.id ?? "",
    subjectIds: [],
    classIds: [],
    weekdays: ["saturday"],
  });

  const hasSaturdaySessions = useMemo(
    () =>
      (saturdayProbeQuery.data ?? []).some((block) =>
        block.sessions.some((session) => session.weekday === "saturday"),
      ),
    [saturdayProbeQuery.data],
  );

  // Resolves the drawer form's ids/codes back to session entities.
  const overrideLookups = useMemo<OverrideLookups>(
    () => ({
      teachersById: new Map((teachers ?? []).map((teacher) => [teacher.id, teacher])),
      roomsById: new Map((rooms ?? []).map((room) => [room.id, room])),
      subjectsByName: new Map(
        (selectedYearDetail?.subjects ?? []).map((subject) => [subject.name, subject]),
      ),
      classesByCode: new Map(
        (selectedYearDetail?.classes ?? []).map((classItem) => [classItem.code, classItem]),
      ),
    }),
    [teachers, rooms, selectedYearDetail],
  );

  // Availability (#5) for whatever is currently selected in the drawer —
  // including an unsaved docente/sala/turma change — not just the event's
  // original ones, so the red-block overlay and the conflict check below stay
  // accurate while editing. Covers teacher, room AND turma red blocks.
  const draftClassIds = useMemo(
    () =>
      formState.selectedTurmasOverride
        .map((code) => overrideLookups.classesByCode.get(code)?.id)
        .filter((id): id is string => !!id),
    [formState.selectedTurmasOverride, overrideLookups],
  );
  const unavailabilityMarks = useEventUnavailability(
    projectId ?? "",
    eventEditor.isOpen ? formState.selectedDocenteOverride : [],
    eventEditor.isOpen ? formState.selectedSalaOverride : [],
    eventEditor.isOpen ? draftClassIds : [],
  );

  // Whether a draft/target turma selection differs from the event's own.
  const turmaChangedFrom = (editing: WeekGridEvent, selectedTurmas: string[]): boolean => {
    const originalTurmas = editing.classCodes ?? [];
    return (
      selectedTurmas.length !== originalTurmas.length ||
      selectedTurmas.some((code) => !originalTurmas.includes(code))
    );
  };

  // Warns (never blocks) when the draft moves the open event to a different
  // turma or into a slot its docente, sala or turma isn't available for — the
  // only two cases worth flagging.
  const warningFor = (editing: WeekGridEvent, nextState: EventDrawerFormState): string | null => {
    if (turmaChangedFrom(editing, nextState.selectedTurmasOverride))
      return "está a passar para uma turma diferente";
    const conflict = slotOverlapsMarks(
      nextState.selectedWeekday,
      timeToHhmm(nextState.startTime),
      nextState.durationSlots,
      unavailabilityMarks,
    );
    if (conflict) return "o novo horário está fora da disponibilidade do docente, sala ou turma";
    return null;
  };

  // Live, non-committing warning as the user builds up a draft in the drawer.
  // Raw typing in the start-time field is skipped — it's mid-edit, not a real
  // value yet.
  const dispatchFormAndWarn = (action: EventDrawerFormAction) => {
    dispatchForm(action);
    if (action.type === "setStartTime") return;
    const editing = eventEditor.editingEvent;
    if (!editing) return;
    const nextState = eventDrawerFormReducer(formState, action);
    const toastId = `schedule-warning-${editing.sessionId}`;
    const warning = warningFor(editing, nextState);
    if (warning) toast(`${eventLabel(editing)} — aviso`, { id: toastId, description: warning });
    else toast.dismiss(toastId);
  };

  // Every committing action (grid move, swap, Guardar) shows one toast naming
  // what changed and offering to undo it. A stable id per session set means
  // rapid repeats on the same session(s) update in place; different sessions
  // stack instead of replacing each other.
  const notifyChange = (opts: {
    sessionIds: string[];
    title: string;
    description: string;
    undo: () => void;
  }) => {
    toast(opts.title, {
      id: `schedule-change-${opts.sessionIds.join("-")}`,
      description: opts.description,
      action: { label: "Desfazer", onClick: opts.undo },
    });
  };

  // Grid placement click: commits the slot (weekday/start/duration) plus,
  // when the click landed in a turma the event didn't already have, the
  // turma reassignment too — never any other docente/sala/uc draft that
  // might also be pending, so it can't accidentally save an unrelated
  // unsaved field.
  const applyPlacement = (editing: WeekGridEvent, nextState: EventDrawerFormState) => {
    const previous = localEdits.overrides[editing.sessionId];
    const nextHhmm = timeToHhmm(nextState.startTime);
    const turmaChanged = turmaChangedFrom(editing, nextState.selectedTurmasOverride);
    localEdits.commit(editing.sessionId, {
      weekday: nextState.selectedWeekday,
      start_time: nextHhmm,
      duration: nextState.durationSlots,
      ...(turmaChanged
        ? {
            classes: nextState.selectedTurmasOverride
              .map((code) => overrideLookups.classesByCode.get(code))
              .filter((classItem): classItem is ClassBase => !!classItem),
          }
        : {}),
    });
    const warning = warningFor(editing, nextState);
    const move = `${slotLabel(editing.weekday, editing.startTime)} → ${slotLabel(nextState.selectedWeekday, nextHhmm)}`;
    notifyChange({
      sessionIds: [editing.sessionId],
      title: eventLabel(editing),
      description: warning ? `${move} — ${warning}.` : `${move}.`,
      undo: () => localEdits.replace(editing.sessionId, previous),
    });
  };

  // Clicking a second, different event while one is open trades their slots
  // instead of retargeting the drawer to the new one.
  const swapEvents = (a: WeekGridEvent, b: WeekGridEvent) => {
    const previousA = localEdits.overrides[a.sessionId];
    const previousB = localEdits.overrides[b.sessionId];
    localEdits.commit(a.sessionId, {
      weekday: b.weekday,
      start_time: b.startTime,
      duration: b.duration,
    });
    localEdits.commit(b.sessionId, {
      weekday: a.weekday,
      start_time: a.startTime,
      duration: a.duration,
    });
    notifyChange({
      sessionIds: [a.sessionId, b.sessionId],
      title: "Aulas trocadas",
      description: `${eventLabel(a)} (${slotLabel(a.weekday, a.startTime)}) ↔ ${eventLabel(b)} (${slotLabel(b.weekday, b.startTime)})`,
      undo: () => {
        localEdits.replace(a.sessionId, previousA);
        localEdits.replace(b.sessionId, previousB);
      },
    });
    closeEditor();
  };

  // Moves every selected session by the same day/time offset the anchor
  // (first selected) needs to reach the clicked slot. Each session clamps to
  // the grid's own bounds independently, so the offset can't push one off the
  // edge even if it fits for the others.
  const applyBulkMove = (
    targetWeekday: Weekday,
    targetMinutes: number,
    selected: WeekGridEvent[],
  ) => {
    const anchor = selected[0];
    if (!anchor) return;
    const dayDelta = WEEKDAYS.indexOf(targetWeekday) - WEEKDAYS.indexOf(anchor.weekday);
    const minuteDelta = targetMinutes - hhmmToMinutes(anchor.startTime);

    const previousBySession = new Map<string, SessionOverride | undefined>();
    const moves: string[] = [];

    for (const ev of selected) {
      const dayIndex = Math.min(
        WEEKDAYS.length - 1,
        Math.max(0, WEEKDAYS.indexOf(ev.weekday) + dayDelta),
      );
      const newWeekday = WEEKDAYS[dayIndex]!;
      const newMinutes = Math.min(
        MAX_PLACEMENT_MINUTES,
        Math.max(MIN_PLACEMENT_MINUTES, hhmmToMinutes(ev.startTime) + minuteDelta),
      );
      const newHhmm = minutesToHhmm(newMinutes);
      previousBySession.set(ev.sessionId, localEdits.overrides[ev.sessionId]);
      localEdits.commit(ev.sessionId, {
        weekday: newWeekday,
        start_time: newHhmm,
        duration: ev.duration,
      });
      moves.push(
        `${eventLabel(ev)}: ${slotLabel(ev.weekday, ev.startTime)} → ${slotLabel(newWeekday, newHhmm)}`,
      );
    }

    notifyChange({
      sessionIds: selected.map((ev) => ev.sessionId),
      title: `${selected.length} aulas movidas`,
      description: moves.join(" · "),
      undo: () => {
        for (const [sessionId, previous] of previousBySession)
          localEdits.replace(sessionId, previous);
      },
    });
    setSelectedSessionIds(new Set());
  };

  const handleEventClick = (clicked: WeekGridEvent, domEvent: MouseEvent<HTMLButtonElement>) => {
    if (domEvent.shiftKey) {
      toggleBulkSelection(clicked.sessionId);
      return;
    }
    const editing = eventEditor.isOpen ? eventEditor.editingEvent : null;
    if (editing && editing.sessionId !== clicked.sessionId) {
      swapEvents(editing, clicked);
      return;
    }
    openEditor(clicked);
  };

  const saveEdit = () => {
    const editing = eventEditor.editingEvent;
    if (!editing) return;
    const previous = localEdits.overrides[editing.sessionId];
    localEdits.commit(editing.sessionId, buildSessionOverride(formState, overrideLookups));
    const warning = warningFor(editing, formState);
    notifyChange({
      sessionIds: [editing.sessionId],
      title: eventLabel(editing),
      description: warning ? `Guardado — ${warning}.` : "Alterações guardadas.",
      undo: () => localEdits.replace(editing.sessionId, previous),
    });
    closeEditor();
  };

  // Live preview of the open event's draft, layered over committed edits, so
  // the grid, lanes, arcs and distribution all recompute as the user edits —
  // before Guardar makes it permanent.
  const effectiveOverrides = useMemo(() => {
    const editing = eventEditor.isOpen ? eventEditor.editingEvent : null;
    if (!editing) return localEdits.overrides;
    const draft = buildSessionOverride(formState, overrideLookups);
    return {
      ...localEdits.overrides,
      [editing.sessionId]: { ...localEdits.overrides[editing.sessionId], ...draft },
    };
  }, [
    eventEditor.isOpen,
    eventEditor.editingEvent,
    formState,
    overrideLookups,
    localEdits.overrides,
  ]);

  const overriddenSessions = useMemo(
    () => applySessionOverrides(sessionsQuery.data, effectiveOverrides),
    [sessionsQuery.data, effectiveOverrides],
  );

  // --- derived filter view ---------------------------------------------
  const filters = useScheduleFilters({
    curso,
    anos,
    ucs,
    turnos,
    turmas,
    dias,
    semanas,
    selectedDegree,
    selectedYearDetail,
    selectedYearWeeks: overriddenSessions,
    hasSaturdaySessions,
  });

  const bulkSelectedEvents = useMemo(
    () =>
      [...selectedSessionIds]
        .map((id) => filters.scheduleEvents.find((ev) => ev.sessionId === id))
        .filter((ev): ev is WeekGridEvent => !!ev),
    [selectedSessionIds, filters.scheduleEvents],
  );
  const isBulkMode = bulkSelectedEvents.length > 1;
  const placementActive = placementMode || isBulkMode;
  const placementDurationSlots = isBulkMode
    ? Math.max(...bulkSelectedEvents.map((ev) => ev.duration))
    : formState.durationSlots;

  // --- cascade ops ------------------------------------------------------
  const { handleSelectTurnos, handleSelectTurmas } = useTurnoTurmaSync({
    classes: filters.selectedYearClasses,
    turnoOrder: filters.turnoOrder,
    turmaOrder: filters.turmaOrder,
    effectiveTurnos: filters.effectiveTurnos,
    effectiveTurmas: filters.effectiveTurmas,
    setTurnos,
    setTurmas,
  });

  useScheduleViewUrl({
    degrees,
    hasYearDetail: !!selectedYearDetail,
    hasYearWeeks: sessionsQuery.data !== undefined,
    selectedYearClasses: filters.selectedYearClasses,
    ucOptions: filters.ucOptions,
    turnoOrder: filters.turnoOrder,
    turmaOrder: filters.turmaOrder,
    allWeekValues: filters.allWeekValues,
    activeDegreeId: activeDegree?.id ?? "",
    ano: filters.effectiveAnos[0] ?? "",
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
  });

  // One palette for the whole page, keyed off the year's full UC list so each
  // UC keeps its colour as the user changes other filters (#10).
  const subjectPalette = useMemo(
    () => createSubjectPalette(filters.ucOptions),
    [filters.ucOptions],
  );

  const handleSelectCurso = (nextCurso: string) => {
    setCurso(nextCurso);
    setAnos([]);
    setUcs([]);
    setTurnos([]);
    setTurmas([]);
    setSemanas([]);
    localEdits.clear();
    setSelectedSessionIds(new Set());
  };

  if (!projectId) return null;

  // Without this, a project that fails to load (e.g. a 404) leaves the page
  // blank forever: the routing-guard effect only redirects a project that
  // loaded but isn't ingestion-ready, never one whose query errored.
  if (isProjectError) {
    return (
      <div className="h-screen bg-[#f0eeeb] flex items-center justify-center text-center text-gray-500 text-lg">
        Não foi possível carregar o projeto.
      </div>
    );
  }

  if (isProjectPending) {
    return (
      <div className="h-screen bg-[#f0eeeb] flex items-center justify-center text-center text-gray-500 text-lg">
        A carregar…
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#f0eeeb] flex flex-col overflow-hidden">
      <title>{project ? `Horário · ${project.name} · AGH` : "Horário · AGH"}</title>
      <ScheduleNavbar
        anyDialogOpen={eventEditor.isOpen || isConflictsDrawerOpen || isDistributionOpen}
        projectId={projectId}
        curso={curso}
        setCurso={handleSelectCurso}
        anos={filters.effectiveAnos}
        setAnos={setAnos}
        ucs={filters.effectiveUcs}
        setUcs={setUcs}
        turnos={filters.effectiveTurnos}
        setTurnos={handleSelectTurnos}
        turmas={filters.effectiveTurmas}
        setTurmas={handleSelectTurmas}
        dias={filters.effectiveDias}
        setDias={setDias}
        semanas={filters.effectiveSemanas}
        setSemanas={setSemanas}
        weekOptions={filters.weekOptions}
        dayOptions={filters.dayOptions}
        ucOptions={filters.ucOptions}
        subjectPalette={subjectPalette}
        turnoTurmaGroups={filters.turnoTurmaGroups}
        yearOptions={filters.yearOptions}
        courseOptions={courseOptions}
        onViewConflicts={() => {
          void yearConflictsQuery.refetch();
          setIsConflictsDrawerOpen(true);
        }}
        onViewDistribution={() => setIsDistributionOpen(true)}
      />

      <DistributionModal
        open={isDistributionOpen}
        onClose={() => setIsDistributionOpen(false)}
        events={filters.scheduleEvents}
      />

      <ConflictsDrawer
        open={isConflictsDrawerOpen}
        onClose={() => setIsConflictsDrawerOpen(false)}
        conflicts={yearConflicts}
        isLoading={yearConflictsQuery.isFetching}
        onRefresh={() => void yearConflictsQuery.refetch()}
      />

      <div className="relative flex-1 min-h-0 overflow-hidden">
        <EditEventDrawer
          key={eventEditor.editingEvent?.id ?? "new"}
          open={eventEditor.isOpen}
          collapsed={eventEditor.isCollapsed}
          onCollapsedChange={eventEditor.setIsCollapsed}
          onClose={closeEditor}
          conflicts={yearConflicts}
          ucOptions={filters.ucOptions}
          turmaOptions={filters.turmaOrder}
          teacherOptions={teacherOptions}
          roomOptions={roomOptions}
          preferredUc={filters.effectiveUcs[0]}
          event={eventEditor.editingEvent}
          formState={formState}
          dispatch={dispatchFormAndWarn}
          placementMode={placementMode}
          onTogglePlacement={() => setPlacementMode((on) => !on)}
          onSave={saveEdit}
        />
        {!canShowSchedule ? (
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            Seleciona Curso para ver o horário
          </div>
        ) : sessionsQuery.isError ? (
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            Não foi possível carregar as sessões.
          </div>
        ) : sessionsQuery.data === undefined ? (
          // First-time load: degree resolved but sessions haven't arrived yet.
          // Background refetches on filter change keep the prior grid mounted
          // so users don't see the schedule flash to a spinner.
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            A carregar sessões…
          </div>
        ) : (
          <div className="h-full min-h-0">
            <WeekGrid
              events={filters.scheduleEvents}
              marks={unavailabilityMarks}
              emptyMessage="Sem eventos para mostrar"
              startTime={800}
              endTime={1930}
              weekdayLabels={WEEKDAYS.map((weekday) => WEEKDAY_LABELS_UPPER[weekday])}
              turmaShifts={filters.turmaShifts}
              selectedTurmas={filters.effectiveTurmas}
              selectedWeeks={filters.selectedWeeks}
              weekNumbers={filters.weekNumbers}
              selectedDays={filters.effectiveDias}
              includeEndSlot
              headerHeightPx={22}
              hourLabelFontPx={12}
              slotHeightPx={30}
              showHalfHourLabels
              showHalfHourDividers
              editingEventId={eventEditor.isOpen ? eventEditor.editingEvent?.id : undefined}
              selectedSessionIds={selectedSessionIds}
              subjectPalette={subjectPalette}
              placementMode={placementActive}
              placementDurationSlots={placementDurationSlots}
              onSlotClick={(weekday, minutes, turma) => {
                if (isBulkMode) {
                  applyBulkMove(weekday, minutes, bulkSelectedEvents);
                  return;
                }
                if (!eventEditor.editingEvent) return;
                const nextState = eventDrawerFormReducer(formState, {
                  type: "placeAt",
                  weekday,
                  minutes,
                  turma,
                });
                dispatchForm({ type: "placeAt", weekday, minutes, turma });
                applyPlacement(eventEditor.editingEvent, nextState);
                // One click, one change: close so a follow-up click starts a
                // fresh selection instead of continuing to move this event.
                closeEditor();
              }}
              onEventClick={handleEventClick}
              onHorizontalScroll={() => eventEditor.setIsCollapsed(true)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
