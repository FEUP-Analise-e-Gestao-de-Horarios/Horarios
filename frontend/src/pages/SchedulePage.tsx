import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import WeekGrid, { type WeekGridEvent } from "@/components/schedule/WeekGrid";
import EditEventDrawer from "@/components/schedule/EditEventDrawer";
import ConflictsDrawer from "@/components/schedule/ConflictsDrawer";
import DistributionModal from "@/components/schedule/DistributionModal";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { useEventUnavailability } from "@/components/schedule/useEventUnavailability";
import { useEventEditor } from "@/components/schedule/useEventEditor";
import { useEventDrawerForm } from "@/components/schedule/useEventDrawerForm";
import {
  applySessionOverrides,
  buildSessionOverride,
  useLocalSessionEdits,
  type OverrideLookups,
  type SessionOverrides,
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
import { minutesToTime } from "@/utils/time";
import { WEEKDAYS, WEEKDAY_LABELS_UPPER } from "@/utils/weekdays";

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

  // In-memory event edits: not persisted, cleared on course change. The edit
  // drawer's form lives here (not inside the drawer) so the grid can preview
  // it live and write a placement click's target into it.
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
  // a button to turn it off.
  const [placementMode, setPlacementMode] = useState(false);
  const openEditor = (event: WeekGridEvent) => {
    setPlacementMode(true);
    eventEditor.openEditor(event, true);
  };
  const closeEditor = () => {
    setPlacementMode(false);
    eventEditor.closeEditor();
  };

  // Where the selected event's teacher(s)/room are unavailable (#5).
  const unavailabilityMarks = useEventUnavailability(
    projectId ?? "",
    eventEditor.isOpen ? eventEditor.editingEvent : null,
  );

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

  const saveEdit = () => {
    const editing = eventEditor.editingEvent;
    if (!editing) return;
    localEdits.commit(editing.sessionId, buildSessionOverride(formState, overrideLookups));
    closeEditor();
  };

  // Live preview of the open event's edits, layered over committed edits, so
  // the grid, lanes, arcs and distribution all recompute as the user edits.
  const effectiveOverrides = useMemo<SessionOverrides>(() => {
    const editing = eventEditor.isOpen ? eventEditor.editingEvent : null;
    if (!editing) return localEdits.overrides;
    const live = buildSessionOverride(formState, overrideLookups);
    return {
      ...localEdits.overrides,
      [editing.sessionId]: { ...localEdits.overrides[editing.sessionId], ...live },
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
          dispatch={dispatchForm}
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
              subjectPalette={subjectPalette}
              compactEmpty={!placementMode}
              placementMode={placementMode}
              placementDurationSlots={formState.durationSlots}
              onSlotClick={(weekday, minutes) => {
                dispatchForm({ type: "setWeekday", value: weekday });
                dispatchForm({ type: "normalizeStartTime", raw: minutesToTime(minutes) });
              }}
              onEventClick={openEditor}
              onHorizontalScroll={() => eventEditor.setIsCollapsed(true)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
