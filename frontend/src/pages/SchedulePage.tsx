import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import EditEventDrawer from "@/components/schedule/EditEventDrawer";
import ConflictsDrawer from "@/components/schedule/ConflictsDrawer";
import ScheduleNavbar from "@/components/schedule/ScheduleNavbar";
import { UCS_POR_CURSO, TURMAS_POR_UC } from "@/components/schedule/data";
import { useProject } from "@/api/hooks/useDashboard";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";

const DEFAULT_ANOS = ["1", "2", "3"];
const DEFAULT_SEMANAS = ["S1", "S2", "S3", "S4", "S5"];

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project } = useProject(projectId ?? "");

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
  const [isEditDrawerOpen, setIsEditDrawerOpen] = useState(false);
  const [isConflictsDrawerOpen, setIsConflictsDrawerOpen] = useState(false);

  const canShowSchedule = curso !== "";

  const ucOptions = useMemo(() => UCS_POR_CURSO[curso] ?? [], [curso]);
  const effectiveAnos = useMemo(
    () => (curso ? (anos.length > 0 ? anos : DEFAULT_ANOS) : []),
    [anos, curso],
  );
  const effectiveUcs = useMemo(
    () => (curso ? (ucs.length > 0 ? ucs.filter((uc) => ucOptions.includes(uc)) : ucOptions) : []),
    [curso, ucOptions, ucs],
  );

  const baseTurmaOptions = useMemo(
    () =>
      effectiveUcs.length > 0
        ? effectiveUcs
            .flatMap((uc) => TURMAS_POR_UC[uc] ?? [])
            .filter((v, i, a) => a.indexOf(v) === i)
        : Object.values(TURMAS_POR_UC)
            .flat()
            .filter((v, i, a) => a.indexOf(v) === i),
    [effectiveUcs],
  );

  const turmasByTurno = useMemo(() => {
    const groups = new Map<number, string[]>();

    for (const turma of baseTurmaOptions) {
      const numericSuffix = turma.match(/(\d+)$/);
      if (!numericSuffix) continue;

      const turmaNumber = Number(numericSuffix[1]);
      if (Number.isNaN(turmaNumber) || turmaNumber <= 0) continue;

      const turno = Math.floor((turmaNumber - 1) / 5) + 1;
      const existing = groups.get(turno) ?? [];
      groups.set(turno, [...existing, turma]);
    }

    const byLabel = new Map<string, string[]>();
    const sortedEntries = [...groups.entries()].sort((a, b) => a[0] - b[0]);
    for (const [turno, turmaList] of sortedEntries) {
      const numbers = turmaList
        .map((turma) => Number(turma.match(/(\d+)$/)?.[1] ?? ""))
        .filter((n) => !Number.isNaN(n))
        .sort((a, b) => a - b);
      const label = `${turno} [Turmas ${numbers.join(", ")}]`;
      byLabel.set(label, turmaList);
    }

    return byLabel;
  }, [baseTurmaOptions]);

  const turnoOptions = useMemo(() => [...turmasByTurno.keys()], [turmasByTurno]);

  const effectiveTurnos = useMemo(
    () =>
      curso
        ? turnos.length > 0
          ? turnos.filter((turno) => turnoOptions.includes(turno))
          : turnoOptions
        : [],
    [curso, turnoOptions, turnos],
  );

  const turmaOptions = useMemo(() => {
    if (effectiveTurnos.length === 0) return baseTurmaOptions;

    return effectiveTurnos
      .flatMap((turnoLabel) => turmasByTurno.get(turnoLabel) ?? [])
      .filter((v, i, a) => a.indexOf(v) === i);
  }, [baseTurmaOptions, effectiveTurnos, turmasByTurno]);

  const effectiveTurmas = useMemo(
    () =>
      curso
        ? turmas.length > 0
          ? turmas.filter((turma) => turmaOptions.includes(turma))
          : turmaOptions
        : [],
    [curso, turmaOptions, turmas],
  );

  const effectiveSemanas = useMemo(
    () => (curso ? (semanas.length > 0 ? semanas : DEFAULT_SEMANAS) : []),
    [curso, semanas],
  );

  if (!projectId) return null;

  return (
    <div className="min-h-screen bg-[#f0eeeb]">
      <title>{project ? `Horário · ${project.name} · AGH` : "Horário · AGH"}</title>
      <ScheduleNavbar
        key={`${isEditDrawerOpen}-${isConflictsDrawerOpen}`}
        projectId={projectId}
        curso={curso}
        setCurso={setCurso}
        anos={effectiveAnos}
        setAnos={setAnos}
        ucs={effectiveUcs}
        setUcs={setUcs}
        turnos={effectiveTurnos}
        setTurnos={setTurnos}
        turmas={effectiveTurmas}
        setTurmas={setTurmas}
        semanas={effectiveSemanas}
        setSemanas={setSemanas}
        ucOptions={ucOptions}
        turnoOptions={turnoOptions}
        turmaOptions={turmaOptions}
        onEditEventClick={() => setIsEditDrawerOpen(true)}
        onViewConflicts={() => setIsConflictsDrawerOpen(true)}
      />

      <EditEventDrawer
        open={isEditDrawerOpen}
        onClose={() => setIsEditDrawerOpen(false)}
        ucOptions={ucOptions}
        turmaOptions={turmaOptions}
        preferredUc={effectiveUcs[0]}
      />

      <ConflictsDrawer
        open={isConflictsDrawerOpen}
        onClose={() => setIsConflictsDrawerOpen(false)}
      />

      <div className="flex-1 flex items-center justify-center text-gray-500 text-lg overflow-hidden">
        {canShowSchedule
          ? `Grelha de horário — projeto ${projectId} (a fazer)`
          : "Seleciona Curso para ver o horário"}
      </div>
    </div>
  );
}
