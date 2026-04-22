import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { WeekGridEvent } from "@/components/schedule/WeekGrid";
import WeekGrid from "@/components/schedule/WeekGrid";
import EditEventDrawer from "@/components/schedule/EditEventDrawer";
import ConflictsDrawer from "@/components/schedule/ConflictsDrawer";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { useProjectDegree, useProjectDegrees, useProject } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";

const DEFAULT_SEMANAS = ["S1", "S2", "S3", "S4", "S5"];
const COURSE_GROUPS = ["Licenciaturas", "Mestrados", "Pós-Graduações", "Outros"] as const;

type DropdownOption = {
  value: string;
  label: string;
  secondaryText?: string;
};

const HARD_CODED_EVENTS: WeekGridEvent[] = [
  {
    id: "evt-1",
    weekday: "wednesday" as const,
    startTime: 1030,
    duration: 4,
    title: "CTEFP",
    body: ["ACPPF", "JFO", "B322"],
    type: "TP",
    turma: "CTFP_2S_T1",
    uc: "CTEFP",
    professor: "JFO",
    sala: "B322",
  },
  {
    id: "evt-2a",
    weekday: "monday" as const,
    startTime: 830,
    duration: 4,
    title: "P",
    body: ["JBispo", "DCC - JMPP", "B002"],
    type: "P",
    turma: "CTFP_2S_T1",
    uc: "P",
    professor: "JBispo",
    sala: "B002",
  },
  {
    id: "evt-2b",
    weekday: "monday" as const,
    startTime: 830,
    duration: 4,
    title: "TC",
    body: ["JAC", "B220"],
    type: "TC",
    turma: "CTFP_2S_T1",
    uc: "TC",
    professor: "JAC",
    sala: "B220",
  },
  {
    id: "evt-2c",
    weekday: "monday" as const,
    startTime: 830,
    duration: 4,
    title: "FI",
    body: ["MJFVLM", "B119"],
    type: "FI",
    turma: "CTFP_2S_T1",
    uc: "FI",
    professor: "MJFVLM",
    sala: "B119",
  },
  {
    id: "evt-2d",
    weekday: "monday" as const,
    startTime: 830,
    duration: 4,
    title: "AC",
    body: ["MMC", "B303"],
    type: "AC",
    turma: "CTFP_2S_T1",
    uc: "AC",
    professor: "MMC",
    sala: "B303",
  },
  {
    id: "evt-3a",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "AM II",
    body: ["RBAMS", "B322"],
    type: "PL",
    turma: "CTFP_2S_T1",
    uc: "AM II",
    professor: "RBAMS",
    sala: "B322",
  },
  {
    id: "evt-3b",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "AC",
    body: ["MMC", "B303"],
    type: "AC",
    turma: "CTFP_2S_T1",
    uc: "AC",
    professor: "MMC",
    sala: "B303",
  },
  {
    id: "evt-3c",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "P",
    body: ["JCL", "B301"],
    type: "P",
    turma: "CTFP_2S_T1",
    uc: "P",
    professor: "JCL",
    sala: "B301",
  },
  {
    id: "evt-3d",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "TC",
    body: ["LFCA", "B117"],
    type: "TC",
    turma: "CTFP_2S_T1",
    uc: "TC",
    professor: "LFCA",
    sala: "B117",
  },
  {
    id: "evt-3e",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "AM II",
    body: ["AMAN", "B323"],
    type: "PL",
    turma: "CTFP_2S_T1",
    uc: "AM II",
    professor: "AMAN",
    sala: "B323",
  },
  {
    id: "evt-3f",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "FI",
    body: ["PTPV", "B219"],
    type: "FI",
    turma: "CTFP_2S_T1",
    uc: "FI",
    professor: "PTPV",
    sala: "B219",
  },
  {
    id: "evt-3g",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "FI",
    body: ["MJFVLM", "B216"],
    type: "FI",
    turma: "CTFP_2S_T1",
    uc: "FI",
    professor: "MJFVLM",
    sala: "B216",
  },
  {
    id: "evt-3h",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "TC",
    body: ["NFMM", "B343"],
    type: "TC",
    turma: "CTFP_2S_T1",
    uc: "TC",
    professor: "NFMM",
    sala: "B343",
  },
  {
    id: "evt-3i",
    weekday: "monday" as const,
    startTime: 1030,
    duration: 2,
    title: "AC",
    body: ["BMCL", "B307"],
    type: "AC",
    turma: "CTFP_2S_T1",
    uc: "AC",
    professor: "BMCL",
    sala: "B307",
  },
  {
    id: "evt-4",
    weekday: "monday" as const,
    startTime: 1230,
    duration: 4,
    title: "AM II",
    body: ["AMPA", "B214"],
    type: "PL",
    turma: "CTFP_2S_T1",
    uc: "AM II",
    professor: "AMPA",
    sala: "B214",
  },
  {
    id: "evt-5",
    weekday: "tuesday" as const,
    startTime: 1030,
    duration: 4,
    title: "P",
    body: ["JBispo", "DCC - JMPP", "B002"],
    type: "P",
    turma: "CTFP_2S_T1",
    uc: "P",
    professor: "JBispo",
    sala: "B002",
  },
];

function getCourseGroupLabel(name: string) {
  const normalized = name.toLowerCase();
  if (normalized.includes("licenciatura")) return "Licenciaturas";
  if (normalized.includes("mestrado")) return "Mestrados";
  if (normalized.includes("pós") || normalized.includes("pos") || normalized.includes("gradua")) {
    return "Pós-Graduações";
  }
  return "Outros";
}

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project } = useProject(projectId ?? "");
  const { data: degrees } = useProjectDegrees(projectId ?? "");

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
  const [turnosTouched, setTurnosTouched] = useState(false);
  const [turmasTouched, setTurmasTouched] = useState(false);
  const [semanas, setSemanas] = useState<string[]>([]);
  const [isEditDrawerOpen, setIsEditDrawerOpen] = useState(false);
  const [isConflictsDrawerOpen, setIsConflictsDrawerOpen] = useState(false);

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

  const selectedYearSubjects = useMemo(() => selectedYear?.subjects ?? [], [selectedYear]);
  const selectedYearClasses = useMemo(() => selectedYear?.classes ?? [], [selectedYear]);

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

  const turnoOptions = useMemo<DropdownOption[]>(() => {
    const byTurno = [...classesByTurno.entries()].sort((a, b) => Number(a[0]) - Number(b[0]));
    return byTurno.map(([turno, classes]) => ({
      value: turno,
      label: `Turno ${turno}`,
      secondaryText: `Turmas: ${classes.map((classItem) => classItem.code).join(", ")}`,
    }));
  }, [classesByTurno]);

  const turmaOptions = useMemo<DropdownOption[]>(
    () =>
      selectedYearClasses
        .slice()
        .sort((a, b) => a.shift - b.shift || a.code.localeCompare(b.code))
        .map((classItem) => ({
          value: classItem.code,
          label: classItem.code,
          secondaryText: `${classItem.shift}º Turno`,
        })),
    [selectedYearClasses],
  );

  const turmaShifts = useMemo(
    () =>
      Object.fromEntries(selectedYearClasses.map((classItem) => [classItem.code, classItem.shift])),
    [selectedYearClasses],
  );

  const allTurnoValues = useMemo(() => turnoOptions.map((option) => option.value), [turnoOptions]);
  const allTurmaValues = useMemo(() => turmaOptions.map((option) => option.value), [turmaOptions]);

  const effectiveTurnos = useMemo(() => {
    if (!curso) return [];
    const validSelected = turnos.filter((turno) => allTurnoValues.includes(turno));
    if (turnosTouched) return validSelected;
    return validSelected.length > 0 ? validSelected : allTurnoValues;
  }, [allTurnoValues, curso, turnos, turnosTouched]);

  const effectiveTurmas = useMemo(() => {
    if (!curso) return [];
    const validSelected = turmas.filter((turma) => allTurmaValues.includes(turma));
    if (turmasTouched) return validSelected;
    return validSelected.length > 0 ? validSelected : allTurmaValues;
  }, [allTurmaValues, curso, turmas, turmasTouched]);

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

    setTurmas(nextTurmasArray);
    setTurnos(turnosFromTurmas(nextTurmasArray));
    setTurmasTouched(true);
    setTurnosTouched(true);
  };

  const handleSelectTurmas = (nextTurmas: string[]) => {
    const validTurmas = nextTurmas.filter((turma) =>
      selectedYearClasses.some((classItem) => classItem.code === turma),
    );
    setTurmas(validTurmas);
    setTurnos(turnosFromTurmas(validTurmas));
    setTurmasTouched(true);
    setTurnosTouched(true);
  };

  const handleSelectCurso = (nextCurso: string) => {
    setCurso(nextCurso);
    setAnos([]);
    setUcs([]);
    setTurnos([]);
    setTurmas([]);
    setSemanas([]);
    setTurnosTouched(false);
    setTurmasTouched(false);
  };

  const effectiveSemanas = useMemo(
    () => (curso ? (semanas.length > 0 ? semanas : DEFAULT_SEMANAS) : []),
    [curso, semanas],
  );

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
        secondaryText: `${year.subjects.length} UCs · ${year.classes.length} turmas`,
      })) ?? [],
    [selectedDegree],
  );

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
        semanas={effectiveSemanas}
        setSemanas={setSemanas}
        ucOptions={ucOptions}
        turnoOptions={turnoOptions}
        turmaOptions={turmaOptions}
        yearOptions={yearOptions}
        courseOptions={courseOptions}
        onEditEventClick={() => setIsEditDrawerOpen(true)}
        onViewConflicts={() => setIsConflictsDrawerOpen(true)}
      />

      <EditEventDrawer
        open={isEditDrawerOpen}
        onClose={() => setIsEditDrawerOpen(false)}
        ucOptions={ucOptions}
        turmaOptions={turmaOptions.map((option) => option.value)}
        preferredUc={effectiveUcs[0]}
      />

      <ConflictsDrawer
        open={isConflictsDrawerOpen}
        onClose={() => setIsConflictsDrawerOpen(false)}
      />

      <div className="flex-1 min-h-0 overflow-hidden">
        {canShowSchedule ? (
          <div className="h-full min-h-0">
            <WeekGrid
              events={[...HARD_CODED_EVENTS]}
              emptyMessage="Sem eventos para mostrar"
              startTime={800}
              endTime={1930}
              weekdayLabels={["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO"]}
              turmaShifts={turmaShifts}
              selectedTurmas={effectiveTurmas}
              includeEndSlot
              headerHeightPx={22}
              hourLabelFontPx={12}
              slotHeightPx={31}
              showHalfHourLabels
              showHalfHourDividers
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
