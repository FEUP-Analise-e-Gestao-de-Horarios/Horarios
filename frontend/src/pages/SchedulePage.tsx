import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import WeekGrid from "@/components/schedule/WeekGrid";
import EditEventDrawer from "@/components/schedule/EditEventDrawer";
import ConflictsDrawer from "@/components/schedule/ConflictsDrawer";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { useProject } from "@/api/hooks/project/project";
import { useProjectDegree, useProjectDegrees } from "@/api/hooks/project/degree";
import { useProjectRooms } from "@/api/hooks/project/room";
import { useProjectTeachers } from "@/api/hooks/project/teacher";
import { useProjectSessions } from "@/api/hooks/project/sessions";
import { useProjectYear, useProjectYearConflicts } from "@/api/hooks/project/year";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";
import {
  SCHEDULE_VIEW_DAYS,
  degreeKey,
  encodeScheduleView,
  parseScheduleView,
  unpackSections,
} from "@/utils/scheduleView";
import type { SessionResponse } from "@/types/project/sessions";

const COURSE_GROUPS = ["Licenciaturas", "Mestrados", "Pós-Graduações", "Outros"] as const;

type DropdownOption = {
  value: string;
  label: string;
  secondaryText?: string;
};

type ScheduleFilters = {
  ucs: Set<string>;
  turnos: Set<string>;
  turmas: Set<string>;
  dias: Set<string>;
};

function sortValuesByReference(values: string[], reference: string[]) {
  const referenceIndex = new Map(reference.map((value, index) => [value, index]));
  return [...new Set(values)]
    .filter((value) => referenceIndex.has(value))
    .sort((left, right) => (referenceIndex.get(left) ?? 0) - (referenceIndex.get(right) ?? 0));
}

function getCourseGroupLabel(name: string) {
  const normalized = name.toLowerCase();
  if (normalized.includes("licenciatura")) return "Licenciaturas";
  if (normalized.includes("mestrado")) return "Mestrados";
  if (normalized.includes("pós") || normalized.includes("pos") || normalized.includes("gradua")) {
    return "Pós-Graduações";
  }
  return "Outros";
}

function formatDateLabel(value: string) {
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${day}-${month}-${year}`;
}

function formatWeekRange(weeks: string[]) {
  if (weeks.length === 0) return "";
  const firstWeek = formatDateLabel(weeks.at(0) ?? "");
  const lastWeek = formatDateLabel(weeks.at(-1) ?? "");
  return firstWeek === lastWeek ? firstWeek : `${firstWeek} - ${lastWeek}`;
}

function sessionToEvents(session: SessionResponse, filters: ScheduleFilters): WeekGridEvent[] {
  const selectedSubjects = new Set(filters.ucs);
  const selectedTurmas = new Set(filters.turmas);
  const selectedTurnos = new Set(filters.turnos);
  const selectedDias = new Set(filters.dias);

  if (
    selectedSubjects.size > 0 &&
    !session.subjects.some((subject) => selectedSubjects.has(subject.name))
  ) {
    return [];
  }

  if (selectedDias.size > 0 && !selectedDias.has(session.weekday)) {
    return [];
  }

  const primarySubject = session.subjects[0];
  const title = session.subjects.map((subject) => subject.acronym).join(", ") || session.type;
  const body = [
    session.teachers.map((teacher) => teacher.acronym).join(", "),
    session.rooms.map((room) => room.name).join(", "),
  ].filter((item) => item.length > 0);

  if (session.classes.length === 0) {
    if (selectedTurmas.size > 0 || selectedTurnos.size > 0) return [];
    return [
      {
        id: session.id,
        weekday: session.weekday,
        startTime: session.start_time,
        duration: session.duration,
        title,
        body,
        type: session.type,
        classCodes: session.classes.map((classItem) => classItem.code),
        uc: primarySubject?.name ?? primarySubject?.acronym ?? session.type,
        professor: session.teachers[0]?.acronym,
        sala: session.rooms[0]?.name,
        teacherIds: session.teachers.map((teacher) => teacher.id),
        roomIds: session.rooms.map((room) => room.id),
        subjectNames: session.subjects.map((subject) => subject.name),
      },
    ];
  }

  return session.classes
    .filter((classItem) => {
      const turno = String(classItem.shift);
      const matchesTurma = selectedTurmas.size === 0 || selectedTurmas.has(classItem.code);
      const matchesTurno = selectedTurnos.size === 0 || selectedTurnos.has(turno);
      return matchesTurma && matchesTurno;
    })
    .map((classItem) => ({
      id: `${session.id}-${classItem.code}`,
      weekday: session.weekday,
      startTime: session.start_time,
      duration: session.duration,
      title,
      body,
      type: session.type,
      turma: classItem.code,
      classCodes: session.classes.map((currentClass) => currentClass.code),
      uc: primarySubject?.name ?? primarySubject?.acronym ?? session.type,
      professor: session.teachers[0]?.acronym,
      sala: session.rooms[0]?.name,
      teacherIds: session.teachers.map((teacher) => teacher.id),
      roomIds: session.rooms.map((room) => room.id),
      subjectNames: session.subjects.map((subject) => subject.name),
    }));
}

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project } = useProject(projectId ?? "");
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

  const [searchParams, setSearchParams] = useSearchParams();
  const [initialView] = useState<string | null>(() => searchParams.get("view"));
  const hydrationPhaseRef = useRef(0);
  const [isHydrated, setIsHydrated] = useState(false);

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

  const weekdayFilter = useMemo(() => (dias.length === 6 ? [] : dias), [dias]);

  const sessionsQuery = useProjectSessions(projectId ?? "", {
    yearId: selectedYear?.id ?? "",
    subjectIds: subjectIdsFilter,
    classIds: classIdsFilter,
    weekdays: weekdayFilter,
  });
  const selectedYearWeeks = sessionsQuery.data;

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

  const turmaOptionsForEditor = useMemo(
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

  const allTurnoValues = turnoOrder;
  const allTurmaValues = turmaOrder;

  const effectiveTurnos = useMemo(() => {
    if (!curso) return [];
    const validSelected = turnos.filter((turno) => allTurnoValues.includes(turno));
    const fallback = validSelected.length > 0 ? validSelected : allTurnoValues;
    return sortValuesByReference(fallback, turnoOrder);
  }, [allTurnoValues, curso, turnoOrder, turnos]);

  const effectiveTurmas = useMemo(() => {
    if (!curso) return [];
    const validSelected = turmas.filter((turma) => allTurmaValues.includes(turma));
    const fallback = validSelected.length > 0 ? validSelected : allTurmaValues;
    return sortValuesByReference(fallback, turmaOrder);
  }, [allTurmaValues, curso, turmaOrder, turmas]);

  const turnosFromTurmas = (turmaCodes: string[]) => {
    const selectedShifts = new Set<string>();
    for (const classItem of selectedYearClasses) {
      if (turmaCodes.includes(classItem.code)) {
        selectedShifts.add(String(classItem.shift));
      }
    }
    return [...selectedShifts].sort((a, b) => Number(a) - Number(b));
  };

  const handleSelectTurnos = (nextTurnos: string[]) => {
    const currentTurnos = effectiveTurnos;
    const currentTurmas = effectiveTurmas;
    const addedTurnos = nextTurnos.filter((turno) => !currentTurnos.includes(turno));
    const removedTurnos = currentTurnos.filter((turno) => !nextTurnos.includes(turno));

    const turmasToAdd = selectedYearClasses
      .filter((classItem) => addedTurnos.includes(String(classItem.shift)))
      .map((classItem) => classItem.code);
    const turmasToRemove = selectedYearClasses
      .filter((classItem) => removedTurnos.includes(String(classItem.shift)))
      .map((classItem) => classItem.code);

    const nextTurmas = new Set(currentTurmas);
    turmasToAdd.forEach((turma) => nextTurmas.add(turma));
    turmasToRemove.forEach((turma) => nextTurmas.delete(turma));

    const nextTurmasArray = [...nextTurmas].filter((turma) =>
      selectedYearClasses.some((classItem) => classItem.code === turma),
    );

    const orderedTurmas = sortValuesByReference(nextTurmasArray, turmaOrder);
    const orderedTurnos = sortValuesByReference(turnosFromTurmas(orderedTurmas), turnoOrder);

    setTurmas(orderedTurmas);
    setTurnos(orderedTurnos);
  };

  const handleSelectTurmas = (nextTurmas: string[]) => {
    const validTurmas = nextTurmas.filter((turma) =>
      selectedYearClasses.some((classItem) => classItem.code === turma),
    );
    const orderedTurmas = sortValuesByReference(validTurmas, turmaOrder);
    setTurmas(orderedTurmas);
    setTurnos(sortValuesByReference(turnosFromTurmas(orderedTurmas), turnoOrder));
  };

  const handleSelectCurso = (nextCurso: string) => {
    setCurso(nextCurso);
    setAnos([]);
    setUcs([]);
    setTurnos([]);
    setTurmas([]);
    setSemanas([]);
  };

  const openEditor = (event: WeekGridEvent | null) => {
    setEditingEvent(event ? { ...event } : null);
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
      if (!selectedYearDetail) return;
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
      if (selectedYearWeeks === undefined) return;
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
    selectedYearDetail,
    selectedYearWeeks,
    selectedYearClasses,
    ucOptions,
    turmaOrder,
    turnoOrder,
    allWeekValues,
  ]);

  useEffect(() => {
    if (!isHydrated) return;

    const newView = encodeScheduleView(
      {
        degreeId: activeDegree?.id ?? "",
        ano: effectiveAnos[0] ?? "",
        ucs,
        turmas,
        dias,
        semanas,
      },
      {
        ucOrder: ucOptions,
        turmaOrder,
        weekOrder: allWeekValues,
      },
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
    activeDegree?.id,
    effectiveAnos,
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
      dias: new Set(dias),
    };

    const blockEvents = activeWeekBlocks.flatMap((block) =>
      block.sessions.flatMap((session) => sessionToEvents(session, filters)),
    );

    return blockEvents;
  }, [activeWeekBlocks, effectiveTurmas, effectiveTurnos, effectiveUcs, dias]);

  const displayEvents = useMemo(() => {
    if (scheduleEvents.length > 0) return scheduleEvents;
    return [];
  }, [scheduleEvents]);

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

  const dayOptions: DropdownOption[] = [
    { value: "monday", label: "Segunda-feira" },
    { value: "tuesday", label: "Terça-feira" },
    { value: "wednesday", label: "Quarta-feira" },
    { value: "thursday", label: "Quinta-feira" },
    { value: "friday", label: "Sexta-feira" },
    { value: "saturday", label: "Sábado" },
  ];

  if (!projectId) return null;

  return (
    <div className="h-screen bg-[#f0eeeb] flex flex-col overflow-hidden">
      <title>{project ? `Horário · ${project.name} · AGH` : "Horário · AGH"}</title>
      <ScheduleNavbar
        key={`${isEditDrawerOpen}-${isConflictsDrawerOpen}`}
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
        dias={dias}
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
        turmaOptions={turmaOptionsForEditor}
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
        {canShowSchedule ? (
          <div className="h-full min-h-0">
            <WeekGrid
              events={displayEvents}
              emptyMessage="Sem eventos para mostrar"
              startTime={800}
              endTime={1930}
              weekdayLabels={["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO"]}
              turmaShifts={turmaShifts}
              selectedTurmas={effectiveTurmas}
              selectedDays={dias}
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
        ) : (
          <div className="h-full flex items-center justify-center text-center text-gray-500 text-lg">
            Seleciona Curso para ver o horário
          </div>
        )}
      </div>
    </div>
  );
}
