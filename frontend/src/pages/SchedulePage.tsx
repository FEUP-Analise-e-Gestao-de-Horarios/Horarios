import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import WeekGrid from "@/components/schedule/WeekGrid";
import EditEventDrawer from "@/components/schedule/EditEventDrawer";
import ConflictsDrawer from "@/components/schedule/ConflictsDrawer";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { useTurnoTurmaSync } from "@/components/schedule/useTurnoTurmaSync";
import { useScheduleViewUrl } from "@/components/schedule/useScheduleViewUrl";
import { useProject } from "@/api/hooks/project/project";
import { useProjectDegree, useProjectDegrees } from "@/api/hooks/project/degree";
import { useProjectRooms } from "@/api/hooks/project/room";
import { useProjectTeachers } from "@/api/hooks/project/teacher";
import { useProjectSessions } from "@/api/hooks/project/sessions";
import { useProjectYear, useProjectYearConflicts } from "@/api/hooks/project/year";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import { SCHEDULE_VIEW_DAYS } from "@/utils/scheduleView";
import {
  COURSE_GROUPS,
  formatWeekRange,
  getCourseGroupLabel,
  sessionToEvents,
  sortValuesByReference,
  type ScheduleFilters,
} from "@/utils/scheduleEvents";
import { WEEKDAYS, WEEKDAY_LABELS_LONG, WEEKDAY_LABELS_UPPER } from "@/utils/weekdays";

type DropdownOption = {
  value: string;
  label: string;
  secondaryText?: string;
};

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const {
    data: project,
    isPending: isProjectPending,
    isError: isProjectError,
  } = useProject(projectId ?? "");
  const { data: degrees } = useProjectDegrees(projectId ?? "");
  const { data: teachers } = useProjectTeachers(projectId ?? "");
  const { data: rooms } = useProjectRooms(projectId ?? "");

  useEffect(() => {
    if (!projectId) {
      void navigate(ROUTES.HOME, { replace: true });
      return;
    }
    if (!project) return;
    const isReady = !!project.ingestion_finished_at;
    if (!isReady) void navigate(buildPath(ROUTES.DASHBOARD, { projectId }), { replace: true });
  }, [project, projectId, navigate]);

  const [curso, setCurso] = useState("");
  const [anos, setAnos] = useState<string[]>([]);
  const [ucs, setUcs] = useState<string[]>([]);
  const [turnos, setTurnos] = useState<string[]>([]);
  const [turmas, setTurmas] = useState<string[]>([]);
  const [semanas, setSemanas] = useState<string[]>([]);
  const [dias, setDias] = useState<string[]>([...SCHEDULE_VIEW_DAYS]);
  const [isEditDrawerOpen, setIsEditDrawerOpen] = useState(false);
  const [isEditDrawerCollapsed, setIsEditDrawerCollapsed] = useState(false);
  const [isConflictsDrawerOpen, setIsConflictsDrawerOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<WeekGridEvent | null>(null);

  const canShowSchedule = curso !== "";

  const activeDegree = useMemo(
    () => degrees?.find((degree) => degree.acronym === curso) ?? null,
    [curso, degrees],
  );

  const { data: selectedDegree } = useProjectDegree(projectId ?? "", activeDegree?.id ?? "");

  const selectedDegreeYearValues = useMemo(
    () => selectedDegree?.years.map((year) => String(year.number)) ?? [],
    [selectedDegree],
  );

  const effectiveAnos = useMemo(() => {
    if (!curso) return [];
    if (selectedDegreeYearValues.length === 0) return anos;
    const filtered = anos.filter((ano) => selectedDegreeYearValues.includes(ano));
    const firstYear = selectedDegreeYearValues[0];
    return filtered.length > 0 ? filtered : firstYear ? [firstYear] : [];
  }, [anos, curso, selectedDegreeYearValues]);

  const selectedYearNumber = effectiveAnos[0] ?? "";
  const selectedYear = useMemo(
    () => selectedDegree?.years.find((year) => String(year.number) === selectedYearNumber) ?? null,
    [selectedDegree, selectedYearNumber],
  );

  const { data: selectedYearDetail } = useProjectYear(projectId ?? "", selectedYear?.id ?? "");
  const yearConflictsQuery = useProjectYearConflicts(projectId ?? "", selectedYear?.id ?? "");
  const yearConflicts = yearConflictsQuery.data ?? [];

  const selectedYearSubjects = useMemo(
    () => selectedYearDetail?.subjects ?? [],
    [selectedYearDetail],
  );
  const selectedYearClasses = useMemo(
    () => selectedYearDetail?.classes ?? [],
    [selectedYearDetail],
  );

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
    if (dias.length === 0 || dias.length === SCHEDULE_VIEW_DAYS.length) return [];
    // Always request saturday so we can tell whether it has any sessions, even
    // when it is currently deselected in the day filter.
    return [...new Set([...dias, "saturday"])];
  }, [dias]);

  const sessionsQuery = useProjectSessions(projectId ?? "", {
    yearId: selectedYear?.id ?? "",
    subjectIds: subjectIdsFilter,
    classIds: classIdsFilter,
    weekdays: weekdayFilter,
  });
  const selectedYearWeeks = sessionsQuery.data;

  const hasSaturdaySessions = useMemo(
    () =>
      (selectedYearWeeks ?? []).some((block) =>
        block.sessions.some((session) => session.weekday === "saturday"),
      ),
    [selectedYearWeeks],
  );

  // Saturday is only shown when the selected year actually has sessions on it.
  const effectiveDias = useMemo(
    () => (hasSaturdaySessions ? dias : dias.filter((day) => day !== "saturday")),
    [dias, hasSaturdaySessions],
  );

  const ucOptions = useMemo(
    () =>
      selectedYearSubjects
        .slice()
        .sort((a, b) => a.acronym.localeCompare(b.acronym))
        .map((subject) => subject.name),
    [selectedYearSubjects],
  );
  const effectiveUcs = useMemo(
    () => (curso ? (ucs.length > 0 ? ucs.filter((uc) => ucOptions.includes(uc)) : ucOptions) : []),
    [curso, ucOptions, ucs],
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

  const turnoTurmaGroups = useMemo(() => {
    const byTurno = [...classesByTurno.entries()].sort((a, b) => Number(a[0]) - Number(b[0]));
    return byTurno.map(([turno, classes]) => ({
      turno,
      label: `Turno ${turno}`,
      turmas: classes
        .slice()
        .sort((a, b) => a.code.localeCompare(b.code))
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

  const teacherOptions = useMemo(
    () =>
      (teachers ?? [])
        .slice()
        .sort((a, b) => a.acronym.localeCompare(b.acronym))
        .map((teacher) => ({
          id: teacher.id,
          label: `${teacher.acronym} - ${teacher.name}`,
        })),
    [teachers],
  );

  const roomOptions = useMemo(
    () =>
      (rooms ?? [])
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((room) => ({
          id: room.id,
          label: room.name,
          type: room.type ?? "",
        })),
    [rooms],
  );

  const turmaShifts = useMemo(
    () =>
      Object.fromEntries(selectedYearClasses.map((classItem) => [classItem.code, classItem.shift])),
    [selectedYearClasses],
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

  const { handleSelectTurnos, handleSelectTurmas } = useTurnoTurmaSync({
    classes: selectedYearClasses,
    turnoOrder,
    turmaOrder,
    effectiveTurnos,
    effectiveTurmas,
    setTurnos,
    setTurmas,
  });

  const handleSelectCurso = (nextCurso: string) => {
    setCurso(nextCurso);
    setAnos([]);
    setUcs([]);
    setTurnos([]);
    setTurmas([]);
    setSemanas([]);
  };

  const openEditor = (event: WeekGridEvent | null) => {
    // Deep-clone so the drawer's in-flight edits can't reach back into the
    // canonical event arrays (`body`, `classCodes`, `teacherIds`, …) that the
    // grid keeps rendering from.
    setEditingEvent(event ? structuredClone(event) : null);
    setIsEditDrawerCollapsed(false);
    setIsEditDrawerOpen(true);
  };

  const weekOptions = useMemo<DropdownOption[]>(() => {
    return (selectedYearWeeks ?? []).flatMap((block) => {
      if (block.weeks.length === 0) return [];

      return [
        {
          value: block.weeks.join("|"),
          label: formatWeekRange(block.weeks),
          secondaryText: block.weeks.length === 1 ? undefined : `${block.weeks.length} semanas`,
        },
      ];
    });
  }, [selectedYearWeeks]);

  const allWeekValues = useMemo(() => weekOptions.map((option) => option.value), [weekOptions]);

  useScheduleViewUrl({
    degrees,
    hasYearDetail: !!selectedYearDetail,
    hasYearWeeks: selectedYearWeeks !== undefined,
    selectedYearClasses,
    ucOptions,
    turnoOrder,
    turmaOrder,
    allWeekValues,
    activeDegreeId: activeDegree?.id ?? "",
    ano: effectiveAnos[0] ?? "",
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

  const effectiveSemanas = useMemo(() => {
    if (!curso) return [];
    const validSelected = semanas.filter((semana) => allWeekValues.includes(semana));
    return validSelected.length > 0 ? validSelected : allWeekValues;
  }, [allWeekValues, curso, semanas]);

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

    const blockEvents = activeWeekBlocks.flatMap((block) =>
      block.sessions.flatMap((session) => sessionToEvents(session, filters)),
    );

    return blockEvents;
  }, [activeWeekBlocks, effectiveTurmas, effectiveTurnos, effectiveUcs, effectiveDias]);

  const courseOptions = useMemo(() => {
    const degreeOptions = (degrees ?? [])
      .slice()
      .sort((a, b) => a.acronym.localeCompare(b.acronym))
      .map((degree) => ({
        value: degree.acronym,
        label: degree.acronym,
        description: degree.name,
      }));

    const groupedByLabel = new Map<string, typeof degreeOptions>();

    for (const option of degreeOptions) {
      const groupLabel = getCourseGroupLabel(option.description ?? option.label);
      const current = groupedByLabel.get(groupLabel) ?? [];
      groupedByLabel.set(groupLabel, [...current, option]);
    }

    return COURSE_GROUPS.map((label) => ({
      label,
      options: groupedByLabel.get(label) ?? [],
    })).filter((group) => group.options.length > 0);
  }, [degrees]);

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
        anyDialogOpen={isEditDrawerOpen || isConflictsDrawerOpen}
        projectId={projectId}
        curso={curso}
        setCurso={handleSelectCurso}
        anos={effectiveAnos}
        setAnos={setAnos}
        ucs={effectiveUcs}
        setUcs={setUcs}
        turnos={effectiveTurnos}
        setTurnos={handleSelectTurnos}
        turmas={effectiveTurmas}
        setTurmas={handleSelectTurmas}
        dias={effectiveDias}
        setDias={setDias}
        semanas={effectiveSemanas}
        setSemanas={setSemanas}
        weekOptions={weekOptions}
        dayOptions={dayOptions}
        ucOptions={ucOptions}
        turnoTurmaGroups={turnoTurmaGroups}
        yearOptions={yearOptions}
        courseOptions={courseOptions}
        onViewConflicts={() => {
          void yearConflictsQuery.refetch();
          setIsConflictsDrawerOpen(true);
        }}
      />

      <EditEventDrawer
        key={editingEvent?.id ?? "new"}
        open={isEditDrawerOpen}
        collapsed={isEditDrawerCollapsed}
        onCollapsedChange={setIsEditDrawerCollapsed}
        onClose={() => {
          setIsEditDrawerOpen(false);
          setEditingEvent(null);
        }}
        conflicts={yearConflicts}
        ucOptions={ucOptions}
        turmaOptions={turmaOrder}
        teacherOptions={teacherOptions}
        roomOptions={roomOptions}
        preferredUc={effectiveUcs[0]}
        event={editingEvent}
      />

      <ConflictsDrawer
        open={isConflictsDrawerOpen}
        onClose={() => setIsConflictsDrawerOpen(false)}
        conflicts={yearConflicts}
        isLoading={yearConflictsQuery.isFetching}
        onRefresh={() => void yearConflictsQuery.refetch()}
      />

      <div className="flex-1 min-h-0 overflow-hidden">
        {!canShowSchedule ? (
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            Seleciona Curso para ver o horário
          </div>
        ) : sessionsQuery.isError ? (
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            Não foi possível carregar as sessões.
          </div>
        ) : selectedYearWeeks === undefined ? (
          // First-time load: degree resolved but sessions haven't arrived yet.
          // Background refetches on filter change keep the prior grid mounted
          // so users don't see the schedule flash to a spinner.
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            A carregar sessões…
          </div>
        ) : (
          <div className="h-full min-h-0">
            <WeekGrid
              events={scheduleEvents}
              emptyMessage="Sem eventos para mostrar"
              startTime={800}
              endTime={1930}
              weekdayLabels={WEEKDAYS.map((weekday) => WEEKDAY_LABELS_UPPER[weekday])}
              turmaShifts={turmaShifts}
              selectedTurmas={effectiveTurmas}
              selectedDays={effectiveDias}
              includeEndSlot
              headerHeightPx={22}
              hourLabelFontPx={12}
              slotHeightPx={31}
              showHalfHourLabels
              showHalfHourDividers
              editingEventId={isEditDrawerOpen ? editingEvent?.id : undefined}
              onEventClick={(event) => openEditor(event)}
              onHorizontalScroll={() => setIsEditDrawerCollapsed(true)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
