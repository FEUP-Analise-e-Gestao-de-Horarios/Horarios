import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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

  const effectiveAnos = useMemo(() => {
    if (!curso) return [];
    const yearOptions = selectedDegree?.years.map((year) => String(year.number)) ?? [];
    if (yearOptions.length === 0) return anos;
    const filtered = anos.filter((ano) => yearOptions.includes(ano));
    const firstYear = yearOptions[0];
    return filtered.length > 0 ? filtered : firstYear ? [firstYear] : [];
  }, [anos, curso, selectedDegree]);

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

  const yearOptions = useMemo(
    () => selectedDegree?.years.map((year) => String(year.number)) ?? [],
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

      <div className="flex-1 min-h-0 flex items-center justify-center text-center text-gray-500 text-lg overflow-hidden">
        {canShowSchedule
          ? `Grelha de horário — projeto ${projectId} (a fazer)`
          : "Seleciona Curso para ver o horário"}
      </div>
    </div>
  );
}
